from pydantic import BaseModel, model_validator


class FlashcardIn(BaseModel):
    question: str
    answer: str


class FlashcardOut(BaseModel):
    id: int
    question: str
    answer: str

    class Config:
        from_attributes = True


class QuizAnswerIn(BaseModel):
    answer_text: str
    is_correct: bool


class QuizQuestionIn(BaseModel):
    question_text: str
    answers: list[QuizAnswerIn] = []

    @model_validator(mode="after")
    def validate_answers(self):
        if len(self.answers) < 4:
            raise ValueError("At least 4 answers must be provided")
        return self


class QuizAnswerOut(BaseModel):
    id: int
    answer_text: str
    is_correct: bool

    class Config:
        from_attributes = True


class QuizQuestionOut(BaseModel):
    id: int
    question_text: str
    answers: list[QuizAnswerOut] = []

    class Config:
        from_attributes = True
