import error
from controller.users import UserOp
from controller.hub import LearningHubOp
from fastapi import APIRouter, Depends
from schema.hub import (LearningHubIn, LearningHubOut, LearningHubVideoOut,
                        VideoAnalyticsOut)
from schema import SuccessOut
from util.enum import UserRole
from service.auth import verify_access_token

router = APIRouter(tags=["Learning Hub"])
NOT_ALLOWED = "You are not authorized to access this route"


@router.post("/learning-hub/{topic_id}", response_model=LearningHubOut)
def add_learning_hub(
    topic_id: int,
    data: LearningHubIn,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return LearningHubOp.add_video(topic_id=topic_id, data=data)


@router.get("/learning-hub/{video_id}", response_model=LearningHubOut)
def get_learning_hub(
    video_id: int,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (
        UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)
        or UserOp.is_user_role(user_id=user_id, role=UserRole.student.value)
    ):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return LearningHubOp.get_video(video_id=video_id)


@router.put("/learning-hub/{video_id}", response_model=LearningHubOut)
def update_learning_hub(
    video_id: int,
    data: LearningHubIn,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return LearningHubOp.update_video(video_id=video_id, data=data)


@router.delete("/learning-hub/{video_id}", response_model=SuccessOut)
def delete_learning_hub(
    video_id: int,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    LearningHubOp.delete_video(video_id=video_id)
    return {"message": "Video deleted successfully"}


@router.get("/learning-hub", response_model=list[LearningHubVideoOut])
def get_all_videos_for_courses_enroled(
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.student.value) or UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return LearningHubOp.get_all_videos_for_courses_enroled(user_id=user_id)


@router.post("/learning-hub/{video_id}/like", response_model=dict)
def toggle_video_like(
    video_id: int,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.student.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return LearningHubOp.toggle_like(user_id=user_id, video_id=video_id)


@router.get("/learning-hub/{video_id}/like", response_model=dict)
def get_video_like_status(
    video_id: int,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.student.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return LearningHubOp.get_like_status(user_id=user_id, video_id=video_id)
