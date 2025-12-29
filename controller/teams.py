from model.teams import Team, TeamJoinRequest, JoinRequestStatus
from model.users import User
from schema.teams import TeamIn
from util.gen import generate_team_code
from error import InvalidRequestError
from controller.users import UserOp
from util.enum import UserRole
from core.db import CreateDBSession
from fastapi import BackgroundTasks
from service.email import MailService


class TeamsOp:
    @staticmethod
    def create_team(data: TeamIn, user_id: str) -> Team:
        if not UserOp.is_user_role(user_id=user_id, role=UserRole.student.value):
            raise InvalidRequestError(msg="Only students can create teams")

        code = generate_team_code()
        team_found = Team.get_team_by_code(code)
        if not team_found:
            team = Team.create_team(name=data.name, code=code, user_id=user_id)
            return team
        return TeamsOp.create_team(data, user_id)

    @staticmethod
    def delete_team(team_id: str, user_id: str, is_admin=True) -> bool:
        team = Team.validate_team_code(team_id)
        if not is_admin and str(team.creator_id) != user_id:
            raise InvalidRequestError(
                msg="Only team creators can delete teams")
        deleted = team.delete()
        return deleted

    @staticmethod
    def add_user_to_a_team(team_code: str, user_id: str, team_creator_id: str) -> User:
        if not UserOp.is_user_role(user_id=user_id, role=UserRole.student.value):
            raise InvalidRequestError(msg="Only students can join teams")

        team = Team.validate_team_code(team_code)
        user = User.validate_user_id(user_id)
        if team.creator_id != team_creator_id:
            raise InvalidRequestError(
                msg="Only team creators can add users to the team"
            )
        if user_id == team.creator_id:
            raise InvalidRequestError(
                msg="Team creator cannot join their own team")
        user.team_id = team.id
        saved_user = user.save()
        return saved_user

    @staticmethod
    def change_team_name(team_code: str, name: str, team_creator_id: int) -> Team:
        team = Team.validate_team_code(team_code)
        if team.creator_id != team_creator_id:
            raise InvalidRequestError(
                msg="Only team creators can edit team name")
        editted_team = team.edit(name=name)
        return editted_team

    @staticmethod
    def get_team_by_code(team_code: str) -> Team:
        return Team.validate_team_code(team_code)

    @staticmethod
    def get_all_teams() -> list[Team]:
        return Team.get_all_teams()

    @staticmethod
    def get_user_teams(user_id: str) -> list[Team]:
        """
        Get all teams that a user has access to: teams they created and teams they joined.
        For teams they created, also load pending join requests.
        """
        created_teams = Team.get_all_teams_created_by_user(user_id)
        joined_teams = Team.get_teams_joined_by_user(user_id)

        # Load pending requests for created teams
        for team in created_teams:
            team.pending_requests = TeamJoinRequest.get_pending_requests_for_team(
                team.id)

        return created_teams + joined_teams

    @staticmethod
    def request_to_join_team(team_code: str, user_id: str) -> TeamJoinRequest:
        if not UserOp.is_user_role(user_id=user_id, role=UserRole.student.value):
            raise InvalidRequestError(msg="Only students can join teams")

        team = Team.validate_team_code(team_code)
        user = User.validate_user_id(user_id)

        # Check if user is already in the team
        if user.team_id == team.id:
            raise InvalidRequestError(
                msg="You are already a member of this team")

        # Check if user already has a pending request
        existing_request = TeamJoinRequest.get_user_pending_request(
            user_id, team.id)
        if existing_request:
            raise InvalidRequestError(
                msg="You already have a pending request for this team")

        # Create the request
        request = TeamJoinRequest.create_request(team.id, user_id)

        return request

    @staticmethod
    def get_pending_requests_for_team(team_id: int, creator_id: str) -> list[TeamJoinRequest]:
        team = Team.get_team_by_id(team_id)
        if not team:
            raise InvalidRequestError(msg="Team not found")
        if str(team.creator_id) != creator_id:
            raise InvalidRequestError(
                msg="Only team creators can view pending requests")
        return TeamJoinRequest.get_pending_requests_for_team(team_id)

    @staticmethod
    def approve_join_request(request_id: int, creator_id: str) -> User:
        request = TeamJoinRequest.get_request_by_id(request_id)
        if not request:
            raise InvalidRequestError(msg="Join request not found")

        team = request.team
        if str(team.creator_id) != creator_id:
            raise InvalidRequestError(
                msg="Only team creators can approve requests")

        # Update request status
        request.update_status(JoinRequestStatus.approved)

        # Add user to team
        user = request.user
        user.team_id = team.id
        saved_user = user.save()

        return saved_user

    @staticmethod
    def approve_join_request_with_details(request_id: int, creator_id: str) -> dict:
        """
        Approve join request and return details needed for email notification.
        Returns dict with user_email, team_name, and creator_name.
        """
        with CreateDBSession() as db:
            request = db.query(TeamJoinRequest).filter(
                TeamJoinRequest.id == request_id).first()
            if not request:
                raise InvalidRequestError(msg="Join request not found")

            team = request.team
            if str(team.creator_id) != creator_id:
                raise InvalidRequestError(
                    msg="Only team creators can approve requests")

            user = request.user

            # Update request status
            request.status = JoinRequestStatus.approved

            # Add user to team
            user.team_id = team.id

            db.commit()

            return {
                "user_email": user.email,
                "team_name": team.name,
                "creator_name": team.creator.full_name.replace("-", " ")
            }

    @staticmethod
    def deny_join_request_with_details(request_id: int, creator_id: str) -> dict:
        """
        Deny join request and return details needed for email notification.
        Returns dict with user_email, team_name, and creator_name.
        """
        with CreateDBSession() as db:
            request = db.query(TeamJoinRequest).filter(
                TeamJoinRequest.id == request_id).first()
            if not request:
                raise InvalidRequestError(msg="Join request not found")

            team = request.team
            if str(team.creator_id) != creator_id:
                raise InvalidRequestError(
                    msg="Only team creators can deny requests")

            user = request.user

            # Update request status
            request.status = JoinRequestStatus.denied

            db.commit()

            return {
                "user_email": user.email,
                "team_name": team.name,
                "creator_name": team.creator.full_name.replace("-", " ")
            }

    @staticmethod
    def deny_join_request(request_id: int, creator_id: str) -> TeamJoinRequest:
        request = TeamJoinRequest.get_request_by_id(request_id)
        if not request:
            raise InvalidRequestError(msg="Join request not found")

        team = request.team
        if str(team.creator_id) != creator_id:
            raise InvalidRequestError(
                msg="Only team creators can deny requests")

        # Update request status
        request.update_status(JoinRequestStatus.denied)

        return request

    @staticmethod
    def remove_user_from_team(team_id: int, user_id_to_remove: str, creator_id: str, background_tasks: "BackgroundTasks") -> bool:
        """
        Remove a user from a team. Only team creators can remove members.
        """
        team = Team.get_team_by_id(team_id)
        if not team:
            raise InvalidRequestError(msg="Team not found")

        if str(team.creator_id) != creator_id:
            raise InvalidRequestError(
                msg="Only team creators can remove members")

        if user_id_to_remove == creator_id:
            raise InvalidRequestError(
                msg="Team creators cannot remove themselves")

        user_to_remove = User.validate_user_id(user_id_to_remove)

        # Check if user is actually in the team
        if user_to_remove.team_id != team.id:
            raise InvalidRequestError(msg="User is not a member of this team")

        # Remove user from team
        user_to_remove.team_id = None
        user_to_remove.save()

        # Send notification email to the removed user
        background_tasks.add_task(
            MailService.send_email,
            email=str(user_to_remove.email),
            subject=f"Removed from Team - {str(team.name)}",
            content={
                "message": "You have been removed from the team by the team creator. If you believe this was done in error, please contact the team creator directly.",
                "team_name": str(team.name),
                "user_name": str(user_to_remove.full_name).replace("-", " ")
            },
            email_template="member_removal_notification.html",
        )

        return True

    @staticmethod
    def get_pending_requests_for_user(user_id: str) -> list[TeamJoinRequest]:
        """
        Get pending join requests sent by a specific user
        """
        with CreateDBSession() as db:
            return db.query(TeamJoinRequest).filter(
                TeamJoinRequest.user_id == user_id,
                TeamJoinRequest.status == JoinRequestStatus.pending
            ).all()
