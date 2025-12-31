from typing import List, Dict, Any
from model.reviews import Review
from model.bookings import InstructorBooking
from schema.reviews import ReviewIn, ReviewOut, InstructorReviewsOut
from schema.users import UserOut
from model.users import User
from model.instructors import Instructor
from core.db import CreateDBSession
from util.enum import BookingStatus
from sqlalchemy.orm import selectinload
import error


class ReviewOp:

    @staticmethod
    def add_review(user_id: str, instructor_id: str, booking_id: int, review_data: ReviewIn) -> ReviewOut:
        """Add a review for a completed booking"""

        # Check if the booking exists and belongs to the user
        with CreateDBSession() as db:
            booking = db.query(InstructorBooking).filter(
                InstructorBooking.id == booking_id,
                InstructorBooking.user_id == user_id,
                InstructorBooking.instructor_id == instructor_id
            ).first()

            if not booking:
                raise error.ResourceNotFoundError("Booking not found")

            # Check if booking is completed
            if booking.status != BookingStatus.completed.value:
                raise error.InvalidRequestError(
                    "Can only review completed bookings")

            # Check if user already reviewed this booking
            existing_review = db.query(Review).filter(
                Review.reviewer_user_id == user_id,
                Review.booking_id == booking_id
            ).first()

            if existing_review:
                raise error.InvalidRequestError(
                    "You have already reviewed this booking session")

            # Create the review
            new_review = Review(
                reviewer_user_id=user_id,
                reviewed_instructor_id=instructor_id,
                booking_id=booking_id,
                rating=review_data.rating,
                comment=review_data.comment
            )

            db.add(new_review)
            db.commit()

            # Fetch the review with relationships loaded for serialization
            review_with_relations = db.query(Review).options(
                selectinload(Review.reviewer),
                selectinload(Review.reviewed_instructor).selectinload(Instructor.user)
            ).filter(Review.id == new_review.id).first()

            if not review_with_relations:
                raise error.ServerError("Failed to retrieve created review")

            # Create Pydantic objects directly to avoid DetachedInstanceError
            reviewer_out = UserOut.from_orm(review_with_relations.reviewer)
            instructor_out = InstructorReviewsOut.from_instructor(review_with_relations.reviewed_instructor)

            return ReviewOut(
                id=getattr(review_with_relations, 'id'),
                rating=getattr(review_with_relations, 'rating'),
                comment=getattr(review_with_relations, 'comment'),
                reviewer=reviewer_out,
                reviewed_instructor=instructor_out
            )

    @staticmethod
    def get_reviews_for_instructor(instructor_id: str) -> List[ReviewOut]:
        """Get all reviews for a specific instructor"""
        with CreateDBSession() as db:
            reviews = db.query(Review).options(
                selectinload(Review.reviewer),
                selectinload(Review.reviewed_instructor).selectinload(Instructor.user)
            ).filter(
                Review.reviewed_instructor_id == instructor_id
            ).all()

            # Use list comprehension for efficient construction
            return [
                ReviewOut(
                    id=review.id,
                    rating=review.rating,
                    comment=review.comment,
                    reviewer=review.reviewer,
                    reviewed_instructor=InstructorReviewsOut.from_instructor(review.reviewed_instructor)
                )
                for review in reviews
            ]

    @staticmethod
    def get_user_reviews(user_id: str) -> List[ReviewOut]:
        """Get all reviews given by a specific user"""
        with CreateDBSession() as db:
            reviews = db.query(Review).options(
                selectinload(Review.reviewer),
                selectinload(Review.reviewed_instructor).selectinload(Instructor.user)
            ).filter(
                Review.reviewer_user_id == user_id
            ).all()

            # Use list comprehension for efficient construction
            return [
                ReviewOut(
                    id=review.id,
                    rating=review.rating,
                    comment=review.comment,
                    reviewer=review.reviewer,
                    reviewed_instructor=InstructorReviewsOut.from_instructor(review.reviewed_instructor)
                )
                for review in reviews
            ]

    @staticmethod
    def get_completed_bookings_for_user(user_id: str) -> List[Dict[str, Any]]:
        """Get completed bookings for a user that can be reviewed"""
        with CreateDBSession() as db:
            # Get all completed bookings for the user
            bookings = db.query(InstructorBooking).filter(
                InstructorBooking.user_id == user_id,
                InstructorBooking.status == BookingStatus.completed.value
            ).all()

            if not bookings:
                return []

            # Get booking IDs for review check
            booking_ids = [b.id for b in bookings]

            # Batch check which bookings have reviews using subquery
            reviewed_booking_ids = {
                r.booking_id for r in db.query(Review.booking_id).filter(
                    Review.reviewer_user_id == user_id,
                    Review.booking_id.in_(booking_ids)
                ).all()
            }

            # Get instructor IDs and batch load instructors
            instructor_ids = list(set(str(b.instructor_id) for b in bookings))
            instructors = {
                str(inst.id): inst for inst in db.query(User).filter(
                    User.id.in_(instructor_ids)
                ).all()
            }

            # Use list comprehension for efficient construction
            return [
                {
                    "booking_id": booking.id,
                    "instructor_id": booking.instructor_id,
                    "instructor_name": ReviewOp._format_instructor_name(
                        instructors.get(str(booking.instructor_id))
                    ),
                    "booking_type": booking.booking_type.value,
                    "scheduled_datetime": booking.scheduled_datetime,
                    "already_reviewed": booking.id in reviewed_booking_ids
                }
                for booking in bookings
            ]

    @staticmethod
    def _format_instructor_name(instructor: User) -> str:
        """Helper method to format instructor name from full_name"""
        if not instructor or not instructor.full_name:
            return "Unknown Instructor"

        # Split by '-' and reconstruct as "First Last"
        parts = instructor.full_name.split('-')
        return f"{parts[0]} {parts[1] if len(parts) > 1 else ''}".strip()
