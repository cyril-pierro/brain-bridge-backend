from model.reviews import Review
from model.bookings import InstructorBooking
from schema.reviews import ReviewIn, ReviewOut, InstructorReviewsOut
from schema.users import UserOut
from model.users import User
from model.instructors import Instructor
from core.db import CreateDBSession
from util.enum import BookingStatus
from sqlalchemy.orm import joinedload
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
                joinedload(Review.reviewer),
                joinedload(Review.reviewed_instructor).joinedload(Instructor.user)
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
    def get_reviews_for_instructor(instructor_id: str) -> list[ReviewOut]:
        """Get all reviews for a specific instructor"""
        with CreateDBSession() as db:
            reviews = db.query(Review).options(
                joinedload(Review.reviewer),
                joinedload(Review.reviewed_instructor).joinedload(Instructor.user)
            ).filter(
                Review.reviewed_instructor_id == instructor_id
            ).all()

            # Manually construct ReviewOut objects to avoid DetachedInstanceError
            result = []
            for review in reviews:
                review_out = ReviewOut(
                    id=review.id,
                    rating=review.rating,
                    comment=review.comment,
                    reviewer=review.reviewer,  # Already loaded
                    reviewed_instructor=InstructorReviewsOut.from_instructor(review.reviewed_instructor)
                )
                result.append(review_out)
            return result

    @staticmethod
    def get_user_reviews(user_id: str) -> list[ReviewOut]:
        """Get all reviews given by a specific user"""
        with CreateDBSession() as db:
            reviews = db.query(Review).options(
                joinedload(Review.reviewer),
                joinedload(Review.reviewed_instructor).joinedload(Instructor.user)
            ).filter(
                Review.reviewer_user_id == user_id
            ).all()

            # Manually construct ReviewOut objects to avoid DetachedInstanceError
            result = []
            for review in reviews:
                review_out = ReviewOut(
                    id=review.id,
                    rating=review.rating,
                    comment=review.comment,
                    reviewer=review.reviewer,  # Already loaded
                    reviewed_instructor=InstructorReviewsOut.from_instructor(review.reviewed_instructor)
                )
                result.append(review_out)
            return result

    @staticmethod
    def get_completed_bookings_for_user(user_id: str) -> list[dict]:
        """Get completed bookings for a user that can be reviewed"""
        with CreateDBSession() as db:
            bookings = db.query(InstructorBooking).filter(
                InstructorBooking.user_id == user_id,
                InstructorBooking.status == BookingStatus.completed.value
            ).all()

            result = []
            for booking in bookings:
                # Check if already reviewed this booking
                existing_review = db.query(Review).filter(
                    Review.reviewer_user_id == user_id,
                    Review.booking_id == booking.id
                ).first()

                instructor = User.get_user_by_id(str(booking.instructor_id))
                result.append({
                    "booking_id": booking.id,
                    "instructor_id": booking.instructor_id,
                    "instructor_name": f"{instructor.full_name.split('-')[0]} {instructor.full_name.split('-')[1]}",
                    "booking_type": booking.booking_type.value,
                    "scheduled_datetime": booking.scheduled_datetime,
                    "already_reviewed": existing_review is not None
                })

            return result
