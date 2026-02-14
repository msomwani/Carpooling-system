import time

from app.common.db import SessionLocal
from app.outbox.models import OutboxEvent
from app.common.kafka import publish_event


print("Outbox processor started...")

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
                publish_event(event.event_type, event.payload)
                event.processed = True
                db.commit()
            except Exception as e:
                print("Outbox publish failed:", e)
                db.rollback()

    finally:
        db.close()

    time.sleep(2)

