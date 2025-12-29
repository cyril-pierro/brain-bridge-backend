from sqlalchemy import Column, Integer, ForeignKey, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from core.setup import Base
from core.db import CreateDBSession
from error import InvalidRequestError


class VideoLike(Base):
    """
    Represents a user's like on a video resource.
    """

    __tablename__ = "video_likes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    video_id = Column(Integer, ForeignKey("video_resources.id"),
                      nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    video = relationship("VideoResource", back_populates="likes")

    def save(self) -> "VideoLike":
        with CreateDBSession() as session:
            session.add(self)
            session.commit()
            session.refresh(self)
            return self

    def delete(self) -> bool:
        with CreateDBSession() as session:
            session.delete(self)
            session.commit()
            return True

    @staticmethod
    def get_by_user_and_video(user_id: str, video_id: int) -> "VideoLike":
        with CreateDBSession() as session:
            return (
                session.query(VideoLike)
                .filter(VideoLike.user_id == user_id,
                        VideoLike.video_id == video_id)
                .first()
            )

    @staticmethod
    def get_video_likes_count(video_id: int) -> int:
        with CreateDBSession() as session:
            return (
                session.query(VideoLike)
                .filter(VideoLike.video_id == video_id)
                .count()
            )


class VideoResource(Base):
    """
    Represents a supplementary video resource (e.g., YouTube URL) tied to a Topic.
    """

    __tablename__ = "video_resources"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    title = Column(String, nullable=False)
    youtube_url = Column(String, nullable=False)
    duration_seconds = Column(Integer, nullable=True)  # Optional metadata

    topic = relationship("Topic", back_populates="video_resources")
    likes = relationship("VideoLike", back_populates="video",
                        cascade="all, delete-orphan")

    def save(self) -> "VideoResource":
        with CreateDBSession() as session:
            session.add(self)
            session.commit()
            session.refresh(self)
            return self

    def update(self, **data) -> "VideoResource":
        with CreateDBSession() as session:
            for key, value in data.items():
                setattr(self, key, value)
            session.add(self)
            session.commit()
            session.refresh(self)
            return self

    def delete(self) -> bool:
        with CreateDBSession() as session:
            session.delete(self)
            session.commit()
            return True

    @staticmethod
    def get_by_id(video_id: int) -> "VideoResource":
        with CreateDBSession() as session:
            return (
                session.query(VideoResource)
                .filter(VideoResource.id == video_id)
                .first()
            )

    @staticmethod
    def validate_video(video_id: int) -> "VideoResource":
        video = VideoResource.get_by_id(video_id)
        if not video:
            raise InvalidRequestError(msg="Video not found", code=404)
        return video

    @staticmethod
    def add(topic_id: int, **data) -> "VideoResource":
        video = VideoResource(topic_id=topic_id, **data)
        return video.save()
