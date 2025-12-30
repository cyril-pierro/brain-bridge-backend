from sqlalchemy import Column, String, Integer, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import relationship
from core.setup import Base
from core.db import CreateDBSession
from error import InvalidRequestError


class Topic(Base):
    """
    Represents a single topic or lesson within a Course.
    """

    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    subject = Column(String, nullable=False)
    content = Column(Text, nullable=False)

    # OPTIMIZED: New column to define the sequence of the topic within the course.
    order = Column(Integer, nullable=False)

    # Relationships
    course = relationship("Course", back_populates="topics", lazy="selectin")
    user_completions = relationship(
        "UserTopicCompletion", back_populates="topic", lazy="selectin")

    video_resources = relationship("VideoResource", back_populates="topic", lazy="selectin")

    # Constraint: Ensures the 'order' is unique within the context of a single course
    __table_args__ = (
        UniqueConstraint("course_id", "order", name="_course_topic_order_uc"),
    )

    def __repr__(self):
        return f"<Topic {self.subject}>"

    def __str__(self):
        return f"{'Topic'}: {self.id} - {self.subject}"

    def save(self) -> "Topic":
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

    def update(self, **data) -> "Topic":
        with CreateDBSession() as session:
            for key, value in data.items():
                setattr(self, key, value)
            session.add(self)
            session.commit()
            session.refresh(self)
            return self

    @staticmethod
    def add(course_id: int, **data) -> "Topic":
        topic = Topic(course_id=course_id, **data)    
        return topic.save()

    @staticmethod
    def get_by_id(topic_id: int) -> "Topic":
        with CreateDBSession() as session:
            return session.query(Topic).filter(Topic.id == topic_id).first()

    @staticmethod
    def validate_topic(topic_id: int) -> "Topic":
        topic = Topic.get_by_id(topic_id)
        if not topic:
            raise InvalidRequestError(msg="Topic not found", code=404)
        return topic

    @staticmethod
    def get_topics_by_course(course_id: int) -> list["Topic"]:
        with CreateDBSession() as session:
            return session.query(Topic).filter(Topic.course_id == course_id).all()
