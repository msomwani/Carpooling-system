from confluent_kafka import Producer
from app.config.settings import settings
import json

producer_conf = {
    "bootstrap.servers": settings.kafka_bootstrap_servers,
}

producer = Producer(producer_conf)


def publish_event(topic: str, payload: dict):
    producer.produce(
        topic=topic,
        value=json.dumps(payload)
    )
    producer.flush()
