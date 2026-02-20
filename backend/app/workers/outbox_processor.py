import time
from datetime import datetime, UTC

from app.common.db import SessionLocal
from app.outbox.models import OutboxEvent
from app.common.kafka import publish_event


print("Outbox processor started...")


def _build_event_envelope(event: OutboxEvent) -> dict:
    payload = event.payload if isinstance(event.payload, dict) else {}
    occurred_at = event.created_at
    if occurred_at is None:
        occurred_at = datetime.now(UTC)

    return {
        "event_id": str(event.id),
        "event_type": event.event_type,
        "schema_version": 1,
        "occurred_at": occurred_at.isoformat(),
        "correlation_id": payload.get("correlation_id"),
        "payload": payload,
    }

while True:
    db = SessionLocal()

    try:
        events = (
            db.query(OutboxEvent)
            .filter(OutboxEvent.processed == False)
            .limit(10)
            .all()
        )

        for event in events:
            try:
                envelope = _build_event_envelope(event)
                booking_id = None
                if isinstance(event.payload, dict):
                    booking_id = event.payload.get("booking_id")
                publish_event(event.event_type, envelope, key=booking_id)
                event.processed = True
                db.commit()
            except Exception as e:
                print("Outbox publish failed:", e)
                db.rollback()

    finally:
        db.close()

    time.sleep(2)
