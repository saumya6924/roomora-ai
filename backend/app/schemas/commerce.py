from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field

from app.core.enums import BookingStatus, OrderItemStatus, PaymentStatus
from app.schemas.common import Money, ORMModel


# ---------------------------------------------------------------- bookings
class BookingCreate(BaseModel):
    designer_id: int
    name: str = Field(min_length=2)
    mobile: str = Field(min_length=10)
    email: EmailStr
    project_type: str = "Home"
    location: str = ""
    start_date: date
    days: int = Field(default=1, ge=1, le=60)
    details: str = ""


class BookingOut(ORMModel):
    id: int
    designer_id: int
    designer_name: str
    name: str
    mobile: str
    email: str
    project_type: str
    location: str
    start_date: date
    days: int
    details: str
    total_amount: Money
    status: BookingStatus
    created_at: datetime


# ---------------------------------------------------------------- orders
class CartItem(BaseModel):
    # No price here on purpose: the server reads the real price from the database.
    product_id: int
    quantity: int = Field(ge=1, le=20)


class OrderCreate(BaseModel):
    items: list[CartItem] = Field(min_length=1)
    full_name: str = Field(min_length=2)
    mobile: str = Field(min_length=10)
    address: str = Field(min_length=3)
    city: str = Field(min_length=2)
    state: str = ""
    pincode: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    payment_method: str = "COD"


class OrderItemOut(ORMModel):
    id: int
    product_id: int | None
    product_name: str
    price: Money
    quantity: int
    status: OrderItemStatus


class OrderOut(ORMModel):
    id: int
    total_amount: Money
    payment_method: str
    payment_status: PaymentStatus
    full_name: str
    address: str
    city: str
    state: str
    pincode: str
    created_at: datetime
    items: list[OrderItemOut]


class SellerOrderRow(BaseModel):
    """One line on the seller's Orders page: who bought my product."""

    item_id: int
    order_id: int
    product_id: int | None
    product_name: str
    price: Money
    quantity: int
    status: OrderItemStatus
    payment_method: str
    payment_status: PaymentStatus
    customer_name: str
    city: str
    created_at: datetime
