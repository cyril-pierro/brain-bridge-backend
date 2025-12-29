from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, Boolean, UUID, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.setup import Base
from core.db import CreateDBSession


class UserTopicCompletion(Base):
    """
    Tracks the completion status of a Topic by a specific User (User <-> Topic).
    """

    __tablename__ = "user_topic_completions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)

    # OPTIMIZED: Explicit default value for clarity
    is_completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="topic_completions")
    topic = relationship("Topic", back_populates="user_completions", lazy="joined")

    # Constraint: Ensures a user can only have one completion record per topic
    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="_user_topic_completion_uc"),
    )

    def save(self):
        with CreateDBSession() as session:
            session.add(self)
            session.commit()
            session.refresh(self)
            return self

    @staticmethod
    def get_completion(user_id: UUID, topic_id: int) -> "UserTopicCompletion":
        with CreateDBSession() as session:
            return (
                session.query(UserTopicCompletion)
                .filter(
                    UserTopicCompletion.user_id == user_id,
                    UserTopicCompletion.topic_id == topic_id,
                )
                .first()
            )

    @staticmethod
    def get_user_completions(user_id: UUID) -> list["UserTopicCompletion"]:
        with CreateDBSession() as session:
            return (
                session.query(UserTopicCompletion)
                .filter(UserTopicCompletion.user_id == user_id)
                .all()
            )

    @staticmethod
    def mark_topic_as_complete(user_id: UUID, topic_id: int) -> "UserTopicCompletion":
        completion = UserTopicCompletion.get_completion(user_id, topic_id)
        if not completion:
            completion = UserTopicCompletion(
                user_id=user_id, topic_id=topic_id, is_completed=True, completed_at=func.now()
            )
        elif not completion.is_completed:
            completion.is_completed = True
            completion.completed_at = func.now()
        return completion.save()
