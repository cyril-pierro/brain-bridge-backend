from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AIQuestionIn(BaseModel):
    question: str
    context: Optional[str] = None  # Optional context like course or topic


class AIAnswerOut(BaseModel):
    question: str
    answer: str
    confidence_score: Optional[float] = None
    sources: Optional[list[str]] = []
    generated_at: datetime

    class Config:
        from_attributes = True
