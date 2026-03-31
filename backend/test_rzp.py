import razorpay
client = razorpay.Client(auth=("rzp_test_SXTfZmWs1kIC6P", "4NqrJpz9I434218W86eGfbn9"))
try:
    order = client.order.create({
        "amount": 100,
        "currency": "INR",
        "receipt": "receipt_test_123",
        "notes": {"booking_id": "test_123"}
    })
    print("SUCCESS", order)
except Exception as e:
    print("ERROR", str(e))
