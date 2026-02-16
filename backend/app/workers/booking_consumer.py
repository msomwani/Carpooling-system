from confluent_kafka import Consumer
import json

conf = {
    "bootstrap.servers":"localhost:29092",#for docker
    # "bootstarp.servers":"localhost:9092"for local host
    "group.id": "booking-workers-test-1",
    "auto.offset.reset": "earliest",
}

consumer = Consumer(conf)
consumer.subscribe(["booking.confirmed","booking.cancelled"])

print("Booking consumer started...")

MAX_RETRIES = 3

while True:
    msg = consumer.poll(1.0)

    if msg is None:
        continue
    if msg.error():
        print("Consumer error:", msg.error())
        continue

    try:
        raw_value = msg.value()
        if raw_value is None:
            print("Received empty message")
            consumer.commit()
            continue

        event = json.loads(raw_value.decode("utf-8"))

    except Exception as e:
        print("Invalid JSON message:", e)
        consumer.commit()
        continue

    retries = 0
    success = False

    while retries < MAX_RETRIES and not success:
        try:
            if msg.topic() == "booking.confirmed":
                print("✅ Booking confirmed:", event)
                # TODO: Send notification email/SMS here

            elif msg.topic() == "booking.cancelled":
                print("❌ Booking cancelled:", event)
                # TODO: Send cancellation notification here

            success = True

        except Exception as e:
            retries += 1
            print(f"Retry {retries} failed:", e)

    if not success:
        # Send to DLQ
        from app.common.kafka import publish_event
        print(f"⚠️ Moving to DLQ after {MAX_RETRIES} retries:", event)
        publish_event("booking.dlq", event)

    consumer.commit()