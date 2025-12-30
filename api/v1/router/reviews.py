from fastapi import APIRouter, Depends
from controller.reviews import ReviewOp
from schema.reviews import ReviewIn, ReviewOut
from service.auth import verify_access_token
from controller.users import UserOp
from util.enum import UserRole

router = APIRouter(tags=["Reviews"])


@router.post("/reviews/{instructor_id}/booking/{booking_id}", response_model=ReviewOut)
def add_review_for_booking(
    instructor_id: str,
    booking_id: int,
    review_data: ReviewIn,
    auth_data: dict = Depends(verify_access_token),
):
    """
    Add a review for a completed booking.

    Students can review instructors after completing their booked sessions.
    """
    user_id = auth_data.get("user_id", None)

    # Only students can add reviews
    if not UserOp.is_user_role(user_id=user_id, role=UserRole.student.value):
        from error import AuthenticationError
        raise AuthenticationError(msg="Only students can add reviews")

    return ReviewOp.add_review(user_id, instructor_id, booking_id, review_data)


@router.get("/reviews/instructor/{instructor_id}", response_model=list[ReviewOut])
def get_reviews_for_instructor(
    instructor_id: str,
    auth_data: dict = Depends(verify_access_token),
):
    """
    Get all reviews for a specific instructor.

    Available to all authenticated users.
    """
    return ReviewOp.get_reviews_for_instructor(instructor_id)


@router.get("/reviews/my-reviews", response_model=list[ReviewOut])
def get_my_reviews(
    auth_data: dict = Depends(verify_access_token),
):
    """
    Get all reviews given by the current user.

    Only accessible by the user who created the reviews.
    """
    user_id = auth_data.get("user_id", None)
    return ReviewOp.get_user_reviews(user_id)


@router.get("/reviews/my-completed-bookings")
def get_completed_bookings_for_review(
    auth_data: dict = Depends(verify_access_token),
):
    """
    Get completed bookings that the user can review.

    Returns bookings that are completed and shows which ones have already been reviewed.
    """
    user_id = auth_data.get("user_id", None)

    # Only students can access this
    if not UserOp.is_user_role(user_id=user_id, role=UserRole.student.value):
        from error import AuthenticationError
        raise AuthenticationError(msg="Only students can access booking reviews")

    return ReviewOp.get_completed_bookings_for_user(user_id)
