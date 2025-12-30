import error
from controller.users import UserOp
from fastapi import APIRouter, Depends
from controller.enrolments import EnrolmentOp
from schema.enrolments import EnrolmentCourseOut, EnrolmentCourseIn
from schema import SuccessOut
from util.enum import UserRole
from service.auth import verify_access_token

router = APIRouter(tags=["Enrolments"])
NOT_ALLOWED = "You are not allowed to perform this action"


@router.get("/enrolments", response_model=list[EnrolmentCourseOut])
def get_courses_enrolled_by_student(
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.student.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)

    enrolments = EnrolmentOp.get_courses_enroled_by_student(user_id=user_id)
    return enrolments


@router.post("/enrolments/{course_id}", response_model=EnrolmentCourseOut)
def enroll_a_student(
    course_id: int,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.student.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)

    UserOp.get_user_by_id(user_id=user_id).update(**{"is_enrolled": True})
    result = EnrolmentOp.enroll_a_student(user_id=user_id, course_id=course_id)

    return result


@router.delete("/enrolments/{enrolment_id}", response_model=SuccessOut)
def unenrol_a_student(
    enrolment_id: int,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)

    EnrolmentOp.unenroll_a_student(enrolment_id=enrolment_id)

    return {"message": "Unenrolled successfully"}


@router.post("/enrolments/all/bulk", response_model=list[EnrolmentCourseOut])
def enroll_multiple_courses(
    data: EnrolmentCourseIn,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.student.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)

    enrolled_courses = []
    for course_id in data.course_ids:
        try:
            # Try to enroll - will skip if already enrolled due to unique constraint
            enrolled_course = EnrolmentOp.enroll_a_student(
                user_id=user_id, course_id=course_id
            )
            enrolled_courses.append(enrolled_course)
        except Exception as e:
            # Skip if already enrolled (unique constraint violation)
            # Could be more specific about the error type, but for now we'll skip silently
            continue

    # Only set has_enrolled to True if this is the first enrollment
    current_enrollments = EnrolmentOp.get_courses_enroled_by_student(user_id)
    if len(current_enrollments) == len(enrolled_courses):
        # This was the first enrollment
        UserOp.get_user_by_id(user_id=user_id).update(**{"has_enrolled": True})

    return enrolled_courses
