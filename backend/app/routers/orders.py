"""Checkout and order tracking.

The cart lives in the browser (localStorage); the backend only gets involved at checkout.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.enums import OrderItemStatus, Role
from app.core.security import get_current_user, require_role
from app.db.session import get_db
from app.models import Order, OrderItem, User
from app.routers._common import parse_enum
from app.schemas.commerce import OrderCreate, OrderOut, SellerOrderRow
from app.schemas.common import StatusUpdate
from app.services import orders as order_service

router = APIRouter(prefix="/orders", tags=["Orders & Checkout"])

seller_or_admin = require_role(Role.SELLER, Role.ADMIN)


@router.post("", response_model=OrderOut, status_code=201)
def place_order(
    data: OrderCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return order_service.place_order(db, user, data)


@router.get("/mine", response_model=list[OrderOut])
def my_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Order).filter(Order.user_id == user.id).order_by(Order.id.desc()).all()


@router.get("/seller", response_model=list[SellerOrderRow])
def seller_orders(seller: User = Depends(seller_or_admin), db: Session = Depends(get_db)):
    """Seller dashboard: only the items of MY products."""
    items = db.query(OrderItem).filter(OrderItem.seller_id == seller.id).order_by(OrderItem.id.desc()).all()
    return [order_service.seller_row(i) for i in items]


@router.patch("/items/{item_id}/status", response_model=SellerOrderRow)
def update_item_status(
    item_id: int,
    data: StatusUpdate,
    seller: User = Depends(seller_or_admin),
    db: Session = Depends(get_db),
):
    """Seller presses 'Mark as packed / shipped / delivered'."""
    new_status = parse_enum(OrderItemStatus, data.status)
    item = db.get(OrderItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Order item not found")
    if seller.role != Role.ADMIN and item.seller_id != seller.id:
        raise HTTPException(status_code=403, detail="This is not your order")
    if item.status in (OrderItemStatus.DELIVERED, OrderItemStatus.CANCELLED):
        raise HTTPException(status_code=400, detail=f"This item is already {item.status.value}")

    item = order_service.set_item_status(db, item, new_status)
    return order_service.seller_row(item)


@router.patch("/items/{item_id}/cancel", response_model=OrderOut)
def cancel_my_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The customer cancels an item, allowed only until the seller has packed it."""
    item = db.get(OrderItem, item_id)
    if item is None or item.order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Order item not found")
    if item.status != OrderItemStatus.PLACED:
        raise HTTPException(status_code=400, detail=f"Too late to cancel - it is already {item.status.value}")

    order_service.set_item_status(db, item, OrderItemStatus.CANCELLED)
    db.refresh(item.order)
    return item.order
