from sqlalchemy import Column, Integer, ForeignKey, UUID
from sqlalchemy.orm import relationship
from core.setup import Base
from core.db import CreateDBSession


class InstructorCourseSpecialty(Base):
    """
    Association table for Instructor <-> Course to track an instructor's primary subjects.
    """

    __tablename__ = "instructor_course_specialties"

    instructor_id = Column(UUID, ForeignKey("instructors.id"), primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), primary_key=True)

    # Relationships (not strictly necessary but good practice)
    instructor = relationship("Instructor", back_populates="specialties", lazy="joined")
    course = relationship(
        "Course", back_populates="specialty_instructors", lazy="joined"
    )

    def save(self) -> "InstructorCourseSpecialty":
        with CreateDBSession() as db:
            db.add(self)
            db.commit()
            db.refresh(self)
            return self

    def delete(self) -> bool:
        with CreateDBSession() as db:
            db.delete(self)
            db.commit()
            return True

    def update(self, **kwargs) -> "InstructorCourseSpecialty":
        for key, value in kwargs.items():
            setattr(self, key, value)
        return self.save()

    @staticmethod
    def get_specialties_for_instructor(
        instructor_id: int,
    ) -> list["InstructorCourseSpecialty"]:
        with CreateDBSession() as db:
            return (
                db.query(InstructorCourseSpecialty)
                .filter(InstructorCourseSpecialty.instructor_id == instructor_id)
                .all()
            )

    @staticmethod
    def get_specialty_for_instructor(
        instructor_id: int, course_id: int
    ) -> "InstructorCourseSpecialty":
        with CreateDBSession() as db:
            return (
                db.query(InstructorCourseSpecialty)
                .filter(
                    InstructorCourseSpecialty.instructor_id == instructor_id,
                    InstructorCourseSpecialty.course_id == course_id,
                )
                .first()
            )

    @staticmethod
    def add(instructor_id: int, course_id: int) -> "InstructorCourseSpecialty":
        new_specialty = InstructorCourseSpecialty(
            instructor_id=instructor_id, course_id=course_id
        )
        return new_specialty.save()

    @staticmethod
    def delete_all_specialties_of_instructor(instructor_id: int) -> bool:
        with CreateDBSession() as db:
            db.query(InstructorCourseSpecialty).filter(
                InstructorCourseSpecialty.instructor_id == instructor_id
            ).delete()
            db.commit()
            return True
