import os

import razorpay


key_id = os.getenv("RAZORPAY_KEY_ID", "")
key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")

if not key_id or not key_secret:
    print("ERROR Missing RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET in the environment.")
else:
    client = razorpay.Client(auth=(key_id, key_secret))
    try:
        order = client.order.create(
            {
                "amount": 100,
                "currency": "INR",
                "receipt": "receipt_test_123",
                "notes": {"booking_id": "test_123"},
            }
        )
        print("SUCCESS", order)
    except Exception as e:
        print("ERROR", str(e))
