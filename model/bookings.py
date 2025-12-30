from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    Enum,
    DateTime,
    UUID,
    String,
)
from sqlalchemy.orm import relationship
from util.enum import BookingStatus, BookingType
from core.setup import Base
from core.db import CreateDBSession


class InstructorBooking(Base):
    """
    Represents a booked session between a student (User) and an Instructor.
    """

    __tablename__ = "instructor_bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    instructor_id = Column(UUID, ForeignKey("instructors.id"), nullable=False)
    # course_id = Column(
    #     Integer, ForeignKey("courses.id"), nullable=True
    # )  # Optional: booking related to a specific course

    booking_type = Column(Enum(BookingType), nullable=False)
    scheduled_datetime = Column(
        DateTime, nullable=False
    )  # The date and time of the booked session
    duration_hours = Column(Integer, nullable=False, default=1)  # Duration in hours
    status = Column(
        Enum(BookingStatus), nullable=False, default=BookingStatus.pending.value
    )
    meeting_link = Column(String(500), nullable=True)

    # Relationships
    user = relationship("User", back_populates="bookings", lazy="selectin")
    instructor = relationship("Instructor", back_populates="booked_sessions", lazy="selectin")
    # course = relationship("Course")

    def save(self) -> "InstructorBooking":
        with CreateDBSession() as db:
            db.add(self)
            db.commit()
            db.refresh(self)
            return self

    def update(self, **kwargs) -> "InstructorBooking":
        for key, value in kwargs.items():
            setattr(self, key, value)
        return self.save()

    def delete(self) -> bool:
        with CreateDBSession() as db:
            db.delete(self)
            db.commit()
            return True

    @staticmethod
    def add(data: dict) -> "InstructorBooking":
        new_booking = InstructorBooking(**data)
        return new_booking.save()

    @staticmethod
    def get_booking_session(book_session_id: int) -> "InstructorBooking":
        with CreateDBSession() as db:
            return (
                db.query(InstructorBooking)
                .filter(InstructorBooking.id == book_session_id)
                .first()
            )

    @staticmethod
    def get_bookings_for_student(user_id: str) -> list["InstructorBooking"]:
        """Get all bookings for a specific student."""
        with CreateDBSession() as db:
            return (
                db.query(InstructorBooking)
                .filter(InstructorBooking.user_id == user_id)
                .order_by(InstructorBooking.scheduled_datetime.desc())
                .all()
            )
