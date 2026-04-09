import logging
import razorpay
from app.config.settings import settings

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self):
        self.client = razorpay.Client(
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
        )

    # ─── Orders ───────────────────────────────────────────────────────────────

    def create_order(self, amount_in_inr: int, booking_id: str):
        data = {
            "amount": amount_in_inr * 100,
            "currency": "INR",
            "receipt": str(booking_id)[:40],
            "notes": {"booking_id": booking_id},
        }
        return self.client.order.create(data=data)

    # ─── Transfers / Escrow ───────────────────────────────────────────────────

    def create_transfer(
        self,
        payment_id: str,
        account_id: str,
        amount_in_paise: int,
        *,
        on_hold: bool = True,
    ):
        """
        Creates a transfer to a linked account with 'on_hold' set to True.
        Used for Escrow/Marketplace model.
        """
        data = {
            "transfers": [
                {
                    "account": account_id,
                    "amount": amount_in_paise,
                    "currency": "INR",
                    "notes": {"payment_id": payment_id},
                    "on_hold": on_hold,
                }
            ]
        }
        return self.client.payment.transfer(payment_id, data)

    def release_transfer(self, transfer_id: str):
        """
        Releases a held transfer.
        Called when a ride is COMPLETED.
        """
        return self.client.transfer.edit(transfer_id, {"on_hold": 0})

    def refund_payment(self, payment_id: str, amount_in_paise: int):
        """
        Refunds a payment to the user.
        Uses reverse_all=1 to automatically reverse any connected on_hold transfers.
        """
        data = {"amount": amount_in_paise, "reverse_all": 1}
        return self.client.payment.refund(payment_id, data)

    def verify_payment(
        self, razorpay_order_id, razorpay_payment_id, razorpay_signature
    ):
        param_dict = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        }
        try:
            return self.client.utility.verify_payment_signature(param_dict)
        except Exception:
            return False

    # ─── Razorpay Route — Linked Accounts ─────────────────────────────────────

    def create_linked_account(
        self,
        *,
        legal_name: str,
        email: str,
        phone: str,
        beneficiary_name: str,
        account_number: str,
        ifsc_code: str,
    ) -> str:
        """
        Full Route onboarding flow (test-mode compatible):
          1. Create the linked account (individual / route)
          2. Add a stakeholder
          3. Request Route product configuration
          4. Patch bank account details
        Returns the Razorpay account_id (e.g. "acc_ABCxyz123").
        """
        # 1. Create linked account
        account_payload = {
            "email": email,
            "profile": {
                "category": "transportation",
                "subcategory": "ride_hailing",
                "addresses": {
                    "registered": {
                        "street1": "NA",
                        "city": "NA",
                        "state": "GJ",
                        "postal_code": "390001",
                        "country": "IN",
                    }
                },
            },
            "type": "individual",
            "legal_info": {"pan": "AAAPL1234C"},  # test-mode placeholder PAN
            "legal_business_name": legal_name,
            "business_type": "individual",
            "contact_name": legal_name,
            "contact_info": {
                "name": legal_name,
                "email": email,
                "phone": phone,
            },
        }
        account = self.client.account.create(account_payload)
        account_id: str = account["id"]
        logger.info("Razorpay linked account created: %s", account_id)

        # 2. Create stakeholder
        stakeholder_payload = {
            "name": legal_name,
            "email": email,
            "relationship": {"director": True},
            "phone": {"primary": phone},
            "percentage_ownership": 100,
        }
        self.client.account.create_stakeholder(account_id, stakeholder_payload)
        logger.info("Stakeholder created for account: %s", account_id)

        # 3. Request Route product
        self.client.account.request_product_configuration(
            account_id, {"product_name": "route"}
        )

        # 4. Update product config with bank details
        bank_payload = {
            "settlements": {
                "account_number": account_number,
                "ifsc_code": ifsc_code,
                "beneficiary_name": beneficiary_name,
            },
            "tnc_accepted": True,
        }
        self.client.account.update_product_configuration(
            account_id, "route", bank_payload
        )
        logger.info("Bank details linked for account: %s", account_id)

        return account_id

    def fetch_linked_account(self, account_id: str) -> dict:
        """Fetch the current status of a linked account from Razorpay."""
        try:
            return self.client.account.fetch(account_id)
        except Exception as exc:
            logger.warning("Could not fetch linked account %s: %s", account_id, exc)
            return {}
