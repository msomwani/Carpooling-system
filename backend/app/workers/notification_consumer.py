import json
import uuid
from confluent_kafka import Consumer
from sqlalchemy.exc import IntegrityError

from app.common.db import SessionLocal
from app.notifications.service import NotificationService
from app.events.models import ProcessedEvent
from app.config.settings import settings
import logging
import signal
from app.common.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)
print("[worker] Notification worker started")

# Graceful shutdown flag
_should_stop = False


def _handle_sigterm(signum, frame):
    global _should_stop
    _should_stop = True
    logger.info("SIGTERM received – shutting down notification consumer...")


signal.signal(signal.SIGTERM, _handle_sigterm)

conf = {
    "bootstrap.servers": settings.kafka_bootstrap_servers,
    "group.id": "notification-workers-group",
    "auto.offset.reset": "earliest",
}

consumer = Consumer(conf)
consumer.subscribe(
    [
        "ride.created",
        "ride.started",
        "booking.confirmed",
        "booking.cancelled",
        "booking.cancelled_by_driver",
        "booking.ready_at_pickup",
        "booking.boarded",
        "booking.settled",
        "booking.refunded",
        "ride.cancelled",
    ]
)

logger.info("Notification consumer started...")

CONSUMER_NAME = "notification_consumer"

while not _should_stop:
    msg = consumer.poll(1.0)

    if msg is None:
        continue
    if msg.error():
        logger.error("Consumer error: %s", msg.error())
        continue

    try:
        decoded = json.loads(msg.value().decode("utf-8"))
        event_id = decoded.get("event_id")
        payload = decoded.get("payload", {})
        topic = msg.topic()

        db = SessionLocal()
        try:
            # Idempotency check
            if event_id:
                processed = ProcessedEvent(
                    event_id=uuid.UUID(event_id),
                    consumer_name=CONSUMER_NAME,
                )
                db.add(processed)
                db.flush()

            # Route to correct service method
            if topic == "ride.created":
                NotificationService.send_ride_created(
                    db, payload.get("driver_id"), payload.get("ride_id")
                )
            elif topic == "ride.started":
                NotificationService.send_ride_started_to_driver(
                    db, payload.get("driver_id"), payload.get("ride_id")
                )
            elif topic == "booking.settled":
                NotificationService.send_ride_completed(
                    db, payload.get("passenger_id"), payload.get("ride_id")
                )
            elif (
                topic == "booking.refunded" and payload.get("reason") == "MISSED_START"
            ):
                NotificationService.send_ride_missed_start(
                    db, payload.get("passenger_id"), payload.get("ride_id")
                )
            elif topic == "booking.confirmed":
                NotificationService.send_booking_confirmed(
                    db, payload.get("passenger_id"), payload.get("ride_id")
                )
            elif topic == "booking.cancelled":
                NotificationService.send_booking_cancelled(
                    db, payload.get("passenger_id"), payload.get("ride_id")
                )
            elif topic == "booking.cancelled_by_driver":
                NotificationService.send_ride_cancelled_to_passenger(
                    db, payload.get("passenger_id"), payload.get("ride_id")
                )
            elif topic == "booking.ready_at_pickup":
                NotificationService.send_pickup_ready_to_passenger(
                    db, payload.get("passenger_id"), payload.get("ride_id")
                )
            elif topic == "booking.boarded":
                NotificationService.send_boarded_to_passenger(
                    db, payload.get("passenger_id"), payload.get("ride_id")
                )
            elif topic == "ride.cancelled":
                NotificationService.send_ride_cancelled_to_driver(
                    db, payload.get("driver_id"), payload.get("ride_id")
                )

            db.commit()
        except IntegrityError:
            db.rollback()
            logger.info("Skipping already processed event: %s", event_id)
        except Exception as exc:
            db.rollback()
            logger.exception("Error processing notification: %s", exc)
        finally:
            db.close()

    except Exception as exc:
        logger.error("Invalid message format: %s", exc)

    consumer.commit()

logger.info("Notification consumer exiting – closing Kafka consumer.")
consumer.close()
