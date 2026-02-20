import json
import uuid
from datetime import datetime, UTC

from confluent_kafka import Consumer
from sqlalchemy.exc import IntegrityError

from app.bookings.history_model import BookingHistory
from app.common.db import SessionLocal
from app.common.kafka import publish_event
from app.config.settings import settings
from app.events.models import ProcessedEvent
from app.notifications.models import NotificationAttempt

conf = {
    "bootstrap.servers": settings.kafka_bootstrap_servers,
    "group.id": "booking-workers-test-1",
    "auto.offset.reset": "earliest",
}

consumer = Consumer(conf)
consumer.subscribe(["booking.confirmed", "booking.cancelled"])

print("Booking consumer started...")

MAX_RETRIES = 3
CONSUMER_NAME = "booking_consumer"


def _normalize_event(topic: str, raw_event: dict) -> dict:
    if isinstance(raw_event, dict) and "event_id" in raw_event and "payload" in raw_event:
        return raw_event

    # Backward compatibility for old payload-only events.
    now_iso = datetime.now(UTC).isoformat()
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": topic,
        "schema_version": 1,
        "occurred_at": now_iso,
        "correlation_id": raw_event.get("correlation_id") if isinstance(raw_event, dict) else None,
        "payload": raw_event if isinstance(raw_event, dict) else {},
    }


def _record_booking_history(db, topic: str, event: dict, payload: dict):
    booking_id = payload.get("booking_id")
    ride_id = payload.get("ride_id")
    passenger_id = payload.get("passenger_id")
    if not booking_id or not ride_id or not passenger_id:
        return

    action = "BOOKING_CONFIRMED" if topic == "booking.confirmed" else "BOOKING_CANCELLED"
    occurred_at_raw = event.get("occurred_at")
    try:
        occurred_at = datetime.fromisoformat(occurred_at_raw) if occurred_at_raw else datetime.now(UTC)
    except ValueError:
        occurred_at = datetime.now(UTC)

    history = BookingHistory(
        event_id=uuid.UUID(event["event_id"]),
        user_id=uuid.UUID(passenger_id),
        booking_id=uuid.UUID(booking_id),
        ride_id=uuid.UUID(ride_id),
        action=action,
        occurred_at=occurred_at,
        correlation_id=event.get("correlation_id"),
        details={
            "seats_booked": payload.get("seats_booked"),
            "seats_returned": payload.get("seats_returned"),
        },
    )
    db.add(history)


def _record_notification(db, event_id: str, topic: str):
    status = "SENT"
    message = f"Console notification for {topic}"
    print(message)
    # TODO: Replace console channel with SendGrid/Twilio providers later.
    attempt = NotificationAttempt(
        event_id=uuid.UUID(event_id),
        channel="console",
        status=status,
        error=None,
    )
    db.add(attempt)


while True:
    msg = consumer.poll(1.0)

    if msg is None:
        continue
    if msg.error():
        print("Consumer error:", msg.error())
        continue

    raw_value = msg.value()
    if raw_value is None:
        print("Received empty message")
        consumer.commit()
        continue

    try:
        decoded = json.loads(raw_value.decode("utf-8"))
    except Exception as exc:
        print("Invalid JSON message:", exc)
        consumer.commit()
        continue

    event = _normalize_event(msg.topic(), decoded)
    payload = event.get("payload", {})

    retries = 0
    success = False

    while retries < MAX_RETRIES and not success:
        db = SessionLocal()
        try:
            processed = ProcessedEvent(
                event_id=uuid.UUID(event["event_id"]),
                consumer_name=CONSUMER_NAME,
            )
            db.add(processed)
            db.flush()

            _record_booking_history(db, msg.topic(), event, payload)
            _record_notification(db, event["event_id"], msg.topic())

            db.commit()
            success = True
        except IntegrityError:
            db.rollback()
            success = True
            print("Skipping already processed event:", event["event_id"])
        except Exception as exc:
            db.rollback()
            retries += 1
            print(f"Retry {retries} failed:", exc)
        finally:
            db.close()

    if not success:
        print(f"Moving to DLQ after {MAX_RETRIES} retries:", event)
        key = payload.get("booking_id") if isinstance(payload, dict) else None
        publish_event("booking.dlq", event, key=key)

    consumer.commit()
