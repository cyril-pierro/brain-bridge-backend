from sqlalchemy import Column, Integer, ForeignKey, Text, String, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.setup import Base
from core.db import CreateDBSession
from error import InvalidRequestError
from schema.questions import FlashcardIn


class Flashcard(Base):
    """
    Represents a single flashcard (question/answer pair) tied to a Course.
    """

    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True)
    # Changed from topic_id to course_id
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)

    # Updated relationship to Course
    course = relationship("Course", back_populates="flashcards")

    def update(self, **data) -> "Flashcard":
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

    def save(self) -> "Flashcard":
        with CreateDBSession() as session:
            session.add(self)
            session.commit()
            session.refresh(self)
            return self

    @staticmethod
    def add(course_id: int, flashcard_data: FlashcardIn) -> "Flashcard":
        with CreateDBSession() as session:
            flashcard = Flashcard(course_id=course_id, **flashcard_data.model_dump())
            session.add(flashcard)
            session.commit()
            session.refresh(flashcard)
            return flashcard

    @staticmethod
    def get(flashcard_id: int) -> "Flashcard":
        with CreateDBSession() as session:
            flashcard = (
                session.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
            )
            if not flashcard:
                raise InvalidRequestError(msg="Flashcard not found", status_code=404)
            return flashcard

    @staticmethod
    def get_questions(course_id: int, limit: int = 10) -> list["Flashcard"]:
        with CreateDBSession() as session:
            flashcards = (
                session.query(Flashcard)
                .filter(Flashcard.course_id == course_id)
                .order_by(func.random())  # Changed to random order
                .limit(limit)
                .all()
            )
            if not flashcards:
                raise InvalidRequestError(msg="No flashcards found", status_code=404)
            return flashcards


class QuizQuestion(Base):
    """
    Represents a single question in a quiz, tied to a Course.
    """

    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True, index=True)
    # Changed from topic_id to course_id
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    question_text = Column(Text, nullable=False)

    # Updated relationship to Course
    course = relationship("Course", back_populates="quiz_questions", lazy="joined")
    answers = relationship(
        "QuizAnswer",
        back_populates="question",
        lazy="joined",
        cascade="all, delete-orphan",
    )

    def save(self) -> "QuizQuestion":
        with CreateDBSession() as session:
            session.add(self)
            session.commit()
            session.refresh(self)
            return self

    def update(self, **data) -> "QuizQuestion":
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
    def get(question_id: int) -> "QuizQuestion":
        with CreateDBSession() as session:
            question = (
                session.query(QuizQuestion)
                .filter(QuizQuestion.id == question_id)
                .first()
            )
            if not question:
                raise InvalidRequestError(msg="Question not found", status_code=404)
            return question

    @staticmethod
    def add(course_id: int, question_text: str) -> "QuizQuestion":

        question = QuizQuestion(course_id=course_id, question_text=question_text)
        return question.save()

    @staticmethod
    def get_quiz_questions(course_id: int, limit: int = 10) -> list["QuizQuestion"]:
        with CreateDBSession() as session:
            questions = (
                session.query(QuizQuestion)
                .filter(QuizQuestion.course_id == course_id)
                .order_by(func.random())  # Changed to random order
                .limit(limit)
                .all()
            )
            if not questions:
                raise InvalidRequestError(msg="No questions found", status_code=404)
            return questions


class QuizAnswer(Base):
    """
    Represents a multiple-choice answer option for a QuizQuestion.
    """

    __tablename__ = "quiz_answers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("quiz_questions.id"), nullable=False)
    answer_text = Column(String, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)

    question = relationship("QuizQuestion", back_populates="answers")

    def update(self, **data) -> "QuizAnswer":
        with CreateDBSession() as session:
            for key, value in data.items():
                setattr(self, key, value)
            session.commit()
            session.refresh(self)
            return self

    def save(self) -> "QuizAnswer":
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
    def get(answer_id: int) -> "QuizAnswer":
        with CreateDBSession() as session:
            answer = (
                session.query(QuizAnswer).filter(QuizAnswer.id == answer_id).first()
            )
            if not answer:
                raise InvalidRequestError(msg="Answer not found", status_code=404)
            return answer

    @staticmethod
    def add(
        question_id: int, answer_text: str, is_correct: bool = False
    ) -> "QuizAnswer":

        answer = QuizAnswer(
            question_id=question_id, answer_text=answer_text, is_correct=is_correct
        )
        return answer.save()

    @staticmethod
    def delete_all_answers(question_id: int) -> bool:
        with CreateDBSession() as session:
            session.query(QuizAnswer).filter(
                QuizAnswer.question_id == question_id
            ).delete()
            session.commit()
            return True
