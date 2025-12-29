from pydantic import BaseModel
from schema.users import UserOut
from schema.courses import SimpleCourseOut
from util.enum import BookingType, BookingStatus, Gender
from datetime import datetime
from typing import Optional
from uuid import UUID


class InstructorCourseSpecialtyOut(BaseModel):
    course: SimpleCourseOut

    class Config:
        from_attributes = True


class InstructorOut(BaseModel):
    id: UUID
    user: UserOut
    years_of_experience: int
    location: str
    phone_number: Optional[str] = None
    hourly_rate: float
    expertise_field: str

    specialties: list[InstructorCourseSpecialtyOut]
    # reviews_received: list[ReviewOut]

    class Config:
        from_attributes = True


class InstructorUserIn(BaseModel):
    email: str
    first_name: str
    last_name: str
    gender: Gender
    profile_picture: Optional[str] = None


class InstructorIn(BaseModel):
    user: InstructorUserIn
    phone_number: Optional[str] = None
    location: str
    years_of_experience: int
    hourly_rate: float
    expertise_field: str
    specialties: Optional[list[int]] = []


class InstructorBookingIn(BaseModel):
    booking_type: BookingType
    scheduled_datetime: datetime
    duration_hours: int = 1


class InstructorBookingOut(BaseModel):
    id: int
    booking_type: BookingType
    status: BookingStatus
    scheduled_datetime: datetime
    duration_hours: int
    meeting_link: Optional[str] = None
    user: UserOut
    instructor: InstructorOut

    class Config:
        from_attributes = True
