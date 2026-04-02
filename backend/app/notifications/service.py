import logging
from sqlalchemy.orm import Session
from app.users.models import User
import uuid

logger = logging.getLogger(__name__)


class NotificationService:
    # Email sending omitted – notifications are logged only (per project policy).
    # The original _send_email helper has been removed.

    @staticmethod
    def send_ride_created(db: Session, driver_id: str, ride_id: str):
        driver = db.query(User).filter(User.id == driver_id).first()
        if driver is not None and isinstance(driver.email, str):
            email_addr = driver.email
            logger.info("[Notification] Sending Ride Created message to %s", email_addr)
            # Email sending omitted – we just log the intent.
            logger.info(
                "[Notification] (email) would send ride‑created to %s", email_addr
            )

    @staticmethod
    def send_booking_confirmed(db: Session, passenger_id: str, ride_id: str):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger is not None and isinstance(passenger.email, str):
            logger.info(
                "[Notification] Sending Booking Confirmation message to %s",
                passenger.email,
            )
            # Email sending omitted – we simply log the confirmation.
            logger.info(
                "[Notification] (email) would send booking‑confirmation to %s",
                passenger.email,
            )

    @staticmethod
    def send_arrival_alert(db: Session, passenger_id: str, ride_id: str, minutes: int):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger is not None and isinstance(passenger.email, str):
            logger.info(
                "[Notification] Arrival alert to %s: Ride %s arriving in %d minutes",
                passenger.email,
                ride_id,
                minutes,
            )
            # Email sending omitted – we simply log the arrival alert.
            logger.info(
                "[Notification] (email) would send arrival alert to %s", passenger.email
            )

    @staticmethod
    def send_ride_started_to_driver(db: Session, driver_id: str, ride_id: str):
        driver = db.query(User).filter(User.id == driver_id).first()
        if driver is not None and isinstance(driver.email, str):
            logger.info("[Notification] Your ride %s has started.", ride_id)
            # Could add email similar pattern

    @staticmethod
    def send_pickup_ready_to_passenger(db: Session, passenger_id: str, ride_id: str):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger is not None and isinstance(passenger.email, str):
            logger.info(
                "[Notification] You are marked ready for pickup on ride %s.", ride_id
            )

    @staticmethod
    def send_boarded_to_passenger(db: Session, passenger_id: str, ride_id: str):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger is not None and isinstance(passenger.email, str):
            logger.info(
                "[Notification] You have been marked as boarded for ride %s.", ride_id
            )

    @staticmethod
    def send_ride_completed(db: Session, passenger_id: str, ride_id: str):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger is not None and isinstance(passenger.email, str):
            logger.info("[Notification] Ride %s is complete.", ride_id)

    @staticmethod
    def send_ride_missed_start(db: Session, passenger_id: str, ride_id: str):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger is not None and isinstance(passenger.email, str):
            logger.info(
                "[Notification] Ride %s did not start on time and your payment is being refunded.",
                ride_id,
            )

    @staticmethod
    def send_booking_cancelled(db: Session, passenger_id: str, ride_id: str):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger is not None and isinstance(passenger.email, str):
            logger.info(
                "[Notification] Booking Cancelled: Your booking for ride %s has been cancelled. Refund will be processed as per policy for %s",
                ride_id,
                passenger.email,
            )

    @staticmethod
    def send_ride_cancelled_to_passenger(db: Session, passenger_id: str, ride_id: str):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger is not None and isinstance(passenger.email, str):
            logger.info(
                "[Notification] ALERT: Your ride %s has been CANCELLED by the driver. A full refund has been initiated for %s",
                ride_id,
                passenger.email,
            )

    @staticmethod
    def send_ride_cancelled_to_driver(db: Session, driver_id: str, ride_id: str):
        driver = db.query(User).filter(User.id == driver_id).first()
        if driver is not None and isinstance(driver.email, str):
            logger.info(
                "[Notification] Your ride %s has been successfully cancelled.", ride_id
            )

    # Duplicate notification methods removed – original implementations retained above
