from sqlalchemy import Column, String, Integer, Enum
from sqlalchemy.orm import relationship
from util.enum import SubjectType
from core.setup import Base
from core.db import CreateDBSession
from schema.courses import CourseIn
from error import InvalidRequestError


class Course(Base):
    """Represents an available course."""

    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String)
    type = Column(Enum(SubjectType), nullable=False)

    # Relationships
    enrolments = relationship(
        "Enrolment", back_populates="course", lazy="selectin")
    flashcards = relationship(
        "Flashcard",  # The name of the related model
        back_populates="course",  # The property name on the Flashcard model
        lazy="selectin",
    )
    quiz_questions = relationship(
        "QuizQuestion",  # The name of the related model
        back_populates="course",  # The property name on the Flashcard model
        lazy="selectin",
    )
    # OPTIMIZED: Topics relationship is now explicitly ordered by the 'order' column.
    topics = relationship(
        "Topic", back_populates="course", order_by="Topic.order", lazy="selectin"
    )
    specialty_instructors = relationship(
        "InstructorCourseSpecialty", back_populates="course", lazy="selectin"
    )

    def __repr__(self):
        return f"<Course {self.name}>"

    def __str__(self):
        return self.name

    def save(self) -> "Course":
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
    def get_courses() -> list["Course"]:
        with CreateDBSession() as session:
            return session.query(Course).all()

    @staticmethod
    def get_course_by_id(course_id: int) -> "Course":
        with CreateDBSession() as session:
            return session.query(Course).filter(Course.id == course_id).first()

    @staticmethod
    def get_courses_by_ids(course_ids: list[int]) -> list["Course"]:
        """Bulk load multiple courses in a single query for better performance."""
        with CreateDBSession() as session:
            return session.query(Course).filter(Course.id.in_(course_ids)).all()

    @staticmethod
    def validate_course(course_id: int) -> "Course":
        course = Course.get_course_by_id(course_id)
        if not course:
            raise InvalidRequestError(msg="Course not found", code=404)
        return course

    @staticmethod
    def add(course_data: CourseIn) -> "Course":
        course = Course(**course_data.model_dump())
        return course.save()

    @staticmethod
    def update(course_id: int, course_data: CourseIn) -> "Course":
        with CreateDBSession() as session:
            course = session.query(Course).filter(
                Course.id == course_id).first()
            if not course:
                raise InvalidRequestError(msg="Course not found", code=404)
            for key, value in course_data.model_dump().items():
                setattr(course, key, value)
            session.commit()
            session.refresh(course)
            return course

    @staticmethod
    def get_core_course_names() -> list[str]:
        """Get all course names that are marked as CORE type."""
        with CreateDBSession() as session:
            from util.enum import SubjectType
            core_courses = session.query(Course).filter(Course.type == SubjectType.CORE).all()
            return [course.name for course in core_courses]
