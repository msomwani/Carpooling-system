from sqlalchemy.orm import Session
from app.rides.models import Ride
from app.users.models import User


class RideService:

    @staticmethod
    def create_ride(
        db: Session,
        *,
        driver_id: str,
        source: str,
        destination: str,
        departure_time,
        total_seats: int
    ):
        # Ensure user is a driver
        driver = db.query(User).filter(User.id == driver_id).first()
        if not driver or driver.role != "driver":
            raise ValueError("Only drivers can create rides")

        ride = Ride(
            driver_id=driver_id,
            source=source,
            destination=destination,
            departure_time=departure_time,
            total_seats=total_seats,
            available_seats=total_seats
        )

        db.add(ride)
        db.commit()
        db.refresh(ride)
        return ride
