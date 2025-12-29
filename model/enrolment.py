from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, UUID
from sqlalchemy.orm import relationship
from core.setup import Base
from core.db import CreateDBSession
from error import InvalidRequestError


class Enrolment(Base):
    """
    Association table (User <-> Course). Tracks which users are enroled in which courses.
    """

    __tablename__ = "enrolments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)

    # Relationships
    user = relationship("User", back_populates="enrolments")
    course = relationship("Course", back_populates="enrolments", lazy="joined")

    # Constraint: Ensures a user can only enrol in a specific course once
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="_user_course_uc"),)

    def __repr__(self):
        return f"<Enrolment {self.user_id} - {self.course_id}>"

    def save(self) -> "Enrolment":
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
    def create_enrolment(user_id: int, course_id: int) -> "Enrolment":
        enrolment = Enrolment(user_id=user_id, course_id=course_id)
        return enrolment.save()

    @staticmethod
    def get_courses_enroled_by_user(user_id: int) -> list["Enrolment"]:
        with CreateDBSession() as session:
            return session.query(Enrolment).filter(Enrolment.user_id == user_id).all()

    @staticmethod
    def get_enrolment_by_id(enrolment_id: int) -> "Enrolment":
        with CreateDBSession() as session:
            return session.query(Enrolment).filter(Enrolment.id == enrolment_id).first()

    @staticmethod
    def validate_enrolment(enrolment_id: int) -> "Enrolment":
        enrolment = Enrolment.get_enrolment_by_id(enrolment_id)
        if not enrolment:
            raise InvalidRequestError(msg="Enrolment not found", code=404)
        return enrolment
