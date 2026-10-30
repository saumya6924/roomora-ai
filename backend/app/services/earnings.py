"""Earnings and payout balances for sellers and designers.

Money moves nowhere in this app: a payout is a mock settlement that an admin marks completed.
Sellers earn from delivered order items; designers earn from completed bookings.
"""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.enums import BookingStatus, OrderItemStatus, PayoutStatus, Role
from app.models import Booking, DesignerProfile, OrderItem, Payout, User

ZERO = Decimal("0")


def month_start(now: datetime | None = None) -> datetime:
    now = now or datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _seller_figures(db: Session, user: User) -> tuple[Decimal, Decimal, Decimal]:
    """(total earned, earned this month, still to be delivered)."""
    value = OrderItem.price * OrderItem.quantity
    base = db.query(func.coalesce(func.sum(value), 0)).filter(OrderItem.seller_id == user.id)
    total = base.filter(OrderItem.status == OrderItemStatus.DELIVERED).scalar()
    month = base.filter(
        OrderItem.status == OrderItemStatus.DELIVERED, OrderItem.updated_at >= month_start()
    ).scalar()
    pending = base.filter(
        OrderItem.status.in_([OrderItemStatus.PLACED, OrderItemStatus.PACKED, OrderItemStatus.SHIPPED])
    ).scalar()
    return Decimal(total), Decimal(month), Decimal(pending)


def _designer_figures(db: Session, user: User) -> tuple[Decimal, Decimal, Decimal]:
    profile = db.query(DesignerProfile).filter(DesignerProfile.user_id == user.id).first()
    if profile is None:
        return ZERO, ZERO, ZERO
    base = db.query(func.coalesce(func.sum(Booking.total_amount), 0)).filter(
        Booking.designer_id == profile.id
    )
    total = base.filter(Booking.status == BookingStatus.COMPLETED).scalar()
    month = base.filter(
        Booking.status == BookingStatus.COMPLETED, Booking.completed_at >= month_start()
    ).scalar()
    pending = base.filter(Booking.status == BookingStatus.ACCEPTED).scalar()
    return Decimal(total), Decimal(month), Decimal(pending)


def balance(db: Session, user: User) -> dict:
    total, month, pending_earnings = (
        _seller_figures(db, user) if user.role in (Role.SELLER, Role.ADMIN) else _designer_figures(db, user)
    )
    payout_sum = lambda *statuses: Decimal(  # noqa: E731
        db.query(func.coalesce(func.sum(Payout.amount), 0))
        .filter(Payout.user_id == user.id, Payout.status.in_(statuses))
        .scalar()
    )
    in_flight = payout_sum(PayoutStatus.REQUESTED, PayoutStatus.PROCESSING)
    paid_out = payout_sum(PayoutStatus.COMPLETED)
    return {
        "total_earnings": total,
        "this_month": month,
        "available": max(total - in_flight - paid_out, ZERO),
        "pending_payout": in_flight,
        "paid_out": paid_out,
        "pending_earnings": pending_earnings,
    }
