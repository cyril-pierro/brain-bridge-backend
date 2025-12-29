import error
from controller.users import UserOp
from fastapi import APIRouter, Depends, BackgroundTasks
from controller.teams import TeamsOp
from model.teams import TeamJoinRequest, JoinRequestStatus
from schema.teams import TeamIn, TeamOut, TeamJoinRequestOut
from schema import SuccessOut
from util.enum import UserRole
from service.auth import verify_access_token
from service.email import MailService

router = APIRouter(tags=["teams"])
NOT_ALLOWED = "You are not authorized to access this route"


@router.get("/teams", response_model=list[TeamOut])
async def get_all_teams(auth_data: dict = Depends(verify_access_token)):
    user_id = auth_data.get("user_id", None)
    is_student = UserOp.is_user_role(
        user_id=user_id, role=UserRole.student.value)
    is_admin = UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)

    if not (is_admin or is_student):
        raise error.AuthenticationError(msg=NOT_ALLOWED)

    return TeamsOp.get_user_teams(user_id=str(user_id)) if is_student else TeamsOp.get_all_teams()


@router.get("/teams/{code}", response_model=TeamOut)
async def get_team_by_code(code: str, auth_data: dict = Depends(verify_access_token)):
    user_id = auth_data.get("user_id", None)
    if not UserOp.is_user_role(user_id=user_id, role=UserRole.student.value):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return TeamsOp.get_team_by_code(code)


@router.delete("/teams/{team_id}", response_model=SuccessOut)
async def delete_team_by_id(team_id: int, auth_data: dict = Depends(verify_access_token)):
    user_id = auth_data.get("user_id", None)
    is_student = UserOp.is_user_role(
        user_id=user_id, role=UserRole.student.value)
    is_admin = UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)

    if not (is_student or is_admin):
        raise error.AuthenticationError(msg=NOT_ALLOWED)

    TeamsOp.delete_team(
        team_id=team_id, user_id=user_id, is_admin=is_admin)

    return {"message": "Team deleted successfully"}


@router.post("/teams", response_model=TeamOut)
async def create_team(
    data: TeamIn,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not UserOp.is_user_role(user_id=user_id, role=UserRole.student.value):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return TeamsOp.create_team(data=data, user_id=user_id)


@router.get("/teams/{code}/join", response_model=SuccessOut)
async def join_team(
    code: str,
    background_tasks: BackgroundTasks,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not UserOp.is_user_role(user_id=user_id, role=UserRole.student.value):
        raise error.AuthenticationError(msg=NOT_ALLOWED)

    # Create the join request
    request = TeamsOp.request_to_join_team(code, str(user_id))

    # Send notification email to creator in background
    team = request.team
    user = request.user
    user_full_name = user.full_name.replace("-", " ")
    background_tasks.add_task(
        MailService.send_email,
        email=team.creator.email,
        subject="New Join Request for Your Team",
        content={
            "message": f"{user_full_name} wants to join your team '{team.name}'. Please review the pending requests in your teams page.",
            "team_name": team.name,
            "requester_name": user_full_name
        },
        email_template="join_team_notification.html",
    )

    return {"message": "Join request sent. Waiting for approval from team creator."}


@router.get("/teams/{team_id}/pending-requests", response_model=list[TeamJoinRequestOut])
async def get_pending_requests(
    team_id: int,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not UserOp.is_user_role(user_id=user_id, role=UserRole.student.value):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    return TeamsOp.get_pending_requests_for_team(team_id, str(user_id))


@router.post("/teams/join-requests/{request_id}/approve", response_model=SuccessOut)
async def approve_join_request(
    request_id: int,
    background_tasks: BackgroundTasks,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not UserOp.is_user_role(user_id=user_id, role=UserRole.student.value):
        raise error.AuthenticationError(msg=NOT_ALLOWED)

    # Approve the request and get the request details
    result = TeamsOp.approve_join_request_with_details(
        request_id, str(user_id))

    # Send approval email in background
    background_tasks.add_task(
        MailService.send_email,
        email=result["user_email"],
        subject="Join Request Approved",
        content={
            "message": f"Your request to join '{result['team_name']}' has been approved by {result['creator_name']}.",
            "team_name": result["team_name"],
            "status": "approved"
        },
        email_template="join_request_response.html",
    )

    return {"message": "Join request approved"}


@router.post("/teams/join-requests/{request_id}/deny", response_model=SuccessOut)
async def deny_join_request(
    request_id: int,
    background_tasks: BackgroundTasks,
    auth_data: dict = Depends(verify_access_token),
):
    user_id = auth_data.get("user_id", None)
    if not UserOp.is_user_role(user_id=user_id, role=UserRole.student.value):
        raise error.AuthenticationError(msg=NOT_ALLOWED)

    # Deny the request and get details for email
    result = TeamsOp.deny_join_request_with_details(request_id, str(user_id))

    # Send denial email in background
    background_tasks.add_task(
        MailService.send_email,
        email=result["user_email"],
        subject="Join Request Denied",
        content={
            "message": f"Your request to join '{result['team_name']}' has been denied by {result['creator_name']}.",
            "team_name": result["team_name"],
            "status": "denied"
        },
        email_template="join_request_response.html",
    )

    return {"message": "Join request denied"}


@router.delete("/teams/{team_id}/members/{user_id}", response_model=SuccessOut)
async def remove_team_member(
    team_id: int,
    user_id: str,
    background_tasks: BackgroundTasks,
    auth_data: dict = Depends(verify_access_token),
):
    creator_id = auth_data.get("user_id", None)
    if not UserOp.is_user_role(user_id=creator_id, role=UserRole.student.value):
        raise error.AuthenticationError(msg=NOT_ALLOWED)

    TeamsOp.remove_user_from_team(team_id, user_id, str(creator_id), background_tasks)
    return {"message": "Member removed from team successfully"}


@router.get("/teams/{code}/add/{token}", response_model=SuccessOut)
async def add_user_to_team(
    code: str,
    token: str,
):
    from service.auth import TokenManager
    auth_data: dict = TokenManager.decode_token(token)
    team_creator_id = auth_data.get("user_id", None)
    user_to_join_id = auth_data.get("user_to_join_id", None)
    if not UserOp.is_user_role(user_id=team_creator_id, role=UserRole.student.value):
        raise error.AuthenticationError(msg=NOT_ALLOWED)
    TeamsOp.add_user_to_a_team(
        team_code=code, user_id=user_to_join_id, team_creator_id=team_creator_id
    )
    return {"message": "User added to team"}
