import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.enums import Role
from app.schemas.common import ORMModel


def _check_password_strength(value: str) -> str:
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password needs one capital letter")
    if not re.search(r"[0-9]", value):
        raise ValueError("Password needs one number")
    if not re.search(r"[^A-Za-z0-9]", value):
        raise ValueError("Password needs one special character")
    return value


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    mobile: str = Field(min_length=10, max_length=20)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("email")
    @classmethod
    def gmail_only(cls, value):
        # Public signup is Gmail-only. Login accepts any address so seeded staff accounts work.
        if not str(value).lower().endswith("@gmail.com"):
            raise ValueError("Only Gmail addresses (@gmail.com) are allowed")
        return value

    _strong = field_validator("password")(_check_password_strength)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORMModel):
    id: int
    name: str
    email: str
    mobile: str
    role: Role
    is_active: bool
    location: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    mobile: str | None = Field(default=None, min_length=10, max_length=20)
    location: str | None = Field(default=None, max_length=120)
    notification_prefs: dict[str, bool] | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=72)

    _strong = field_validator("new_password")(_check_password_strength)
