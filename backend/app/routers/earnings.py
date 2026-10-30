"""Earnings and payout requests for sellers and designers."""

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.enums import NotificationType, PayoutStatus, Role
from app.core.security import require_role
from app.db.session import get_db
from app.models import Payout, User
from app.schemas.common import Money, ORMModel
from app.services import earnings as earnings_service
from app.services.notifications import notify_admins

router = APIRouter(tags=["Earnings & Payouts"])

earner = require_role(Role.SELLER, Role.DESIGNER)


class PayoutOut(ORMModel):
    id: int
    amount: Money
    status: PayoutStatus
    reference: str
    requested_at: datetime
    processed_at: datetime | None


class PayoutRequest(BaseModel):
    amount: Money | None = Field(default=None, gt=0)  # empty means "everything available"


@router.get("/earnings/me")
def my_earnings(user: User = Depends(earner), db: Session = Depends(get_db)):
    return {k: float(v) for k, v in earnings_service.balance(db, user).items()}


@router.get("/payouts/mine", response_model=list[PayoutOut])
def my_payouts(user: User = Depends(earner), db: Session = Depends(get_db)):
    return db.query(Payout).filter(Payout.user_id == user.id).order_by(Payout.id.desc()).all()


@router.post("/payouts", response_model=PayoutOut, status_code=201)
def request_payout(data: PayoutRequest, user: User = Depends(earner), db: Session = Depends(get_db)):
    available = earnings_service.balance(db, user)["available"]
    amount = data.amount if data.amount is not None else available
    if amount <= Decimal("0") or amount > available:
        raise HTTPException(status_code=400, detail="There is no balance available for payout")
    payout = Payout(user_id=user.id, amount=amount)
    db.add(payout)
    db.flush()
    payout.reference = f"PAY-{payout.id}"
    notify_admins(
        db, NotificationType.PAYOUT, "Payout requested", f"{user.name} requested {payout.reference}."
    )
    db.commit()
    db.refresh(payout)
    return payout
