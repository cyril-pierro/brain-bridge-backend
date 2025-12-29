from sqlalchemy import Column, Integer, Date, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from core.setup import Base
from core.db import CreateDBSession
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
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    week_start_date = Column(Date, nullable=False)
    created_at = Column(Date, default=date.today)
    updated_at = Column(Date, default=date.today)

    # Relationships
    daily_sessions = relationship(
        "DailyStudySession", back_populates="study_plan", lazy="joined", cascade="all, delete-orphan"
    )
    user = relationship("User", back_populates="study_plans")

    def save(self) -> "StudyPlan":
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
    def get_study_plan_by_id(plan_id: int) -> "StudyPlan":
        with CreateDBSession() as session:
            return session.query(StudyPlan).filter(StudyPlan.id == plan_id).first()

    @staticmethod
    def get_user_study_plans(user_id: UUID) -> list["StudyPlan"]:
        with CreateDBSession() as session:
            return session.query(StudyPlan).filter(StudyPlan.user_id == user_id).all()

    @staticmethod
    def get_current_week_plan(user_id: UUID, week_start: date) -> "StudyPlan":
        with CreateDBSession() as session:
            return session.query(StudyPlan).filter(
                StudyPlan.user_id == user_id,
                StudyPlan.week_start_date == week_start
            ).first()


class DailyStudySession(Base):
    """Represents a daily study session within a study plan."""

    __tablename__ = "daily_study_sessions"

    id = Column(Integer, primary_key=True, index=True)
    study_plan_id = Column(Integer, ForeignKey("study_plans.id"), nullable=False)
    day_of_week = Column(Enum(DayOfWeek), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    tasks = Column(JSON, nullable=False)  # List of tasks

    # Relationships
    study_plan = relationship("StudyPlan", back_populates="daily_sessions")
    course = relationship("Course", lazy="joined")
    topic = relationship("Topic", lazy="joined")

    def save(self) -> "DailyStudySession":
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
    def get_sessions_for_plan(plan_id: int) -> list["DailyStudySession"]:
        with CreateDBSession() as session:
            return session.query(DailyStudySession).filter(DailyStudySession.study_plan_id == plan_id).all()


class SubjectStrength(Base):
    """Represents user's strength rating for a subject."""

    __tablename__ = "subject_strengths"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    strength = Column(Integer, nullable=False)  # 1-5 scale

    user = relationship("User", back_populates="subject_strengths")
    course = relationship("Course")

    def save(self) -> "SubjectStrength":
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
    def get_user_strengths(user_id: str) -> list["SubjectStrength"]:
        with CreateDBSession() as session:
            return session.query(SubjectStrength).filter(SubjectStrength.user_id == user_id).all()

    @staticmethod
    def get_strength(user_id: str, course_id: int) -> "SubjectStrength":
        with CreateDBSession() as session:
            return session.query(SubjectStrength).filter(
                SubjectStrength.user_id == user_id,
                SubjectStrength.course_id == course_id
            ).first()
