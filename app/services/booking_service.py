from sqlalchemy.orm import Session
from app.db.models import Booking
from app.schemas.booking import BookingCreate

class BookingService:
    """Service for handling interview bookings."""

    @staticmethod
    def create_booking(db: Session, booking_data: BookingCreate) -> Booking:
        """Save a new interview booking to the database."""
        db_booking = Booking(
            name=booking_data.name,
            email=booking_data.email,
            interview_date=booking_data.interview_date,
            interview_time=booking_data.interview_time,
        )
        db.add(db_booking)
        db.commit()
        db.refresh(db_booking)
        return db_booking