from sqlalchemy import (
    Column,
    String,
    Integer,
    Numeric,
    ForeignKey,
    UUID,
)
from sqlalchemy.orm import relationship
from core.setup import Base
from core.db import CreateDBSession


class Instructor(Base):
    """
    Holds specialized data for users with the 'instructor' role.
    Uses one-to-one relationship with the User table.
    """

    __tablename__ = "instructors"

    # Primary Key is also a Foreign Key to the User table
    id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    # Instructor-specific fields
    years_of_experience = Column(Integer, default=0, nullable=False)
    hourly_rate = Column(Numeric(precision=10, scale=2), default=0.00, nullable=False)
    location = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)

    # Could be a summary, e.g., "Quantum Physics, Advanced Calculus"
    expertise_field = Column(String, nullable=True)

    # Relationships
    # One-to-one link back to the User object
    user = relationship(
        "User",
        back_populates="instructor_profile",
        uselist=False,
        lazy="joined",
        cascade="all, delete-orphan",
        single_parent=True,
    )

    # Many-to-Many relationship to Courses (courses they major in/specialize in
    specialties = relationship(
        "InstructorCourseSpecialty",
        back_populates="instructor",
        lazy="joined",
        cascade="all, delete-orphan",
    )

    reviews_received = relationship(
        "Review",
        back_populates="reviewed_instructor",
        lazy="joined",
        cascade="all, delete-orphan",
    )
    booked_sessions = relationship(
        "InstructorBooking",
        back_populates="instructor",
        lazy="joined",
        cascade="all, delete-orphan",
    )

    def save(self) -> "Instructor":
        with CreateDBSession() as db:
            db.add(self)
            db.commit()
            db.refresh(self)
            return self

    def delete(self) -> bool:
        with CreateDBSession() as db:
            db.delete(self)
            db.commit()
            return True

    def update(self, data: dict) -> "Instructor":
        for key, value in data.items():
            setattr(self, key, value)
        return self.save()

    @staticmethod
    def get_instructor_by_user_id(user_id: int) -> "Instructor":
        with CreateDBSession() as db:
            return db.query(Instructor).filter(Instructor.id == user_id).first()

    @staticmethod
    def get_all_instructors() -> list["Instructor"]:
        with CreateDBSession() as db:
            return db.query(Instructor).all()

    @staticmethod
    def add_instructor(data: dict) -> "Instructor":
        new_instructor = Instructor(**data)
        return new_instructor.save()
