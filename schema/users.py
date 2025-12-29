from pydantic import BaseModel
from typing import Optional
from util.enum import UserRole, SubscriptionType, Gender, Provider
from pydantic import model_validator
from uuid import UUID
from typing import Union


class SignIn(BaseModel):
    email: str
    password: str


class SignUp(BaseModel):
    email: str
    password: Optional[str]
    first_name: str
    last_name: str
    role: UserRole
    gender: Gender
    auth_provider: Optional[Provider] = None
    auth_provider_id: Optional[str] = None


class SignUpOTP(BaseModel):
    email: str
    otp: str


class ResendOTP(BaseModel):
    email: str


class SubscriptionOut(BaseModel):
    subscription: Union[SubscriptionType, None]


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_picture: Optional[str] = None


class ChangePassword(BaseModel):
    current_password: str
    new_password: str


class UserOut(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    role: UserRole
    gender: Gender
    profile_picture: Optional[str] = None
    is_active: bool
    is_verified: bool
    is_subscribed: bool
    has_enrolled: bool

    @model_validator(mode="before")
    def split_full_name(cls, data):
        if isinstance(data, dict):
            if "full_name" in data:
                first_name, last_name = data["full_name"].split("-")
                data["first_name"] = first_name
                data["last_name"] = last_name
                del data["full_name"]
        else:
            if hasattr(data, "full_name"):
                first_name, last_name = data.full_name.split("-")
                data.first_name = first_name
                data.last_name = last_name
                delattr(data, "full_name")
        return data

    class Config:
        from_attributes = True


class SignInOut(BaseModel):
    user: UserOut
    access_token: str
    token_type: str = "bearer"


class AuthRequest(BaseModel):
    code: str
