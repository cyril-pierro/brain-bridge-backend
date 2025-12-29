from pydantic import BaseModel
from typing import Optional


class LearningHubIn(BaseModel):
    title: str
    youtube_url: str
    duration_seconds: Optional[int] = None


class LearningHubOut(BaseModel):
    id: int
    title: str
    youtube_url: str
    duration_seconds: Optional[int] = None

    class Config:
        from_attributes = True


class TopicVideoOut(BaseModel):
    id: int
    video_resources: list[LearningHubOut]

    class Config:
        from_attributes = True


class CourseVideOut(BaseModel):
    id: int
    name: str
    topics: list[TopicVideoOut]

    class Config:
        from_attributes = True


class EnrolmentVideoOut(BaseModel):
    id: int
    course: CourseVideOut

    class Config:
        from_attributes = True


class VideoLikeOut(BaseModel):
    id: int
    user_id: str
    video_id: int
    created_at: str

    class Config:
        from_attributes = True


class UserLikeOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    liked_at: str


class VideoAnalyticsOut(BaseModel):
    video_id: int
    title: str
    youtube_url: str
    duration_seconds: int
    topic_subject: str
    course_name: str
    likes_count: int
    liked_users: list[UserLikeOut]
    created_at: str

    class Config:
        from_attributes = True


class LearningHubVideoOut(BaseModel):
    """Schema for videos returned by the learning hub endpoint with like status."""
    id: int
    title: str
    youtube_url: str
    duration_seconds: Optional[int] = None
    liked: bool
    likes_count: int
    topic: dict  # Simplified topic info
    course: dict  # Simplified course info
