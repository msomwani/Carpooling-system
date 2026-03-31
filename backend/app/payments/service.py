import razorpay
from app.config.settings import settings

class PaymentService:
    def __init__(self):
        self.client=razorpay.Client(
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
        )

    def create_order(self,amount_in_inr:int,booking_id:str):
        data={
            "amount":amount_in_inr*100,
            "currency":"INR",
            "receipt":str(booking_id)[:40],
            "notes":{"booking_id":booking_id}
        }
        
        return self.client.order.create(data=data)


    def create_transfer(self, payment_id: str, account_id: str, amount_in_paise: int):
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
                    "notes": {
                        "payment_id": payment_id
                    },
                    "on_hold": 1 # 1 means True in Razorpay API for this field
                }
            ]
        }
        return self.client.payment.transfer(payment_id, data)

    def release_transfer(self, transfer_id: str):
        """
        Releases a held transfer.
        Called when a ride is COMPLETED.
        """
        # Razorpay Transfer update API to release hold
        return self.client.transfer.edit(transfer_id, {"on_hold": 0})

    def refund_payment(self, payment_id: str, amount_in_paise: int):
        """
        Refunds a payment to the user.
        Uses reverse_all=1 to automatically reverse any connected on_hold transfers.
        """
        data = {
            "amount": amount_in_paise,
            "reverse_all": 1
        }
        return self.client.payment.refund(payment_id, data)

    def verify_payment(self,razorpay_order_id,razorpay_payment_id,razorpay_signature):
        param_dict={
            'razorpay_order_id':razorpay_order_id,
            'razorpay_payment_id':razorpay_payment_id,
            'razorpay_signature':razorpay_signature
        }

        try:
            return self.client.utility.verify_payment_signature(param_dict)

        except Exception:
            return False
