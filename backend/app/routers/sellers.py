"""Everything the seller panel needs beyond product CRUD and orders."""

from collections import defaultdict

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.core.enums import OrderItemStatus, ProductStatus, Role
from app.core.security import require_role
from app.db.session import get_db
from app.models import Notification, OrderItem, Product, Review, SellerProfile, User
from app.services import earnings as earnings_service
from app.services.export import csv_response
from app.services.reviews import summarize
from app.services.stats import as_utc, growth, last_months, month_key, monthly_series, this_and_last_month

router = APIRouter(prefix="/sellers/me", tags=["Seller Panel"])

seller_only = require_role(Role.SELLER)


def get_profile(db: Session, user: User) -> SellerProfile:
    profile = db.query(SellerProfile).filter_by(user_id=user.id).first()
    if profile is None:
        profile = SellerProfile(user_id=user.id, store_name=user.name)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def profile_out(profile: SellerProfile, user: User) -> dict:
    return {
        "store_name": profile.store_name,
        "business_email": profile.business_email,
        "mobile": user.mobile,
        "gst_number": profile.gst_number,
        "bank_holder": profile.bank_holder,
        "bank_account_masked": profile.bank_account_masked,
        "ifsc": profile.ifsc,
        "status": profile.status,
        "owner_name": user.name,
        "email": user.email,
        "notification_prefs": user.notification_prefs or {},
    }


class SellerProfileUpdate(BaseModel):
    store_name: str | None = Field(default=None, min_length=2, max_length=120)
    business_email: str | None = Field(default=None, max_length=150)
    mobile: str | None = Field(default=None, min_length=10, max_length=20)
    gst_number: str | None = Field(default=None, max_length=20)
    bank_holder: str | None = Field(default=None, max_length=100)
    bank_account_masked: str | None = Field(default=None, max_length=40)
    ifsc: str | None = Field(default=None, max_length=20)


@router.get("")
def my_store(user: User = Depends(seller_only), db: Session = Depends(get_db)):
    return profile_out(get_profile(db, user), user)


@router.put("")
def update_store(data: SellerProfileUpdate, user: User = Depends(seller_only), db: Session = Depends(get_db)):
    profile = get_profile(db, user)
    for field, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(user if field == "mobile" else profile, field, value)
    db.commit()
    return profile_out(profile, user)


def _items(db: Session, user: User) -> list[OrderItem]:
    return (
        db.query(OrderItem)
        .options(joinedload(OrderItem.order), joinedload(OrderItem.product))
        .filter(OrderItem.seller_id == user.id)
        .all()
    )


def _value(item: OrderItem) -> float:
    return float(item.price * item.quantity)


@router.get("/dashboard")
def dashboard(user: User = Depends(seller_only), db: Session = Depends(get_db)):
    items = _items(db, user)
    live = [i for i in items if i.status != OrderItemStatus.CANCELLED]
    products = db.query(Product).filter(Product.seller_id == user.id).all()

    revenue_now, revenue_before = this_and_last_month((i.order.created_at, _value(i)) for i in live)
    order_dates = {i.order_id: i.order.created_at for i in items}
    orders_now, orders_before = this_and_last_month((d, 1) for d in order_dates.values())

    reviews = (
        db.query(Review.rating)
        .join(Product, Product.id == Review.product_id)
        .filter(Product.seller_id == user.id)
        .all()
    )
    review_stats = summarize(r[0] for r in reviews)
    delivered = sum(1 for i in live if i.status == OrderItemStatus.DELIVERED)

    sold: dict[int, dict] = {}
    for item in live:
        row = sold.setdefault(
            item.product_id,
            {
                "name": item.product_name,
                "price": float(item.price),
                "sold": 0,
                "category": item.product.category if item.product else "",
            },
        )
        row["sold"] += item.quantity

    recent = sorted(items, key=lambda i: i.id, reverse=True)[:3]
    activity = (
        db.query(Notification).filter_by(user_id=user.id).order_by(Notification.id.desc()).limit(3).all()
    )
    return {
        "store_name": get_profile(db, user).store_name,
        "total_products": len(products),
        "products_this_month": sum(1 for p in products if month_key(p.created_at) == last_months(1)[0]),
        "total_orders": len(order_dates),
        "orders_growth": growth(orders_now, orders_before),
        "month_revenue": revenue_now,
        "revenue_growth": growth(revenue_now, revenue_before),
        "average_rating": review_stats["average"],
        "review_count": review_stats["count"],
        "pending_orders": sum(1 for i in items if i.status == OrderItemStatus.PLACED),
        "low_stock": sum(1 for p in products if p.stock <= p.low_stock_threshold),
        "pending_approval": sum(1 for p in products if p.status == ProductStatus.PENDING),
        "available_balance": float(earnings_service.balance(db, user)["available"]),
        "recent_orders": [
            {
                "order_id": i.order_id,
                "customer": i.order.full_name,
                "product": i.product_name,
                "amount": _value(i),
                "status": i.status,
            }
            for i in recent
        ],
        "top_products": sorted(sold.values(), key=lambda r: r["sold"], reverse=True)[:3],
        "activity": [
            {"title": n.title, "body": n.body, "type": n.type, "created_at": n.created_at} for n in activity
        ],
        "health": {
            "product_quality": round(100 * sum(1 for r in reviews if r[0] >= 4) / len(reviews))
            if reviews
            else 0,
            "order_fulfillment": round(100 * delivered / len(live)) if live else 0,
            "customer_satisfaction": round(review_stats["average"] * 20),
        },
    }


@router.get("/customers")
def customers(user: User = Depends(seller_only), db: Session = Depends(get_db)):
    people: dict[int, dict] = defaultdict(lambda: {"orders": set(), "spent": 0.0, "last": None})
    for item in _items(db, user):
        if item.status == OrderItemStatus.CANCELLED:
            continue
        row = people[item.order.user_id]
        row["orders"].add(item.order_id)
        row["spent"] += _value(item)
        created = as_utc(item.order.created_at)
        row["last"] = created if row["last"] is None or created > row["last"] else row["last"]
    result = []
    for user_id, row in people.items():
        customer = db.get(User, user_id)
        result.append(
            {
                "name": customer.name,
                "email": customer.email,
                "orders": len(row["orders"]),
                "total_spent": round(row["spent"], 2),
                "last_order": row["last"],
            }
        )
    return sorted(result, key=lambda r: r["total_spent"], reverse=True)


@router.get("/analytics")
def analytics(user: User = Depends(seller_only), db: Session = Depends(get_db)):
    live = [i for i in _items(db, user) if i.status != OrderItemStatus.CANCELLED]
    by_category: dict[str, float] = defaultdict(float)
    for item in live:
        by_category[(item.product.category if item.product else "Other") or "Other"] += _value(item)
    top = sorted(by_category.items(), key=lambda kv: kv[1], reverse=True)[:4]
    best = top[0][1] if top else 0
    return {
        "monthly_sales": monthly_series((i.order.created_at, _value(i)) for i in live),
        "categories": [
            {
                "category": name,
                "revenue": round(value, 2),
                "percent": round(100 * value / best) if best else 0,
            }
            for name, value in top
        ],
    }


@router.get("/export/orders.csv")
def export_orders(user: User = Depends(seller_only), db: Session = Depends(get_db)) -> Response:
    rows = [
        [
            i.order_id,
            as_utc(i.order.created_at).date().isoformat(),
            i.order.full_name,
            i.order.city,
            i.product_name,
            i.quantity,
            float(i.price),
            _value(i),
            i.status.value,
            i.order.payment_method,
            i.order.payment_status.value,
        ]
        for i in sorted(_items(db, user), key=lambda i: i.id)
    ]
    return csv_response(
        "orders.csv",
        [
            "Order",
            "Date",
            "Customer",
            "City",
            "Product",
            "Qty",
            "Unit price",
            "Total",
            "Status",
            "Payment",
            "Payment status",
        ],
        rows,
    )
