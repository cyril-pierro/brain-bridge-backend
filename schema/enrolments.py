from pydantic import BaseModel
from schema.courses import CourseOut
from uuid import UUID


class EnrolmentCourseOut(BaseModel):
    user_id: UUID
    course: CourseOut

    class Config:
        from_attributes = True


class EnrolmentCourseIn(BaseModel):
    course_ids: list[int]
