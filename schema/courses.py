from pydantic import BaseModel
from typing import Optional
from util.enum import SubjectType
from schema.questions import FlashcardOut, QuizQuestionOut
from schema.hub import LearningHubOut
from datetime import datetime


class TopicIn(BaseModel):
    subject: str
    content: Optional[str] = None
    order: int


class TopicOut(BaseModel):
    id: int
    subject: str
    content: Optional[str] = None

    class Config:
        from_attributes = True


class SimpleCourseOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    type: SubjectType

    class Config:
        from_attributes = True


class TopicOutWithCourseOut(BaseModel):
    id: int
    subject: str
    content: Optional[str] = None
    course: SimpleCourseOut

    class Config:
        from_attributes = True


class CompletedCourseOut(BaseModel):
    id: int
    is_completed: bool
    topic: TopicOutWithCourseOut
    completed_at: datetime

    class Config:
        from_attributes = True


class TopicOut2(BaseModel):
    id: int
    subject: str
    content: Optional[str] = None
    order: int
    video_resources: list[LearningHubOut] = []

    class Config:
        from_attributes = True


class CourseIn(BaseModel):
    name: str
    description: Optional[str] = None
    type: SubjectType = SubjectType.ELECTIVE


class CourseOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    type: SubjectType
    topics: list[TopicOut2] = []
    flashcards: list[FlashcardOut] = []
    quiz_questions: list[QuizQuestionOut] = []

    class Config:
        from_attributes = True
