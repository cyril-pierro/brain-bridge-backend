from pydantic import BaseModel
from typing import List
from datetime import date
from model.study_plans import DayOfWeek


class SubjectStrengthIn(BaseModel):
    course_id: int
    strength: int  # 1-5


class StudyPlanGenerateIn(BaseModel):
    selected_subjects: List[int]  # course_ids
    daily_study_time: int  # minutes
    strength_ratings: List[SubjectStrengthIn]
    completed_topics: List[int]  # topic_ids


class TaskOut(BaseModel):
    type: str  # "reading", "flashcards", "quiz"
    duration: int  # minutes


class DailyStudySessionOut(BaseModel):
    id: int
    day_of_week: DayOfWeek
    course_id: int
    course_name: str
    topic_id: int
    topic_subject: str
    tasks: List[TaskOut]

    class Config:
        from_attributes = True


class StudyPlanOut(BaseModel):
    id: int
    user_id: str
    week_start_date: date
    daily_sessions: List[DailyStudySessionOut]

    class Config:
        from_attributes = True


class SubjectStrengthOut(BaseModel):
    id: int
    course_id: int
    course_name: str
    strength: int

    class Config:
        from_attributes = True


class StudyPlanSwapIn(BaseModel):
    from_day: DayOfWeek
    to_day: DayOfWeek
