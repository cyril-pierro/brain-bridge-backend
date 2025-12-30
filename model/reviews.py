from sqlalchemy import (
    Column,
    Text,
    Integer,
    ForeignKey,
    DateTime,
    UniqueConstraint,
    func,
    UUID
)
from sqlalchemy.orm import relationship
from core.setup import Base


class Review(Base):
    """
    Represents a review given by a student (User) to an Instructor.
    """

    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    # The student/user giving the review
    reviewer_user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    # The instructor being reviewed (Note: Instructor.id is also a User.id)
    reviewed_instructor_id = Column(
        UUID, ForeignKey("instructors.id"), nullable=False
    )
    # Link the review to a specific booking session
    booking_id = Column(Integer, ForeignKey("instructor_bookings.id"), nullable=False)
    # Optional: Link the review to a specific course if relevant
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)

    # Review Data
    rating = Column(Integer, nullable=False)  # e.g., 1 to 5 stars
    comment = Column(Text, nullable=True)  # Detailed textual feedback
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    reviewer = relationship(
        "User", back_populates="reviews_given", foreign_keys=[reviewer_user_id],
        lazy="selectin"
    )
    reviewed_instructor = relationship(
        "Instructor",
        back_populates="reviews_received",
        lazy="selectin",
        foreign_keys=[reviewed_instructor_id],
    )
    course = relationship("Course")  # To access details of the course, if provided

    # Constraint: A student can review each booking session only once.
    __table_args__ = (
        UniqueConstraint(
            "reviewer_user_id",
            "booking_id",
            name="_user_booking_review_uc",
        ),
    )
