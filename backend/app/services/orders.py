"""Checkout and order-item lifecycle. Prices always come from the database, never the browser."""

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import NotificationType, OrderItemStatus, PaymentStatus, ProductStatus
from app.models import Order, OrderItem, Product, User
from app.schemas.commerce import OrderCreate
from app.services.notifications import notify
from app.services.platform import require_enabled


def place_order(db: Session, user: User, data: OrderCreate) -> Order:
    require_enabled(db, "marketplace_enabled", "The marketplace is temporarily closed")

    # The same product twice in the cart becomes one line.
    wanted: dict[int, int] = {}
    for item in data.items:
        wanted[item.product_id] = wanted.get(item.product_id, 0) + item.quantity

    order = Order(
        user_id=user.id,
        payment_method=data.payment_method,
        full_name=data.full_name,
        mobile=data.mobile,
        address=data.address,
        city=data.city,
        state=data.state,
        pincode=data.pincode,
    )

    total = Decimal("0")
    # Lock the rows in a stable order so two checkouts cannot oversell the same stock.
    products = db.scalars(
        select(Product).where(Product.id.in_(wanted)).order_by(Product.id).with_for_update()
    ).all()
    by_id = {p.id: p for p in products}

    for product_id, quantity in wanted.items():
        product = by_id.get(product_id)
        if product is None or product.status != ProductStatus.APPROVED:
            raise HTTPException(status_code=400, detail=f"Product {product_id} is not available")
        if product.stock < quantity:
            raise HTTPException(status_code=400, detail=f"Only {product.stock} left for '{product.name}'")

        total += product.price * quantity
        product.stock -= quantity
        order.items.append(
            OrderItem(
                product_id=product.id,
                seller_id=product.seller_id,
                product_name=product.name,
                price=product.price,
                quantity=quantity,
            )
        )

    order.total_amount = total
    db.add(order)
    db.flush()  # gives the order its id for the notifications below

    for seller_id in {i.seller_id for i in order.items}:
        count = sum(1 for i in order.items if i.seller_id == seller_id)
        notify(
            db,
            seller_id,
            NotificationType.ORDER,
            "New order received",
            f"Order #{order.id} · {count} item(s)",
        )
    for product in products:
        if product.stock <= product.low_stock_threshold:
            notify(
                db,
                product.seller_id,
                NotificationType.STOCK,
                "Low stock alert",
                f"{product.name} · {product.stock} units left",
            )

    db.commit()
    db.refresh(order)
    return order


def restock_if_cancelled(db: Session, item: OrderItem, new_status: OrderItemStatus) -> None:
    """Cancelling an item puts its quantity back into stock."""
    if new_status == OrderItemStatus.CANCELLED and item.status != OrderItemStatus.CANCELLED:
        product = db.get(Product, item.product_id) if item.product_id else None
        if product:
            product.stock += item.quantity


def set_item_status(db: Session, item: OrderItem, new_status: OrderItemStatus) -> OrderItem:
    restock_if_cancelled(db, item, new_status)
    item.status = new_status

    # Cash on delivery counts as paid once every non-cancelled item has been delivered.
    order = item.order
    live = [i for i in order.items if i.status != OrderItemStatus.CANCELLED]
    if order.payment_method == "COD" and live and all(i.status == OrderItemStatus.DELIVERED for i in live):
        order.payment_status = PaymentStatus.PAID

    notify(
        db,
        order.user_id,
        NotificationType.ORDER,
        "Order update",
        f"{item.product_name} is now {new_status.value}",
    )
    db.commit()
    db.refresh(item)
    return item


def order_status(order: Order) -> str:
    """One status for the whole order, derived from its items (used by the admin Orders page)."""
    statuses = [i.status for i in order.items]
    if statuses and all(s == OrderItemStatus.CANCELLED for s in statuses):
        return "cancelled"
    live = [s for s in statuses if s != OrderItemStatus.CANCELLED]
    if live and all(s == OrderItemStatus.DELIVERED for s in live):
        return "delivered"
    if any(s != OrderItemStatus.PLACED for s in live):
        return "processing"
    return "pending"


def seller_row(item: OrderItem) -> dict:
    order = item.order
    return {
        "item_id": item.id,
        "order_id": item.order_id,
        "product_id": item.product_id,
        "product_name": item.product_name,
        "price": item.price,
        "quantity": item.quantity,
        "status": item.status,
        "payment_method": order.payment_method,
        "payment_status": order.payment_status,
        "customer_name": order.full_name,
        "city": order.city,
        "created_at": order.created_at,
    }
