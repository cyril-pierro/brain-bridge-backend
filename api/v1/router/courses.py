import error
from controller.users import UserOp
from fastapi import APIRouter, Depends
from controller.courses import CourseOp
from schema.courses import (
    CourseIn,
    CourseOut,
    TopicIn,
    TopicOut,
    TopicOut2,
    CompletedCourseOut,
)
from schema import SuccessOut
from util.enum import UserRole
from service.auth import verify_access_token
from service.redis import Redis
from util.serialize import serialize_data

redis_instance = Redis()

router = APIRouter(tags=["Subjects"])
NOT_ALLOWED = "You are not authorized to access this route"


@router.post("/subjects", response_model=CourseOut)
async def add_subject(
    data: CourseIn,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)

    # Invalidate courses cache after adding new subject
    redis_instance.delete("all_subjects")

    return CourseOp.add(data)


@router.put("/subjects/{subject_id}", response_model=CourseOut)
async def update_subject(
    subject_id: int,
    data: CourseIn,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)

    # Invalidate courses cache after updating subject
    redis_instance.delete("all_subjects")

    return CourseOp.update(course_id=subject_id, course_data=data)


@router.delete("/subjects/{subject_id}", response_model=SuccessOut)
async def delete_subject(
    subject_id: int,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)

    CourseOp.delete(course_id=subject_id)

    # Invalidate courses cache after deleting subject
    redis_instance.delete("all_subjects")

    return {"message": "Subject deleted successfully"}


@router.get("/subjects", response_model=list[CourseOut])
async def get_subjects(
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (
        UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)
        or UserOp.is_user_role(user_id=user_id, role=UserRole.student.value)
    ):
        raise error.AuthenticationError(msg=NOT_ALLOWED)

    # OPTIMIZED: Cache course list for 30 minutes
    cache_key = "all_subjects"
    cached_subjects = redis_instance.get_json(cache_key)
    if cached_subjects:
        return cached_subjects

    subjects = CourseOp.get_courses()
    subjects_out = [CourseOut(**subject.__dict__) for subject in subjects]
    serialized_subjects = [serialize_data(subject.model_dump()) for subject in subjects_out]
    redis_instance.set_json(cache_key, serialized_subjects, expiry=1800)  # 30 minutes
    return subjects_out


@router.get("/subjects/{subject_id}", response_model=CourseOut)
async def get_subject(
    subject_id: int,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (
        UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)
        or UserOp.is_user_role(user_id=user_id, role=UserRole.student.value)
    ):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return CourseOp.get_course_by_id(course_id=subject_id)


@router.post("/subjects/{subject_id}/topics", response_model=TopicOut2)
async def add_topic(
    subject_id: int,
    data: TopicIn,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return CourseOp.add_topic(course_id=subject_id, topic_data=data)


@router.put("/topics/{topic_id}", response_model=TopicOut2)
async def update_topic(
    topic_id: int,
    data: TopicIn,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return CourseOp.update_topic(topic_id=topic_id, topic_data=data)


@router.delete("/topics/{topic_id}", response_model=SuccessOut)
async def delete_topic(
    topic_id: int,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    CourseOp.delete_topic(topic_id=topic_id)
    return {"message": "Topic deleted successfully"}


@router.get("/topics/{subject_id}", response_model=list[TopicOut])
async def get_topics(
    subject_id: int,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return CourseOp.get_topics(course_id=subject_id)


@router.get("/topics/{topic_id}/complete", response_model=SuccessOut)
async def mark_topic_as_complete(
    topic_id: int,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.student.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)

    CourseOp.mark_topic_as_complete(user_id=user_id, topic_id=topic_id)

    # Invalidate user's enrollment cache when topic completion changes
    # This ensures study plans reflect updated progress
    cache_key = f"user_enrolments:{user_id}"
    redis_instance.delete(cache_key)

    return {"message": "Topic marked as complete"}


@router.get("/topics/users/completed", response_model=list[CompletedCourseOut])
async def get_user_topics_completed(
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.student.value)):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return CourseOp.get_user_topics_completed(user_id=user_id)
