from unittest.mock import patch
from uuid import uuid4

from app.auth.dependencies import get_current_user_id
from app.bookings.models import Booking
from app.main import app


def test_create_order_requires_authentication(client):
    response = client.post("/payments/create-order", json={"booking_id": str(uuid4())})

    assert response.status_code == 401


def test_create_order_uses_server_side_amount_for_booking_owner(client, db, sample_passenger, sample_ride):
    sample_ride.price_per_seat = 180
    db.commit()

    booking = Booking(
        id=uuid4(),
        ride_id=sample_ride.id,
        passenger_id=sample_passenger.id,
        seats_booked=2,
        status="PENDING_PAYMENT",
    )
    db.add(booking)
    db.commit()

    app.dependency_overrides[get_current_user_id] = lambda: str(sample_passenger.id)

    with patch("app.payments.router.payment_service.create_order", return_value={"id": "order_test_123", "amount": 36000}) as mock_create_order:
        response = client.post(
            "/payments/create-order",
            json={"booking_id": str(booking.id), "amount": 1},
        )

    assert response.status_code == 200
    mock_create_order.assert_called_once_with(360, str(booking.id))
    db.refresh(booking)
    assert booking.razorpay_order_id == "order_test_123"

    app.dependency_overrides.clear()


def test_verify_payment_rejects_order_mismatch(client, db, sample_passenger, sample_ride):
    booking = Booking(
        id=uuid4(),
        ride_id=sample_ride.id,
        passenger_id=sample_passenger.id,
        seats_booked=1,
        status="PENDING_PAYMENT",
        razorpay_order_id="order_expected",
    )
    db.add(booking)
    db.commit()

    app.dependency_overrides[get_current_user_id] = lambda: str(sample_passenger.id)

    with patch("app.payments.router.payment_service.verify_payment", return_value=True):
        response = client.post(
            "/payments/verify",
            json={
                "booking_id": str(booking.id),
                "razorpay_order_id": "order_other",
                "razorpay_payment_id": "pay_test_123",
                "razorpay_signature": "sig_test_123",
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Payment order does not match this booking."

    app.dependency_overrides.clear()
