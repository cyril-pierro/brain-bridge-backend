import error
from controller.users import UserOp
from fastapi import APIRouter, Depends
from controller.questions import QuestionOp
from schema.questions import (
    FlashcardIn,
    FlashcardOut,
)
from schema import SuccessOut
from util.enum import UserRole
from service.auth import verify_access_token

router = APIRouter(tags=["Flashcards"])
NOT_ALLOWED = "You are not authorized to access this route"


@router.post("/flashcards/{course_id}", response_model=FlashcardOut)
def add_flashcard(
    course_id: int,
    data: FlashcardIn,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (
        UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)
        or UserOp.is_user_role(user_id=user_id, role=UserRole.instructor.value)
    ):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return QuestionOp.add_flashcard(course_id=course_id, flashcard_data=data)


@router.put("/flashcards/{flashcard_id}", response_model=FlashcardOut)
def update_flashcard(
    flashcard_id: int,
    data: FlashcardIn,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (
        UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)
        or UserOp.is_user_role(user_id=user_id, role=UserRole.instructor.value)
    ):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return QuestionOp.update_flashcard(flashcard_id=flashcard_id, flashcard_data=data)


@router.delete("/flashcards/{flashcard_id}", response_model=SuccessOut)
def delete_flashcard(
    flashcard_id: int,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (
        UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)
        or UserOp.is_user_role(user_id=user_id, role=UserRole.instructor.value)
    ):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    QuestionOp.delete_flashcard(flashcard_id=flashcard_id)
    return {"message": "Flashcard deleted successfully"}


@router.get("/flashcards/{course_id}", response_model=list[FlashcardOut])
def get_flashcards_by_course_id(
    course_id: int,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (
        UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)
        or UserOp.is_user_role(user_id=user_id, role=UserRole.student.value)
    ):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return QuestionOp.get_flashcards(course_id=course_id)
