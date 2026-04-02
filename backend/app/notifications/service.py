import logging
from sqlalchemy.orm import Session
from app.users.models import User
import uuid

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    def send_ride_created(db: Session, driver_id: str, ride_id: str):
        driver = db.query(User).filter(User.id == driver_id).first()
        if driver and driver.email:
            logger.info(
                "[Notification] Sending Ride Created message to %s", driver.email
            )
            # Real email call here later

    @staticmethod
    def send_booking_confirmed(db: Session, passenger_id: str, ride_id: str):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger and passenger.email:
            logger.info(
                "[Notification] Sending Booking Confirmation message to %s",
                passenger.email,
            )

    @staticmethod
    def send_ride_started_to_driver(db: Session, driver_id: str, ride_id: str):
        driver = db.query(User).filter(User.id == driver_id).first()
        if driver and driver.email:
            logger.info("[Notification] Your ride %s has started.", ride_id)

    @staticmethod
    def send_pickup_ready_to_passenger(db: Session, passenger_id: str, ride_id: str):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger and passenger.email:
            logger.info(
                "[Notification] You are marked ready for pickup on ride %s.", ride_id
            )

    @staticmethod
    def send_boarded_to_passenger(db: Session, passenger_id: str, ride_id: str):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger and passenger.email:
            logger.info(
                "[Notification] You have been marked as boarded for ride %s.", ride_id
            )

    @staticmethod
    def send_ride_completed(db: Session, passenger_id: str, ride_id: str):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger and passenger.email:
            logger.info("[Notification] Ride %s is complete.", ride_id)

    @staticmethod
    def send_ride_missed_start(db: Session, passenger_id: str, ride_id: str):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger and passenger.email:
            logger.info(
                "[Notification] Ride %s did not start on time and your payment is being refunded.",
                ride_id,
            )

    @staticmethod
    def send_booking_cancelled(db: Session, passenger_id: str, ride_id: str):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger and passenger.email:
            logger.info(
                "[Notification] Booking Cancelled: Your booking for ride %s has been cancelled. Refund will be processed as per policy for %s",
                ride_id,
                passenger.email,
            )

    @staticmethod
    def send_ride_cancelled_to_passenger(db: Session, passenger_id: str, ride_id: str):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger and passenger.email:
            logger.info(
                "[Notification] ALERT: Your ride %s has been CANCELLED by the driver. A full refund has been initiated for %s",
                ride_id,
                passenger.email,
            )

    @staticmethod
    def send_ride_cancelled_to_driver(db: Session, driver_id: str, ride_id: str):
        driver = db.query(User).filter(User.id == driver_id).first()
        if driver and driver.email:
            logger.info(
                "[Notification] Your ride %s has been successfully cancelled.", ride_id
            )
