"""Everything the Admin dashboard needs. Every route here is admin-only."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.enums import DesignerStatus, OrderItemStatus, ProductStatus, Role
from app.core.security import require_role
from app.db.session import get_db
from app.models import (
    Booking,
    DesignerProfile,
    Order,
    OrderItem,
    Product,
    SellerProfile,
    User,
)
from app.routers._common import parse_enum
from app.schemas.auth import UserOut
from app.schemas.commerce import OrderOut

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_role(Role.ADMIN))],
)


@router.get("/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    """The numbers on the admin dashboard cards."""
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


@router.get("/users", response_model=list[UserOut])
def list_users(search: str | None = None, role: str | None = None, db: Session = Depends(get_db)):
    query = db.query(User)
    if role:
        query = query.filter(User.role == parse_enum(Role, role, "Role"))
    if search:
        query = query.filter(User.name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%"))
    return query.order_by(User.id).all()


class RoleUpdate(BaseModel):
    role: str


@router.patch("/users/{user_id}/role", response_model=UserOut)
def change_role(
    user_id: int,
    data: RoleUpdate,
    admin: User = Depends(require_role(Role.ADMIN)),
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
    admin: User = Depends(require_role(Role.ADMIN)),
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


@router.get("/orders", response_model=list[OrderOut])
def all_orders(db: Session = Depends(get_db)):
    return db.query(Order).order_by(Order.id.desc()).all()
