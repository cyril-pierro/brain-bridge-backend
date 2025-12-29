from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Enum,
    Integer,
    ForeignKey,
    UUID,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from util.enum import Provider, UserRole, Gender
from schema.users import SignUp
from core.db import CreateDBSession
from core.setup import Base
from passlib.context import CryptContext
from error import InvalidRequestError
from uuid import uuid4

# Password hashing configuration - singleton for better performance


class PasswordHasher:
    _instance = None
    _context = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PasswordHasher, cls).__new__(cls)
            cls._context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return cls._instance

    def hash(self, password: str) -> str:
        return self._context.hash(password)

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return self._context.verify(plain_password, hashed_password)


pwd_hasher = PasswordHasher()


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255))
    hashed_password = Column(String, nullable=True)

    # Authentication provider details
    auth_provider = Column(Enum(Provider), default=Provider.STANDARD)
    auth_provider_id = Column(
        String(255), nullable=True)  # ID from Google/Apple

    gender = Column(Enum(Gender), nullable=False, default=Gender.male.value)
    role = Column(Enum(UserRole), nullable=False,
                  default=UserRole.student.value)
    profile_picture = Column(String(255), nullable=True)

    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    has_enrolled = Column(Boolean, default=False)
    is_subscribed = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    enrolments = relationship("Enrolment", back_populates="user")
    subscription = relationship(
        "Subscription", back_populates="user", uselist=False)
    topic_completions = relationship(
        "UserTopicCompletion", back_populates="user")
    team = relationship("Team", back_populates="students",
                        foreign_keys=[team_id])
    created_teams = relationship(
        "Team", back_populates="creator", foreign_keys="Team.creator_id"
    )
    instructor_profile = relationship(
        "Instructor", back_populates="user", uselist=False, lazy="selectin"
    )
    reviews_given = relationship(
        "Review", back_populates="reviewer", foreign_keys="Review.reviewer_user_id"
    )
    bookings = relationship("InstructorBooking", back_populates="user")
    study_plans = relationship("StudyPlan", back_populates="user")
    subject_strengths = relationship("SubjectStrength", back_populates="user")
    join_requests = relationship("TeamJoinRequest", back_populates="user")

    def __repr__(self):
        return f"<User {self.email}>"

    def json(self) -> dict:
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "is_verified": self.is_verified,
            "is_active": self.is_active,
            "has_enrolled": self.has_enrolled,
            "is_subscribed": self.is_subscribed,
            "role": self.role,
            "gender": self.gender,
            "profile_picture": self.profile_picture,
        }

    def delete(self) -> bool:
        with CreateDBSession() as db:
            db.delete(self)
            db.commit()
            return True

    def save(self) -> "User":
        with CreateDBSession() as db:
            db.add(self)
            db.commit()
            db.refresh(self)
            return self

    def update(self, **kwargs) -> "User":
        for key, value in kwargs.items():
            setattr(self, key, value)
        return self.save()

    @staticmethod
    def add(user: SignUp) -> "User":
        # Generate a unique UUID by checking if it already exists
        user_id = uuid4()
        while User.get_user_by_id(str(user_id)):
            user_id = uuid4()

        new_user = User(
            id=user_id,
            email=user.email,
            full_name=f"{user.first_name}-{user.last_name}",
            hashed_password=(
                pwd_hasher.hash(user.password) if user.password else None
            ),
            gender=user.gender.value,
            auth_provider=user.auth_provider,
            auth_provider_id=user.auth_provider_id,
        )
        return new_user.save()

    @staticmethod
    def create(data: dict) -> "User":
        new_user = User(**data)
        return new_user.save()

    @staticmethod
    def get_users() -> list["User"]:
        with CreateDBSession() as db:
            return db.query(User).all()

    @staticmethod
    def get_user_by_email(email: str) -> "User":
        with CreateDBSession() as db:
            return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_id(user_id: str) -> "User":
        with CreateDBSession() as db:
            return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def verify_password(plain_password, hashed_password):
        return pwd_hasher.verify(plain_password, hashed_password)

    @staticmethod
    def validate_user_id(user_id: str) -> "User":
        user = User.get_user_by_id(user_id=user_id)
        if not user:
            raise InvalidRequestError(msg="Invalid user request", code=404)
        return user
