"""Creates in-app notifications. Callers commit the session themselves."""

from sqlalchemy.orm import Session

from app.core.enums import NotificationType, Role
from app.models import Notification, User


def notify(db: Session, user_id: int, kind: NotificationType, title: str, body: str = "") -> None:
    db.add(Notification(user_id=user_id, type=kind, title=title[:150], body=body[:400]))


def notify_admins(db: Session, kind: NotificationType, title: str, body: str = "") -> None:
    for admin_id in db.query(User.id).filter(User.role == Role.ADMIN, User.is_active.is_(True)):
        notify(db, admin_id[0], kind, title, body)
