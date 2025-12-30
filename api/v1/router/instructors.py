import error
from controller.users import UserOp
from fastapi import APIRouter, Depends, BackgroundTasks, Query, responses
from controller.instructors import InstructorOp
from schema.instructors import (
    InstructorCourseSpecialtyOut,
    InstructorIn,
    InstructorOut,
    InstructorBookingIn,
    InstructorBookingOut,
)
from schema import SuccessOut
from util.enum import UserRole
from service.auth import verify_access_token, TokenManager
from fastapi import HTTPException
from uuid import UUID
from config.setting import settings

router = APIRouter(tags=["Instructors"])
NOT_ALLOWED = "You are not allowed to perform this action"


def verify_booking_token(token: str, expected_booking_id: int) -> dict:
    """Verify the booking confirmation token and return payload."""
    try:
        payload = TokenManager.decode_token(token)
        if payload.get("booking_id") != expected_booking_id:
            raise HTTPException(
                status_code=403, detail="Invalid token for this booking")
        if payload.get("action") != "confirm_booking":
            raise HTTPException(status_code=403, detail="Invalid token action")

        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.get("/instructors", response_model=list[InstructorOut])
def get_all_instructors(
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value):
        return InstructorOp.get_all_instructors()
    elif UserOp.is_user_role(user_id=user_id, role=UserRole.student.value):
        return InstructorOp.get_available_instructors()
    else:
        raise error.AuthenticationError(msg=NOT_ALLOWED)


@router.post("/instructors", response_model=InstructorOut)
def add_instructor(
    data: InstructorIn,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return InstructorOp.add_instructor(data=data)


@router.patch("/instructors/{instructor_id}/verify", response_model=SuccessOut)
def verify_instructors_details(
    instructor_id: UUID,
    auth_data: dict = Depends(verify_access_token),
):
    auth_user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=auth_user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    InstructorOp.verify_instructor(instructor_id=instructor_id)
    return {"message": "User verified successfully"}


@router.get("/instructors/{instructor_id}", response_model=InstructorOut)
def get_instructor(
    instructor_id: UUID,
    auth_data: dict = Depends(verify_access_token),
):
    auth_user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=auth_user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return InstructorOp.get_instructor(user_id=instructor_id)


@router.put("/instructors/{instructor_id}", response_model=InstructorOut)
def update_instructor(
    instructor_id: UUID,
    data: InstructorIn,
    auth_data: dict = Depends(verify_access_token),
):
    auth_user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=auth_user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return InstructorOp.update_instructor(user_id=instructor_id, data=data)


@router.delete("/instructors/{instructor_id}", response_model=SuccessOut)
def delete_instructor(
    instructor_id: UUID,
    auth_data: dict = Depends(verify_access_token),
):
    auth_user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=auth_user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    InstructorOp.delete_instructor(user_id=instructor_id)
    return {"message": "Instructor deleted successfully"}


@router.post(
    "/instructors/{instructor_id}/specialties/{course_id}",
    response_model=InstructorCourseSpecialtyOut,
)
def add_instructor_specialty(
    instructor_id: UUID,
    course_id: int,
    auth_data: dict = Depends(verify_access_token),
):
    auth_user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=auth_user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return InstructorOp.add_instructor_specialty(
        user_id=instructor_id, course_id=course_id
    )


@router.delete(
    "/instructors/{instructor_id}/specialties/{course_id}", response_model=SuccessOut
)
def delete_instructor_specialty(
    instructor_id: UUID,
    course_id: int,
    auth_data: dict = Depends(verify_access_token),
):
    auth_user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=auth_user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    InstructorOp.delete_instructor_specialty(
        user_id=instructor_id, course_id=course_id)
    return {"message": "Specialty deleted successfully"}


@router.post("/instructors/{instructor_id}/book", response_model=InstructorBookingOut)
def book_an_instructor(
    instructor_id: UUID,
    data: InstructorBookingIn,
    background_tasks: BackgroundTasks,
    token: dict = Depends(verify_access_token),
):
    auth_user_id = token.get("user_id", None)
    if not (UserOp.is_user_role(user_id=auth_user_id, role=UserRole.student.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    booked = InstructorOp.book_instructor(
        user_id=auth_user_id, instructor_id=instructor_id, data=data, background_tasks=background_tasks
    )
    return booked


@router.get("/book/{book_session_id}/email/cancel")
def cancel_book_session(
    book_session_id: int,
    token_param: str = Query(None, alias="token"),
):
    if not token_param:
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    # Use token-based authentication
    token_payload = verify_booking_token(token_param, book_session_id)
    instructor_id = token_payload.get("instructor_id")

    InstructorOp.cancel_book_session(
        book_session_id=book_session_id, instructor_id=instructor_id,
        for_tutor=True
    )
    return responses.RedirectResponse(
        url=f"{settings.FRONTEND_URI}/booking-confirmation?action=cancel"
    )


@router.get("/book/{book_session_id}/email/confirm")
def confirm_book_session(
    book_session_id: int,
    background_tasks: BackgroundTasks,
    token_param: str = Query(None, alias="token"),
):
    if not token_param:
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    # Use token-based authentication
    token_payload = verify_booking_token(token_param, book_session_id)
    instructor_id = token_payload.get("instructor_id")

    InstructorOp.confirm_book_session(
        instructor_id=str(instructor_id), book_session_id=book_session_id, background_tasks=background_tasks
    )
    return responses.RedirectResponse(
        url=f"{settings.FRONTEND_URI}/booking-confirmation?action=confirm"
    )


@router.get("/book/{book_session_id}/cancel", response_model=SuccessOut)
def cancel_book_session_by_student(
    book_session_id: int,
    token: dict = Depends(verify_access_token)
):
    user_id = token.get("user_id", None)
    if not UserOp.is_user_role(user_id, role=UserRole.student.value):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    InstructorOp.cancel_book_session(
        instructor_id=user_id,
        book_session_id=book_session_id
    )
    return {"message": "Book session has been successfully cancelled"}


@router.put("/book/{book_session_id}/reschedule", response_model=InstructorBookingOut)
def reschedule_book_session(
    book_session_id: int,
    data: InstructorBookingIn,
    background_tasks: BackgroundTasks,
    token: dict = Depends(verify_access_token)
):
    user_id = token.get("user_id", None)
    if not UserOp.is_user_role(user_id, role=UserRole.student.value):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    rescheduled_booking = InstructorOp.reschedule_book_session(
        user_id=user_id,
        book_session_id=book_session_id,
        data=data,
        background_tasks=background_tasks
    )
    return rescheduled_booking


@router.get("/book/{book_session_id}/complete", response_model=SuccessOut)
def complete_book_session(
    book_session_id: int,
    background_tasks: BackgroundTasks,
    token: dict = Depends(verify_access_token),
):
    auth_user_id = token.get("user_id", None)
    if not (UserOp.is_user_role(user_id=auth_user_id, role=UserRole.student.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    InstructorOp.complete_book_session(
        book_session_id=book_session_id, background_tasks=background_tasks
    )
    return {"message": "Book session completed successfully"}


@router.get("/instructors/bookings/bystudents", response_model=list[InstructorBookingOut])
def get_student_bookings(
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.student.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    data = InstructorOp.get_student_bookings(user_id=user_id)
    return data
