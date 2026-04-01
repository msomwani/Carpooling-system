import json
import uuid
from confluent_kafka import Consumer
from sqlalchemy.exc import IntegrityError

from app.common.db import SessionLocal
from app.notifications.service import NotificationService
from app.events.models import ProcessedEvent
from app.config.settings import settings

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

print("Notification consumer started...")

CONSUMER_NAME = "notification_consumer"

while True:
    msg = consumer.poll(1.0)

    if msg is None:
        continue
    if msg.error():
        print("Consumer error:", msg.error())
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
            elif topic == "booking.refunded" and payload.get("reason") == "MISSED_START":
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
            print(f"Skipping already processed event: {event_id}")
        except Exception as exc:
            db.rollback()
            print(f"Error processing notification: {exc}")
        finally:
            db.close()

    except Exception as exc:
        print("Invalid message format:", exc)

    consumer.commit()
