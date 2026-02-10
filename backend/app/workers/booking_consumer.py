from confluent_kafka import Consumer
import json

conf = {
    "bootstrap.servers":"localhost:29092",#for external servers
    # "bootstrap.servers": "localhost:9092",#for inetrnal servers
    "group.id": "booking-workers-test-1",
    "auto.offset.reset": "earliest",
}

consumer = Consumer(conf)
consumer.subscribe(["booking.confirmed"])

print("Booking consumer started...")

while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue
    if msg.error():
        print("Consumer error:", msg.error())
        continue

    event = json.loads(msg.value().decode("utf-8"))
    print("Received booking event:", event)

    # Here you would:
    # - send email
    # - send push notification
    # - store analytics
