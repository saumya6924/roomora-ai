from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import BookingStatus, OrderItemStatus, PaymentStatus
from app.db.base import PK, Base, Money, created_at_col, enum_type, updated_at_col
from app.models.catalog import Product
from app.models.user import DesignerProfile, User


class Order(Base):
    """One checkout by a customer."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    total_amount: Mapped[Decimal] = mapped_column(Money, default=0)
    payment_method: Mapped[str] = mapped_column(String(30), default="COD")
    payment_status: Mapped[PaymentStatus] = mapped_column(
        enum_type(PaymentStatus, "payment_status"), default=PaymentStatus.PENDING
    )
    full_name: Mapped[str] = mapped_column(String(100))
    mobile: Mapped[str] = mapped_column(String(20))
    address: Mapped[str] = mapped_column(String(300))
    city: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(80), default="")
    pincode: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = created_at_col()

    user: Mapped[User] = relationship()
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    """One product line of an order. Status is per item because each item can have a different seller."""

    __tablename__ = "order_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="quantity_positive"),)

    id: Mapped[int] = mapped_column(PK, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    product_name: Mapped[str] = mapped_column(
        String(150)
    )  # copied: old orders stay correct if a product changes
    price: Mapped[Decimal] = mapped_column(Money)  # price at the time of buying
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[OrderItemStatus] = mapped_column(
        enum_type(OrderItemStatus, "order_item_status"), default=OrderItemStatus.PLACED, index=True
    )
    updated_at: Mapped[datetime] = updated_at_col()

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product | None] = relationship()


class Booking(Base):
    """A customer booking a designer."""

    __tablename__ = "bookings"
    __table_args__ = (CheckConstraint("days >= 1", name="days_positive"),)

    id: Mapped[int] = mapped_column(PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    designer_id: Mapped[int] = mapped_column(ForeignKey("designer_profiles.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    mobile: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(150))
    project_type: Mapped[str] = mapped_column(String(30), default="Home")
    location: Mapped[str] = mapped_column(String(120), default="")
    start_date: Mapped[date] = mapped_column(Date)
    days: Mapped[int] = mapped_column(Integer, default=1)
    details: Mapped[str] = mapped_column(Text, default="")
    total_amount: Mapped[Decimal] = mapped_column(Money, default=0)
    status: Mapped[BookingStatus] = mapped_column(
        enum_type(BookingStatus, "booking_status"), default=BookingStatus.PENDING, index=True
    )
    created_at: Mapped[datetime] = created_at_col()
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship()
    designer: Mapped[DesignerProfile] = relationship()
