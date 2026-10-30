"""Everything the Admin dashboard needs. Every route here is admin-only."""

from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.enums import (
    BookingStatus,
    DesignerStatus,
    NotificationType,
    OrderItemStatus,
    PayoutStatus,
    ProductStatus,
    Role,
    SellerStatus,
)
from app.core.security import require_role
from app.db.session import get_db
from app.models import (
    Booking,
    DesignerProfile,
    Order,
    OrderItem,
    Payout,
    Product,
    Review,
    SellerProfile,
    User,
)
from app.routers._common import parse_enum
from app.schemas.auth import UserOut
from app.schemas.catalog import ProductOut
from app.schemas.commerce import OrderOut
from app.schemas.common import Money, StatusUpdate
from app.services import orders as order_service
from app.services import platform
from app.services.export import csv_response
from app.services.notifications import notify
from app.services.reviews import summarize
from app.services.stats import as_utc, growth, monthly_series, now_utc, this_and_last_month

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_role(Role.ADMIN))],
)
admin_user = require_role(Role.ADMIN)


# ---------------------------------------------------------------- shared helpers
def _value(item: OrderItem) -> float:
    return float(item.price * item.quantity)


def transactions(db: Session) -> list[dict]:
    """Furniture orders and designer bookings as one list, newest first (the admin Orders view)."""
    rows = []
    orders = db.query(Order).options(joinedload(Order.items)).all()
    for order in orders:
        first = order.items[0].product_name if order.items else "-"
        extra = f" +{len(order.items) - 1} more" if len(order.items) > 1 else ""
        rows.append(
            {
                "id": order.id,
                "ref": f"#RM{order.id}",
                "kind": "Furniture",
                "customer": order.full_name,
                "item": first + extra,
                "amount": float(order.total_amount),
                "payment": order.payment_status.value,
                "status": order_service.order_status(order),
                "created_at": order.created_at,
            }
        )
    bookings = db.query(Booking).options(joinedload(Booking.designer)).all()
    for b in bookings:
        rows.append(
            {
                "id": b.id,
                "ref": f"#DB{b.id}",
                "kind": "Designer",
                "customer": b.name,
                "item": f"{b.designer.user.name} · {b.days} Day{'s' if b.days != 1 else ''}",
                "amount": float(b.total_amount),
                "payment": "paid" if b.status == BookingStatus.COMPLETED else "pending",
                "status": b.status.value,
                "created_at": b.created_at,
            }
        )
    return sorted(rows, key=lambda r: as_utc(r["created_at"]), reverse=True)


def _revenue_rows(db: Session) -> list[tuple[datetime, float]]:
    """(when, amount) for every non-cancelled order item and every non-declined booking."""
    rows = [
        (i.order.created_at, _value(i))
        for i in db.query(OrderItem).options(joinedload(OrderItem.order)).all()
        if i.status != OrderItemStatus.CANCELLED
    ]
    rows += [
        (b.created_at, float(b.total_amount))
        for b in db.query(Booking).all()
        if b.status != BookingStatus.DECLINED
    ]
    return rows


# ---------------------------------------------------------------- dashboard
@router.get("/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    """Headline counts (also used by the tests and the CSV export)."""
    revenue = (
        db.query(func.sum(OrderItem.price * OrderItem.quantity))
        .filter(OrderItem.status != OrderItemStatus.CANCELLED)
        .scalar()
    ) or Decimal("0")
    return {
        "total_users": db.query(User).filter(User.role == Role.USER).count(),
        "total_sellers": db.query(User).filter(User.role == Role.SELLER).count(),
        "total_designers": db.query(DesignerProfile).count(),
        "total_products": db.query(Product).count(),
        "products_pending_approval": db.query(Product)
        .filter(Product.status == ProductStatus.PENDING)
        .count(),
        "designers_pending_approval": db.query(DesignerProfile)
        .filter(DesignerProfile.status == DesignerStatus.PENDING)
        .count(),
        "total_orders": db.query(Order).count(),
        "total_bookings": db.query(Booking).count(),
        "revenue_inr": float(revenue),
    }


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    users = db.query(User).filter(User.role == Role.USER).all()
    active_cutoff = now_utc() - timedelta(days=30)
    active = sum(1 for u in users if u.last_login_at and as_utc(u.last_login_at) >= active_cutoff)
    users_now, users_before = this_and_last_month((u.created_at, 1) for u in users)

    rev_now, rev_before = this_and_last_month(_revenue_rows(db))
    all_tx = transactions(db)
    orders_now, orders_before = this_and_last_month((t["created_at"], 1) for t in all_tx)

    designers = db.query(DesignerProfile).all()
    sellers = db.query(User).filter(User.role == Role.SELLER).all()
    today = now_utc().date()
    today_tx = [t for t in all_tx if as_utc(t["created_at"]).date() == today]
    return {
        "total_users": len(users),
        "users_growth": growth(users_now, users_before),
        "active_users": active,
        "active_percent": round(100 * active / len(users), 1) if users else 0,
        "total_products": db.query(Product).count(),
        "products_pending": db.query(Product).filter(Product.status == ProductStatus.PENDING).count(),
        "total_designers": len(designers),
        "designers_available": sum(
            1 for d in designers if d.status == DesignerStatus.APPROVED and d.is_available
        ),
        "month_revenue": rev_now,
        "revenue_growth": growth(rev_now, rev_before),
        "total_orders": len(all_tx),
        "orders_growth": growth(orders_now, orders_before),
        "pending_requests": db.query(Booking).filter(Booking.status == BookingStatus.PENDING).count(),
        "total_sellers": len(sellers),
        "sellers_active": sum(1 for s in sellers if s.is_active),
        "recent_orders": all_tx[:4],
        "activity_today": {
            "new_users": sum(1 for u in users if as_utc(u.created_at).date() == today),
            "products_added": db.query(Product)
            .filter(Product.created_at >= datetime.combine(today, datetime.min.time()))
            .count(),
            "designer_requests": sum(1 for t in today_tx if t["kind"] == "Designer"),
            "revenue": sum(t["amount"] for t in today_tx if t["status"] != "cancelled"),
        },
        "system": {
            "database": "operational",
            "ai_engine": "claude" if settings.anthropic_api_key else "rules",
            "payments": "record-only",
        },
    }


# ---------------------------------------------------------------- users
class UserAdminOut(UserOut):
    orders: int
    last_active: datetime | None
    status: str


@router.get("/users", response_model=list[UserAdminOut])
def list_users(search: str | None = None, role: str | None = None, db: Session = Depends(get_db)):
    query = db.query(User)
    if role:
        query = query.filter(User.role == parse_enum(Role, role, "Role"))
    if search:
        query = query.filter(User.name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%"))

    counts: dict[int, int] = {}
    for user_id, n in db.query(Order.user_id, func.count(Order.id)).group_by(Order.user_id):
        counts[user_id] = n
    for user_id, n in db.query(Booking.user_id, func.count(Booking.id)).group_by(Booking.user_id):
        counts[user_id] = counts.get(user_id, 0) + n

    cutoff = now_utc() - timedelta(days=30)
    result = []
    for user in query.order_by(User.id).all():
        if not user.is_active:
            status = "blocked"
        elif user.last_login_at and as_utc(user.last_login_at) >= cutoff:
            status = "active"
        else:
            status = "inactive"
        result.append(
            {
                **UserOut.model_validate(user).model_dump(),
                "orders": counts.get(user.id, 0),
                "last_active": user.last_login_at,
                "status": status,
            }
        )
    return result


class RoleUpdate(BaseModel):
    role: str


@router.patch("/users/{user_id}/role", response_model=UserOut)
def change_role(
    user_id: int,
    data: RoleUpdate,
    admin: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    new_role = parse_enum(Role, data.role, "Role")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id and new_role != Role.ADMIN:
        raise HTTPException(status_code=400, detail="You cannot remove your own admin role")

    user.role = new_role
    # A seller or designer needs a profile row, or their dashboard has nothing to show.
    if new_role == Role.DESIGNER and not db.query(DesignerProfile).filter_by(user_id=user.id).first():
        db.add(DesignerProfile(user_id=user.id, status=DesignerStatus.PENDING))
    if new_role == Role.SELLER and not db.query(SellerProfile).filter_by(user_id=user.id).first():
        db.add(SellerProfile(user_id=user.id, store_name=user.name))
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/block", response_model=UserOut)
def block_or_unblock(
    user_id: int,
    admin: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot block yourself")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------- products
class ProductAdminOut(ProductOut):
    seller_name: str


@router.get("/products", response_model=list[ProductAdminOut])
def all_products(
    search: str | None = None,
    category: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Product).options(joinedload(Product.seller), joinedload(Product.images))
    if status:
        query = query.filter(Product.status == parse_enum(ProductStatus, status))
    if category:
        query = query.filter(Product.category == category)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    out = []
    for p in query.order_by(Product.id.desc()).all():
        profile = db.query(SellerProfile).filter_by(user_id=p.seller_id).first()
        out.append(
            {
                **ProductOut.model_validate(p).model_dump(),
                "seller_name": (profile.store_name if profile and profile.store_name else p.seller.name),
            }
        )
    return out


# ---------------------------------------------------------------- designers and bookings
@router.get("/designers")
def all_designers(db: Session = Depends(get_db)):
    today = now_utc().date()
    out = []
    for d in db.query(DesignerProfile).options(joinedload(DesignerProfile.user)).order_by(DesignerProfile.id):
        bookings = db.query(Booking).filter(Booking.designer_id == d.id).all()
        busy = any(
            b.status == BookingStatus.ACCEPTED
            and b.start_date <= today <= b.start_date + timedelta(days=b.days - 1)
            for b in bookings
        )
        rating = summarize(r[0] for r in db.query(Review.rating).filter(Review.designer_id == d.id))
        out.append(
            {
                "id": d.id,
                "user_id": d.user_id,
                "name": d.user.name,
                "title": d.title,
                "speciality": d.speciality,
                "price_per_day": float(d.price_per_day),
                "status": d.status,
                "availability": "offline" if not d.is_available else "booked" if busy else "available",
                "projects": sum(1 for b in bookings if b.status == BookingStatus.COMPLETED),
                "rating": rating["average"],
                "review_count": rating["count"],
            }
        )
    return out


@router.get("/bookings")
def all_bookings(db: Session = Depends(get_db)):
    rows = db.query(Booking).options(joinedload(Booking.designer)).order_by(Booking.id.desc()).all()
    return [
        {
            "id": b.id,
            "ref": f"#DR{b.id}",
            "customer": b.name,
            "project_type": b.project_type,
            "designer": b.designer.user.name,
            "start_date": b.start_date,
            "days": b.days,
            "amount": float(b.total_amount),
            "status": b.status.value,
            "created_at": b.created_at,
        }
        for b in rows
    ]


# ---------------------------------------------------------------- orders
@router.get("/orders", response_model=list[OrderOut])
def all_orders(db: Session = Depends(get_db)):
    return db.query(Order).order_by(Order.id.desc()).all()


@router.get("/transactions")
def all_transactions(db: Session = Depends(get_db)):
    """Furniture orders and designer bookings together, for the Orders page."""
    return transactions(db)


# ---------------------------------------------------------------- sellers
@router.get("/sellers")
def all_sellers(db: Session = Depends(get_db)):
    out = []
    for user in db.query(User).filter(User.role == Role.SELLER).order_by(User.id):
        profile = db.query(SellerProfile).filter_by(user_id=user.id).first()
        items = db.query(OrderItem).filter(OrderItem.seller_id == user.id).all()
        live = [i for i in items if i.status != OrderItemStatus.CANCELLED]
        out.append(
            {
                "user_id": user.id,
                "owner": user.name,
                "email": user.email,
                "business": profile.store_name if profile else user.name,
                "status": profile.status.value if profile else SellerStatus.ACTIVE.value,
                "products": db.query(Product).filter(Product.seller_id == user.id).count(),
                "orders": len({i.order_id for i in items}),
                "revenue": round(sum(_value(i) for i in live), 2),
            }
        )
    return out


@router.patch("/sellers/{user_id}/status")
def set_seller_status(user_id: int, data: StatusUpdate, db: Session = Depends(get_db)):
    new_status = parse_enum(SellerStatus, data.status)
    user = db.get(User, user_id)
    if user is None or user.role != Role.SELLER:
        raise HTTPException(status_code=404, detail="Seller not found")
    profile = db.query(SellerProfile).filter_by(user_id=user.id).first()
    if profile is None:
        profile = SellerProfile(user_id=user.id, store_name=user.name)
        db.add(profile)
    profile.status = new_status
    db.commit()
    return {"user_id": user.id, "status": new_status.value}


# ---------------------------------------------------------------- reports and settings
@router.get("/reports")
def reports(db: Session = Depends(get_db)):
    furniture = db.query(Order).count()
    designer = db.query(Booking).count()
    total = furniture + designer
    return {
        "monthly_revenue": monthly_series(_revenue_rows(db)),
        "total_orders": total,
        "furniture_percent": round(100 * furniture / total) if total else 0,
        "designer_percent": round(100 * designer / total) if total else 0,
    }


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    return platform.all_flags(db)


@router.put("/settings")
def update_settings(data: dict[str, bool], db: Session = Depends(get_db)):
    for key, enabled in data.items():
        platform.set_flag(db, key, enabled)
    db.commit()
    return platform.all_flags(db)


# ---------------------------------------------------------------- payouts
class PayoutAdminOut(BaseModel):
    id: int
    user_id: int
    user_name: str
    role: str
    amount: Money
    status: PayoutStatus
    reference: str
    requested_at: datetime
    processed_at: datetime | None


@router.get("/payouts", response_model=list[PayoutAdminOut])
def all_payouts(db: Session = Depends(get_db)):
    rows = db.query(Payout).options(joinedload(Payout.user)).order_by(Payout.id.desc()).all()
    return [
        {
            "id": p.id,
            "user_id": p.user_id,
            "user_name": p.user.name,
            "role": p.user.role.value,
            "amount": p.amount,
            "status": p.status,
            "reference": p.reference,
            "requested_at": p.requested_at,
            "processed_at": p.processed_at,
        }
        for p in rows
    ]


@router.patch("/payouts/{payout_id}", response_model=PayoutAdminOut)
def set_payout_status(payout_id: int, data: StatusUpdate, db: Session = Depends(get_db)):
    new_status = parse_enum(PayoutStatus, data.status)
    payout = db.get(Payout, payout_id)
    if payout is None:
        raise HTTPException(status_code=404, detail="Payout not found")
    if payout.status in (PayoutStatus.COMPLETED, PayoutStatus.REJECTED):
        raise HTTPException(status_code=400, detail=f"This payout is already {payout.status.value}")
    payout.status = new_status
    if new_status in (PayoutStatus.COMPLETED, PayoutStatus.REJECTED):
        payout.processed_at = now_utc()
    notify(
        db,
        payout.user_id,
        NotificationType.PAYOUT,
        f"Payout {new_status.value}",
        f"{payout.reference} is now {new_status.value}",
    )
    db.commit()
    return all_payouts_row(payout)


def all_payouts_row(p: Payout) -> dict:
    return {
        "id": p.id,
        "user_id": p.user_id,
        "user_name": p.user.name,
        "role": p.user.role.value,
        "amount": p.amount,
        "status": p.status,
        "reference": p.reference,
        "requested_at": p.requested_at,
        "processed_at": p.processed_at,
    }


# ---------------------------------------------------------------- CSV export
@router.get("/export/users.csv")
def export_users(db: Session = Depends(get_db)) -> Response:
    rows = [
        [
            u.id,
            u.name,
            u.email,
            u.mobile,
            u.role.value,
            "yes" if u.is_active else "blocked",
            as_utc(u.created_at).date().isoformat(),
        ]
        for u in db.query(User).order_by(User.id)
    ]
    return csv_response("users.csv", ["ID", "Name", "Email", "Mobile", "Role", "Active", "Joined"], rows)


@router.get("/export/orders.csv")
def export_orders(db: Session = Depends(get_db)) -> Response:
    rows = [
        [
            t["ref"],
            as_utc(t["created_at"]).date().isoformat(),
            t["kind"],
            t["customer"],
            t["item"],
            t["amount"],
            t["payment"],
            t["status"],
        ]
        for t in transactions(db)
    ]
    return csv_response(
        "orders.csv", ["Reference", "Date", "Type", "Customer", "Item", "Amount", "Payment", "Status"], rows
    )
