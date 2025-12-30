import error
import httpx
from schema.users import (
    SignUp,
    SignIn,
    SubscriptionOut,
    SignUpOTP,
    ResendOTP,
    UserOut,
    UserUpdate,
    ChangePassword,
    SignInOut,
    AuthRequest,
)
from controller.users import UserOp
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from service.email import MailService
from util.enum import SubscriptionType, UserRole
from service.auth import verify_access_token, TokenManager
from schema import SuccessOut
from service.redis import Redis
from config.setting import settings


redis_instance = Redis()

router = APIRouter(tags=["users"])


@router.post("/users/register", response_model=SuccessOut)
def register(user: SignUp, background_tasks: BackgroundTasks):
    """
    Register a new user
    - Creates user account
    - Sends verification email with OTP
    - Returns success message
    """
    user, otp = UserOp.register(user)
    print("user-otp", otp)
    background_tasks.add_task(
        MailService.send_email,
        email=user.email,  # type: ignore
        subject="Email Verification",
        content={
            "otp": otp,
            "title": f"Hello {user.full_name.split('-')[0].capitalize()}",
        },
        email_template="otp.html",
    )
    return {"message": "User created successfully"}


@router.post("/users/otp/verify", response_model=SuccessOut)
def verify_user_registration_otp(data: SignUpOTP):
    """
    Verify user registration OTP
    - Validates OTP and marks user as verified
    - Returns success message
    """
    if UserOp.verify_user_otp(email=data.email, otp=data.otp):
        return {"message": "User verified successfully"}
    raise error.InvalidRequestError(msg="Invalid OTP")


@router.post("/users/otp/resend", response_model=SuccessOut)
def resend_otp(data: ResendOTP, background_task: BackgroundTasks):
    """
    Resend OTP for user registration
    - Generates and sends new OTP
    - Returns success message
    """
    user, otp = UserOp.resend_otp(data.email)
    print("user-otp", otp)
    background_task.add_task(
        MailService.send_email,
        email=user.email,  # type: ignore
        subject="Email Verification",
        content={
            "otp": otp,
            "title": f"Hello {user.full_name.split('-')[0].capitalize()}",
        },
        email_template="otp.html",
    )
    return {"message": "OTP sent successfully"}


@router.post("/users/login", response_model=SignInOut)
def login(user: SignIn):
    """
    Authenticate and login a user
    - Validates user credentials
    - Returns auth token on success
    """
    user_details, access_token = UserOp.login(user)
    return {
        "user": user_details.json(),
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/auth/google", response_model=SignInOut)
async def google_auth(auth_data: AuthRequest):
    """
    Exchanges the authorization code for a Google access token,
    fetches user info, and returns a local JWT.
    """
    # 1. Exchange code for Google tokens
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": auth_data.code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": "postmessage",  # Standard for the Google Identity Services popup
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code")

        google_tokens = response.json()
        access_token = google_tokens.get("access_token")

        # 2. Get user info from Google
        user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        user_info_res = await client.get(user_info_url, headers={
                                         "Authorization": f"Bearer {access_token}"})

        if user_info_res.status_code != 200:
            raise HTTPException(
                status_code=400, detail="Failed to fetch user info")

        user_info = user_info_res.json()

    # 3. Handle User in Database
    user = UserOp.get_or_create_oauth_user(user_info, "google")

    # 4. Create local session/JWT
    local_token = TokenManager.create_access_token(
        data={"user_id": str(user.id), "name": user_info.get("name")},
        expires_in_minutes=settings.USER_LOGIN_EXPIRE_SECONDS,
    )

    # Store token in Redis with same expiry as token
    await redis_instance.set(
        f"token-{user.id}",
        local_token,
        expiry=settings.USER_LOGIN_EXPIRE_SECONDS * 60,
    )

    return {
        "user": user,
        "access_token": local_token,
        "token_type": "bearer",
    }


@router.post("/users/logout", response_model=SuccessOut)
def logout(auth_data: dict = Depends(verify_access_token)):
    """
    Logout user and clear all associated cache records
    - Requires authentication
    - Clears user-specific cache entries
    - Returns success message
    """
    user_id = auth_data.get("user_id")
    if not user_id:
        raise error.AuthenticationError("Invalid authentication token")

    # Clear user-specific caches
    cache_keys_to_clear = [
        f"user_subscription:{user_id}",
        f"token-{user_id}",
        f"user_study_plans:{user_id}",
        f"user_current_week_plan:{user_id}",
        f"user_strengths:{user_id}",
    ]

    # Also clear token payload cache - since we don't know the hash, we'll skip for now
    # It will expire naturally

    for key in cache_keys_to_clear:
        redis_instance.delete(key)

    return {"message": "Logged out successfully"}


@router.get("/users/profile", response_model=UserOut)
def get_current_user(user: dict = Depends(verify_access_token)):
    """
    Get the current user's details
    - Requires authentication
    - Returns user details
    """
    user_details = UserOp.get_user_by_id(user.get("user_id"))
    return user_details


@router.put("/users/profile", response_model=UserOut)
def update_current_user(
    user_data: UserUpdate,
    auth_data: dict = Depends(verify_access_token)
):
    """
    Update the current user's profile
    - Requires authentication
    - Updates user details
    """
    user_id = auth_data.get("user_id")
    if not user_id:
        raise error.AuthenticationError("Invalid authentication token")

    # Update user profile
    updated_user = UserOp.update_user_profile(
        user_id, user_data.model_dump(exclude_unset=True))

    return updated_user


@router.put("/users/change-password", response_model=SuccessOut)
def change_password(
    password_data: ChangePassword,
    auth_data: dict = Depends(verify_access_token)
):
    """
    Change the current user's password
    - Requires authentication
    - Verifies current password and updates to new password
    """
    user_id = auth_data.get("user_id")
    if not user_id:
        raise error.AuthenticationError("Invalid authentication token")

    # Change password
    UserOp.change_password(user_id, password_data)

    return {"message": "Password changed successfully"}


@router.get("/users", response_model=list[UserOut])
def get_all_users(auth_data: dict = Depends(verify_access_token)):
    """
    Get all users
    - Requires authentication
    - Returns list of users
    """
    user_id = auth_data.get("user_id", None)
    if not (UserOp.is_user_role(user_id=user_id, role=UserRole.admin.value)):
        raise error.AuthenticationError(msg="Not allowed")
    return UserOp.get_all_users()


@router.get("/users/subscribe/{subscription_type}", response_model=SubscriptionOut)
def subscribe(
    subscription_type: SubscriptionType, token: dict = Depends(verify_access_token)
):
    """
    Subscribe a user to a package or upgrade existing subscription
    - Validates user credentials
    - Returns auth token on success
    """
    user_id = token.get("user_id")

    # Check if user already has a subscription
    has_subscribed = UserOp.get_subscription(user_id)

    if has_subscribed:
        # User already subscribed, perform upgrade
        subscription = UserOp.upgrade_subscription_package(
            user_id, subscription_type.value)
    else:
        # New subscription
        subscription = UserOp.subscribe_to_package(
            user_id, subscription_type.value)

    if not subscription:
        raise error.InvalidRequestError(msg="Invalid subscription type")

    # Invalidate cache when subscription changes
    cache_key = f"user_subscription:{user_id}"
    redis_instance.delete(cache_key)

    return {"subscription": subscription.type.value if subscription.type else None}


@router.get("/users/subscription", response_model=SubscriptionOut)
def get_subscription(token: dict = Depends(verify_access_token)):
    """
    Get a user's subscription
    - Validates user credentials
    - Returns subscription data or null if none exists
    """
    user_id = token.get("user_id")

    # Try to get from cache first
    cache_key = f"user_subscription:{user_id}"

    cached_result = redis_instance.get_json(cache_key)
    if cached_result:
        return cached_result

    # Get from database if not cached
    subscription = UserOp.get_subscription(user_id)
    if not subscription:
        # Return null subscription instead of error
        result = {"subscription": None}
    else:
        result = {"subscription": subscription.type.value}

    # Cache the result for 10 minutes
    redis_instance.set_json(cache_key, result, expiry=600)

    return result


@router.post("/users/role/{user_id}/{role}/assign", response_model=SuccessOut)
def assign_role_to_user(
    user_id: str, role: UserRole, token: dict = Depends(verify_access_token)
):
    # Get authenticated user ID and validate it exists
    auth_user_id = token.get("user_id")
    if not auth_user_id:
        raise error.AuthenticationError("Invalid authentication token")

    # Get target user and validate they exist
    user_found = UserOp.get_user_by_id(user_id)
    if not user_found:
        raise error.AuthenticationError("Target user not found")

    # Check if user has permission to assign role
    is_admin = UserOp.is_user_role(auth_user_id, UserRole.admin.value)
    is_self = auth_user_id == user_id

    if not (is_admin or is_self):
        raise error.AuthenticationError(
            "You are not authorized to perform this action")

    # Prevent non-admins from assigning admin role
    if role == UserRole.admin and not is_admin:
        raise error.AuthenticationError("Only admins can assign admin role")

    # Prevent assigning admin role to existing admin
    if role == UserRole.admin and UserOp.is_user_role(user_id, UserRole.admin.value):
        raise error.AuthenticationError("User is already an admin")

    # Assign the role
    UserOp.assign_role(user_id, role)
    return {"message": f"You have successfully assigned user with role {role}"}
