from pydantic import BaseModel
from typing import Optional
from schema.users import UserOut
from uuid import UUID


class ReviewIn(BaseModel):
    rating: int
    comment: Optional[str] = None


class InstructorReviewsOut(BaseModel):
    id: UUID
    user: UserOut
    years_of_experience: int
    location: Optional[str] = None

    @classmethod
    def from_instructor(cls, instructor):
        """Create InstructorReviewsOut from instructor object, avoiding lazy relationships"""
        # Use UserOut.from_orm to properly handle the user data
        user_out = UserOut.from_orm(instructor.user)

        return cls(
            id=instructor.id,
            user=user_out,
            years_of_experience=instructor.years_of_experience,
            location=instructor.location
        )


class ReviewOut(BaseModel):
    id: int
    rating: int
    comment: Optional[str] = None
    reviewer: UserOut
    reviewed_instructor: InstructorReviewsOut

    # No from_attributes to avoid DetachedInstanceError issues
