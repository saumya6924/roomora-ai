"""Signup, login, and "who am I?"."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import NotificationType, Role
from app.core.ratelimit import login_limit, signup_limit
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models import User
from app.schemas.auth import (
    LoginRequest,
    PasswordChange,
    ProfileUpdate,
    SignupRequest,
    TokenOut,
    UserOut,
)
from app.schemas.common import Message
from app.services.notifications import notify_admins
from app.services.platform import require_enabled

router = APIRouter(prefix="/auth", tags=["Login & Signup"])


@router.post("/signup", response_model=TokenOut, status_code=201, dependencies=[Depends(signup_limit)])
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    require_enabled(db, "allow_registration", "New registrations are currently closed")
    email = data.email.lower()

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="This email is already registered")

    # Public signup always creates a normal customer. Only an admin can grant other roles.
    user = User(
        name=data.name,
        email=email,
        mobile=data.mobile,
        password_hash=hash_password(data.password),
        role=Role.USER,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # two signups with the same email at the same moment
        db.rollback()
        raise HTTPException(status_code=400, detail="This email is already registered") from None
    db.refresh(user)
    return {"access_token": create_access_token(user.id), "user": user}


@router.post("/login", response_model=TokenOut, dependencies=[Depends(login_limit)])
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower()).first()

    # Same message for "no such email" and "wrong password".
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Wrong email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account is blocked")

    user.last_login_at = datetime.now(UTC)
    db.commit()
    return {"access_token": create_access_token(user.id), "user": user}


@router.get("/me", response_model=UserOut)
def who_am_i(current_user: User = Depends(get_current_user)):
    """The frontend calls this on every page load to confirm the login and the role."""
    return current_user


@router.patch("/me", response_model=UserOut)
def update_profile(
    data: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    for field, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        if field == "notification_prefs":
            user.notification_prefs = {**(user.notification_prefs or {}), **value}
        else:
            setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.post("/change-password", response_model=Message, dependencies=[Depends(login_limit)])
def change_password(
    data: PasswordChange,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"message": "Password updated"}


@router.post("/delete-request", response_model=Message)
def request_account_deletion(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Tell the admins that this user wants their account removed. Nothing is deleted automatically."""
    notify_admins(
        db,
        NotificationType.SYSTEM,
        "Account deletion requested",
        f"{user.name} ({user.email}) asked to delete their account.",
    )
    db.commit()
    return {"message": "Account deletion request submitted"}
