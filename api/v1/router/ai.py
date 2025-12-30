from fastapi import APIRouter, Depends
from controller.ai import AIOp
from schema.ai import AIQuestionIn, AIAnswerOut
from service.auth import verify_access_token
from controller.users import UserOp
from util.enum import UserRole

router = APIRouter(tags=["AI Assistant"])


@router.post("/ai/ask", response_model=AIAnswerOut)
def ask_ai_question(
    question_data: AIQuestionIn,
    auth_data: dict = Depends(verify_access_token),
):
    """
    Ask an AI question as a student.

    This endpoint allows authenticated students to ask questions to an AI tutor
    that provides academic assistance across various subjects.
    """
    user_id = auth_data.get("user_id", None)

    # Only students can ask AI questions
    if not UserOp.is_user_role(user_id=user_id, role=UserRole.student.value):
        from error import AuthenticationError
        raise AuthenticationError(msg="Only students can use the AI assistant")

    # Process the AI question
    result = AIOp.ask_ai(question_data)
    return result
