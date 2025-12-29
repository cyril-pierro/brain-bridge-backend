from sqlalchemy import Column, Integer, String, ForeignKey, UUID, Enum
from sqlalchemy.orm import relationship
from core.setup import Base
from core.db import CreateDBSession
from error import InvalidRequestError
import enum
from typing import Union


class JoinRequestStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    denied = "denied"


class TeamJoinRequest(Base):
    __tablename__ = "team_join_requests"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(JoinRequestStatus), default=JoinRequestStatus.pending)

    # Relationships
    team = relationship("Team", back_populates="join_requests", lazy="joined")
    user = relationship("User", back_populates="join_requests", lazy="joined")

    def save(self) -> "TeamJoinRequest":
        with CreateDBSession() as db:
            db.add(self)
            db.commit()
            db.refresh(self)
            return self

    def update_status(self, status: JoinRequestStatus):
        with CreateDBSession() as db:
            self.status = status
            db.commit()
            db.refresh(self)
            return self

    @staticmethod
    def create_request(team_id: int, user_id: str) -> "TeamJoinRequest":
        request = TeamJoinRequest(team_id=team_id, user_id=user_id)
        return request.save()

    @staticmethod
    def get_pending_requests_for_team(team_id: int) -> list["TeamJoinRequest"]:
        with CreateDBSession() as db:
            return db.query(TeamJoinRequest).filter(
                TeamJoinRequest.team_id == team_id,
                TeamJoinRequest.status == JoinRequestStatus.pending
            ).all()

    @staticmethod
    def get_request_by_id(request_id: int) -> "TeamJoinRequest":
        with CreateDBSession() as db:
            return db.query(TeamJoinRequest).filter(TeamJoinRequest.id == request_id).first()

    @staticmethod
    def get_user_pending_request(user_id: str, team_id: int) -> "TeamJoinRequest":
        with CreateDBSession() as db:
            return db.query(TeamJoinRequest).filter(
                TeamJoinRequest.user_id == user_id,
                TeamJoinRequest.team_id == team_id,
                TeamJoinRequest.status == JoinRequestStatus.pending
            ).first()


class Team(Base):
    """
    Represents a learning team or cohort.
    Students (Users) are linked to a team via the team_id foreign key on the User model.
    """

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    # The unique code used for joining the team
    code = Column(String, unique=True, index=True, nullable=False)

    creator_id = Column(UUID, ForeignKey("users.id"), nullable=False)

    # Relationships
    # Students associated with this team
    students = relationship("User", back_populates="team",
                            foreign_keys="User.team_id", lazy="joined")
    creator = relationship(
        "User", back_populates="created_teams", foreign_keys=[creator_id],
        lazy="joined"
    )
    join_requests = relationship("TeamJoinRequest", back_populates="team", cascade="all, delete-orphan")

    def save(self) -> "Team":
        with CreateDBSession() as db:
            db.add(self)
            db.commit()
            db.refresh(self)
            return self

    def edit(self, name: str):
        with CreateDBSession() as db:
            self.name = name
            db.commit()
            db.refresh(self)
            return self

    def delete(self) -> bool:
        with CreateDBSession() as db:
            db.delete(self)
            db.commit()
            return True

    @staticmethod
    def create_team(name: str, code: str, user_id: int) -> "Team":
        new_team = Team(name=name, code=code, creator_id=user_id)
        return new_team.save()

    @staticmethod
    def get_team_by_code(code: str) -> "Team":
        with CreateDBSession() as db:
            return db.query(Team).filter(Team.code == code).first()

    @staticmethod
    def get_team_by_id(team_id: int) -> "Team":
        with CreateDBSession() as db:
            return db.query(Team).filter(Team.id == team_id).first()

    @staticmethod
    def validate_team_code(code: Union[str, int]) -> "Team":
        if isinstance(code, str):
            team = Team.get_team_by_code(code)
        else:
            team = Team.get_team_by_id(code)
        if not team:
            raise InvalidRequestError(msg="Invalid team code")
        return team

    @staticmethod
    def get_all_teams() -> list["Team"]:
        with CreateDBSession() as db:
            return db.query(Team).all()

    @staticmethod
    def get_all_teams_created_by_user(user_id: str) -> list["Team"]:
        with CreateDBSession() as db:
            return db.query(Team).filter(Team.creator_id == user_id).all()

    @staticmethod
    def get_teams_joined_by_user(user_id: str) -> list["Team"]:
        """
        Get all teams that a user has joined as a student
        """
        with CreateDBSession() as db:
            # Query teams where the user is a student (via User.team_id relationship)
            from uuid import UUID
            # Convert string UUID to UUID object for proper comparison
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            return db.query(Team).filter(Team.students.any(id=user_uuid)).all()
