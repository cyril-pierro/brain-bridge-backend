import error
from controller.users import UserOp
from fastapi import APIRouter, Depends
from controller.questions import QuestionOp
from schema.questions import (
    QuizQuestionIn,
    QuizAnswerIn,
    QuizAnswerOut,
    QuizQuestionOut,
)
from schema import SuccessOut
from util.enum import UserRole
from service.auth import verify_access_token

router = APIRouter(tags=["Quiz or Tests"])
NOT_ALLOWED = "You are not authorized to access this route"


@router.post("/quiz/{course_id}", response_model=QuizQuestionOut)
def add_quiz_question(
    course_id: int,
    data: QuizQuestionIn,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return QuestionOp.add_quiz_question(course_id=course_id, quiz_data=data)


@router.put("/quiz/{question_id}", response_model=QuizQuestionOut)
def update_quiz_question(
    question_id: int,
    data: QuizQuestionIn,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return QuestionOp.update_quiz_question(question_id=question_id, quiz_data=data)


@router.delete("/quiz/{question_id}", response_model=SuccessOut)
def delete_quiz_question(
    question_id: int,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    QuestionOp.delete_quiz_question(question_id=question_id)
    return {"message": "Quiz question deleted successfully"}


@router.get("/quiz/{course_id}", response_model=list[QuizQuestionOut])
def get_quiz_questions_by_course_id(
    course_id: int,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (
        UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)
        or UserOp.is_user_role(user_id=user_id, role=UserRole.student.value)
    ):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return QuestionOp.get_quiz_questions(course_id=course_id)


@router.post("/quiz/{question_id}/answer", response_model=QuizAnswerOut)
def add_quiz_answer(
    question_id: int,
    data: QuizAnswerIn,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return QuestionOp.add_quiz_answer(question_id=question_id, answer_data=data)


@router.put("/quiz/{question_id}/answer", response_model=QuizAnswerOut)
def update_quiz_answer(
    answer_id: int,
    data: QuizAnswerIn,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return QuestionOp.update_quiz_answer(answer_id=answer_id, answer_data=data)


@router.delete("/quiz/{answer_id}", response_model=SuccessOut)
def delete_quiz_answer(
    answer_id: int,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    QuestionOp.delete_quiz_answer(answer_id=answer_id)
    return {"message": "Quiz answer deleted successfully"}
