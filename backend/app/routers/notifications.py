"""The bell icon: a user's own notifications."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.enums import NotificationType
from app.core.security import get_current_user
from app.db.session import get_db
from app.models import Notification, User
from app.schemas.common import Message, ORMModel

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationOut(ORMModel):
    id: int
    type: NotificationType
    title: str
    body: str
    is_read: bool
    created_at: datetime


class NotificationList(BaseModel):
    unread: int
    items: list[NotificationOut]


@router.get("", response_model=NotificationList)
def my_notifications(limit: int = 50, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Notification).filter(Notification.user_id == user.id)
    unread = query.filter(Notification.is_read.is_(False)).count()
    items = query.order_by(Notification.id.desc()).limit(min(limit, 100)).all()
    return {"unread": unread, "items": items}


@router.post("/read-all", response_model=Message)
def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    db.commit()
    return {"message": "All notifications marked as read"}


@router.patch("/{notification_id}/read", response_model=Message)
def mark_read(notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(Notification, notification_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    item.is_read = True
    db.commit()
    return {"message": "Marked as read"}
