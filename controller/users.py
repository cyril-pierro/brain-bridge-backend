from model.users import User, pwd_hasher
from model.subscription import Subscription
from schema.users import SignUp, SignIn, ChangePassword
from util.gen import generate_otp
from service.redis import Redis
from service.auth import TokenManager
import error
from util.enum import UserRole, SubscriptionType, Gender, Provider
from config.setting import settings
from pydantic import EmailStr

redis = Redis()
INVALID_REQUEST = "Invalid Request"


class UserOp:
    @staticmethod
    def register(user_details: SignUp) -> tuple[User, str]:
        # Check if user already exists
        user = User.get_user_by_email(user_details.email)
        if user:
            raise error.InvalidRequestError(msg="User already exists")

        user_created = User.add(user_details)
        # Generate OTP for the new user
        otp = generate_otp()
        # Store OTP in Redis with user email as key
        redis.set(
            f"register-{user_created.email}",
            otp,
            expiry=settings.USER_REGISTER_EXPIRE_SECONDS,
        )
        return user_created, otp

    @staticmethod
    def get_all_users() -> list[User]:
        return User.get_users()

    @staticmethod
    def verify_user_otp(email: EmailStr, otp: str) -> bool:
        user = User.get_user_by_email(email)
        if not user:
            return False
        if user.is_verified:
            return False
        # verify user otp
        stored_otp = redis.get(f"register-{email}")
        if not stored_otp or int(stored_otp) != int(otp):
            return False
        user.is_verified = True
        user.save()
        redis.delete(f"register-{email}")
        return True

    @staticmethod
    def resend_otp(email: EmailStr) -> tuple[User, str]:
        user = User.get_user_by_email(email)
        if not user:
            raise error.InvalidRequestError(msg="User not found")
        if user.is_verified:
            raise error.InvalidRequestError(msg="User already verified")
        otp = generate_otp()
        redis.set(
            f"register-{email}",
            otp,
            expiry=settings.USER_REGISTER_EXPIRE_SECONDS,
        )
        return user, otp

    @staticmethod
    def login(user_details: SignIn):
        user = User.get_user_by_email(user_details.email)
        if not user:
            raise error.AuthenticationError(msg="Invalid credentials")
        if not User.verify_password(user_details.password, user.hashed_password):
            raise error.AuthenticationError(msg="Invalid credentials")

        if not user.is_verified:
            raise error.AuthenticationError(msg="User not verified")

        # Check if user has valid token in Redis
        existing_token = redis.get(f"token-{user.id}")
        if existing_token:
            return user, existing_token

        # Generate new access token if none exists
        access_token = TokenManager.create_access_token(
            data={"user_id": user.id},
            expires_in_minutes=settings.USER_LOGIN_EXPIRE_SECONDS,
        )

        # Store token in Redis with same expiry as token
        redis.set(
            f"token-{user.id}",
            access_token,
            expiry=settings.USER_LOGIN_EXPIRE_SECONDS * 60,
        )

        return user, access_token

    @staticmethod
    def get_user_by_id(user_id: str) -> User:
        user = User.get_user_by_id(user_id)
        if not user:
            raise error.InvalidRequestError(msg=INVALID_REQUEST)
        return user

    @staticmethod
    def is_user_role(user_id: str, role: UserRole) -> bool:
        user = UserOp.get_user_by_id(user_id=user_id)
        return user.role == role

    @staticmethod
    def assign_role(user_id: str, role: UserRole) -> User:
        user = UserOp.get_user_by_id(user_id=user_id)
        updated_user = user.update(**{"role": role})
        return updated_user

    @staticmethod
    def subscribe_to_package(
        user_id: str, subscription_type: SubscriptionType
    ) -> Subscription:
        has_subscribed = Subscription.get_subscription_by_user_id(
            user_id=user_id)
        if has_subscribed:
            raise error.InvalidRequestError(msg="User already subscribed")
        subscription = Subscription.subscribe(
            user_id=user_id, subscription_type=subscription_type
        )
        UserOp.get_user_by_id(user_id=user_id).update(
            **{"is_subscribed": True})
        return subscription

    @staticmethod
    def get_subscription(user_id: str) -> Subscription:
        return Subscription.get_subscription_by_user_id(user_id=user_id)

    @staticmethod
    def update_user_profile(user_id: str, update_data: dict) -> User:
        """Update user profile information"""
        user = UserOp.get_user_by_id(user_id=user_id)

        # Only allow updating specific fields
        allowed_fields = {'profile_picture'}
        filtered_data = {k: v for k, v in update_data.items()
                         if k in allowed_fields and v is not None}

        # Combine first_name and last_name into full_name if present
        if 'first_name' in update_data or 'last_name' in update_data:
            first_name = update_data.get('first_name')
            last_name = update_data.get('last_name')
            filtered_data['full_name'] = f"{first_name}-{last_name}"

        if filtered_data:
            updated_user = user.update(**filtered_data)
            return updated_user

        return user

    @staticmethod
    def change_password(user_id: str, password_data: ChangePassword) -> User:
        """Change user password"""
        user = UserOp.get_user_by_id(user_id=user_id)

        # Verify current password
        if not User.verify_password(password_data.current_password, user.hashed_password):
            raise error.AuthenticationError(
                msg="Current password is incorrect")

        # Hash new password and update - using the optimized password hasher
        hashed_new_password = pwd_hasher.hash(password_data.new_password)

        updated_user = user.update(**{"hashed_password": hashed_new_password})
        return updated_user

    @staticmethod
    def upgrade_subscription_package(
        user_id: str, subscription_type: SubscriptionType
    ) -> Subscription:
        has_subscribed = Subscription.get_subscription_by_user_id(
            user_id=user_id)
        if not has_subscribed:
            raise error.InvalidRequestError(
                msg="Please subscribe to a package")

        if (
            has_subscribed.type == SubscriptionType.premium.value
            and subscription_type == SubscriptionType.free.value
        ):
            raise error.InvalidRequestError(
                msg="Cannot downgrade from premium to free subscription"
            )

        # Delete previous subscription
        has_subscribed.delete()

        # Create new subscription
        subscription = Subscription.subscribe(
            user_id=user_id, subscription_type=subscription_type
        )
        # Ensure user is marked as subscribed (should already be true, but just in case)
        UserOp.get_user_by_id(user_id=user_id).update(
            **{"is_subscribed": True})
        return subscription

    @staticmethod
    def get_or_create_oauth_user(user_info: dict, provider: Provider) -> User:
        """Get existing user or create new OAuth user"""
        email = user_info.get("email")
        if not email:
            raise error.InvalidRequestError(
                msg="Email not provided by OAuth provider")

        # Check if user already exists
        user = User.get_user_by_email(email)
        if user:
            # Update OAuth info if needed
            if not user.auth_provider:
                user.update(auth_provider=provider,
                            auth_provider_id=user_info.get("sub"))
            return user

        # Create new user
        name = user_info.get("name", "")
        first_name, last_name = (name.split(
            " ", 1) + [""])[:2] if name else ("", "")
        user_data = SignUp(
            email=email,
            password=None,  # OAuth users don't have passwords
            first_name=first_name,
            last_name=last_name,
            role=UserRole.student,  # Default role
            gender=Gender.male,  # Default gender
            auth_provider=provider,
            auth_provider_id=user_info.get("sub"),
        )
        # Use create method with explicit unique UUID generation for OAuth users
        from uuid import uuid4
        # Generate a unique UUID by checking if it already exists
        user_id = uuid4()
        while User.get_user_by_id(str(user_id)):
            user_id = uuid4()

        new_user = User.create({
            'id': user_id,
            'email': user_data.email,
            'full_name': f"{user_data.first_name}-{user_data.last_name}",
            'hashed_password': None,
            'gender': user_data.gender.value,
            'auth_provider': user_data.auth_provider,
            'auth_provider_id': user_data.auth_provider_id,
            'is_verified': True,  # OAuth users are pre-verified
        })
        return new_user
