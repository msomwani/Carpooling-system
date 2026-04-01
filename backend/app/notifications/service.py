import logging
from sqlalchemy.orm import Session
from app.users.models import User
import uuid

logger=logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def send_ride_created(db: Session, driver_id: str, ride_id: str):
        driver = db.query(User).filter(User.id == driver_id).first()
        if driver and driver.email:
            print(f" [Notification] Sending Ride Created email to {driver.email}")
            # Real email call here later

    @staticmethod
    def send_booking_confirmed(db: Session, passenger_id: str, ride_id: str):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger and passenger.email:
            print(f"[Notification] Sending Booking Confirmation email to {passenger.email}")

    @staticmethod
    def send_ride_started_to_driver(db: Session, driver_id: str, ride_id: str):
        driver = db.query(User).filter(User.id == driver_id).first()
        if driver and driver.email:
            print(f"[Notification] Your ride {ride_id} has started.")

    @staticmethod
    def send_pickup_ready_to_passenger(db: Session, passenger_id: str, ride_id: str):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger and passenger.email:
            print(f"[Notification] You are marked ready for pickup on ride {ride_id}.")

    @staticmethod
    def send_boarded_to_passenger(db: Session, passenger_id: str, ride_id: str):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger and passenger.email:
            print(f"[Notification] You have been marked as boarded for ride {ride_id}.")

    @staticmethod
    def send_ride_completed(db: Session, passenger_id: str, ride_id: str):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger and passenger.email:
            print(f"[Notification] Ride {ride_id} is complete.")

    @staticmethod
    def send_ride_missed_start(db: Session, passenger_id: str, ride_id: str):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger and passenger.email:
            print(f"[Notification] Ride {ride_id} did not start on time and your payment is being refunded.")

    @staticmethod
    def send_booking_cancelled(db: Session, passenger_id: str, ride_id: str):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger and passenger.email:
            print(f"[Notification] Booking Cancelled: Your booking for ride {ride_id} has been cancelled. Refund will be processed as per policy for {passenger.email}")

    @staticmethod
    def send_ride_cancelled_to_passenger(db: Session, passenger_id: str, ride_id: str):
        passenger = db.query(User).filter(User.id == passenger_id).first()
        if passenger and passenger.email:
            print(f"[Notification] ALERT: Your ride {ride_id} has been CANCELLED by the driver. A full refund has been initiated for {passenger.email}")

    @staticmethod
    def send_ride_cancelled_to_driver(db: Session, driver_id: str, ride_id: str):
        driver = db.query(User).filter(User.id == driver_id).first()
        if driver and driver.email:
            print(f"[Notification] Your ride {ride_id} has been successfully cancelled.")
