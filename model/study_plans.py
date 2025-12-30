from sqlalchemy import Column, Integer, Date, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from core.setup import Base
import enum
from datetime import date


class DayOfWeek(enum.Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"


class StudyPlan(Base):
    """Represents a weekly study plan for a user."""
    __tablename__ = "study_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey(
        "users.id"), nullable=False, index=True)
    week_start_date = Column(Date, nullable=False, index=True)
    created_at = Column(Date, default=date.today)
    updated_at = Column(Date, default=date.today, onupdate=date.today)

    # Relationships - Removed lazy="joined" to handle it explicitly in queries for better control
    daily_sessions = relationship(
        "DailyStudySession",
        back_populates="study_plan",
        cascade="all, delete-orphan"
    )
    user = relationship("User", back_populates="study_plans")


class DailyStudySession(Base):
    """Represents a daily study session within a study plan."""
    __tablename__ = "daily_study_sessions"

    id = Column(Integer, primary_key=True, index=True)
    study_plan_id = Column(Integer, ForeignKey(
        "study_plans.id"), nullable=False, index=True)
    day_of_week = Column(Enum(DayOfWeek), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    tasks = Column(JSON, nullable=False)

    study_plan = relationship("StudyPlan", back_populates="daily_sessions")
    course = relationship("Course")
    topic = relationship("Topic")


class SubjectStrength(Base):
    """Represents user's strength rating for a subject."""
    __tablename__ = "subject_strengths"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey(
        "users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    strength = Column(Integer, nullable=False)

    user = relationship("User", back_populates="subject_strengths")
    course = relationship("Course")
