"""Passwords, login tokens, and "who is calling the API?"."""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import Role
from app.db.session import get_db
from app.models import User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int) -> str:
    expires = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": str(user_id), "exp": expires}, settings.secret_key, algorithm="HS256")


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    problem = HTTPException(status.HTTP_401_UNAUTHORIZED, "Please login first")
    if credentials is None:
        raise problem
    try:
        data = jwt.decode(credentials.credentials, settings.secret_key, algorithms=["HS256"])
        user_id = int(data["sub"])
    except Exception:  # expired, fake or broken token
        raise problem from None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise problem
    return user


def require_role(*allowed: Role):
    """Use as Depends(require_role(Role.ADMIN)) or Depends(require_role(Role.SELLER, Role.ADMIN))."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not allowed to do this")
        return user

    return checker
