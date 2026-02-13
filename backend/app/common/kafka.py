from confluent_kafka import Producer
from app.config.settings import settings
import json

producer_conf = {
    "bootstrap.servers": settings.kafka_bootstrap_servers,
    "retries": 5,
    "acks": "all",
}

producer = Producer(producer_conf)


def delivery_report(err, msg):
    if err is not None:
        print("❌ Delivery failed:", err)
    else:
        print(f"✅ Delivered to {msg.topic()} [{msg.partition()}]")


def publish_event(topic: str, payload: dict):
    try:
        producer.produce(
            topic=topic,
            value=json.dumps(payload),
            callback=delivery_report,
        )
        producer.poll(0)
    except Exception as e:
        print("Kafka publish error:", e)
