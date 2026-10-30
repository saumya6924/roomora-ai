"""Admin-controlled platform switches (stored in the platform_settings table)."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import PlatformSetting

DEFAULTS: dict[str, bool] = {
    "allow_registration": True,
    "marketplace_enabled": True,
    "designer_bookings_enabled": True,
    "email_notifications": True,  # stored only: this app sends no email
    "designer_notifications": True,
}


def get_flag(db: Session, key: str) -> bool:
    row = db.get(PlatformSetting, key)
    if row is None:
        return DEFAULTS[key]
    return bool(row.value.get("enabled", DEFAULTS[key]))


def all_flags(db: Session) -> dict[str, bool]:
    flags = dict(DEFAULTS)
    for row in db.query(PlatformSetting).all():
        if row.key in flags:
            flags[row.key] = bool(row.value.get("enabled", flags[row.key]))
    return flags


def set_flag(db: Session, key: str, enabled: bool) -> None:
    if key not in DEFAULTS:
        raise HTTPException(status_code=400, detail=f"Unknown setting '{key}'")
    row = db.get(PlatformSetting, key)
    if row is None:
        db.add(PlatformSetting(key=key, value={"enabled": enabled}))
    else:
        row.value = {"enabled": enabled}


def require_enabled(db: Session, key: str, message: str) -> None:
    if not get_flag(db, key):
        raise HTTPException(status_code=403, detail=message)
