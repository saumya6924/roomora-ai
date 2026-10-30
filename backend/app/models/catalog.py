from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ProductStatus, ServiceUnit
from app.db.base import PK, Base, Money, created_at_col, enum_type, updated_at_col
from app.models.user import DesignerProfile, User


class Product(Base):
    """A furniture item sold by a seller. Columns mirror the seller's Add Product form."""

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("seller_id", "sku", name="seller_sku"),
        CheckConstraint("price > 0", name="price_positive"),
        CheckConstraint("stock >= 0", name="stock_not_negative"),
    )

    id: Mapped[int] = mapped_column(PK, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[ProductStatus] = mapped_column(
        enum_type(ProductStatus, "product_status"), default=ProductStatus.PENDING, index=True
    )

    # basic information
    name: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(60), default="Furniture", index=True)
    product_type: Mapped[str] = mapped_column(String(30), default="New")
    short_description: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    image_url: Mapped[str] = mapped_column(String(500), default="")  # cover image

    # pricing and tax
    price: Mapped[Decimal] = mapped_column(Money)
    mrp: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    gst_percent: Mapped[Decimal] = mapped_column(Money, default=12)
    discount_percent: Mapped[Decimal] = mapped_column(Money, default=0)

    # dimensions and weight
    length_cm: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    width_cm: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    height_cm: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(Money, nullable=True)

    # material and features
    material: Mapped[str] = mapped_column(String(60), default="")
    color: Mapped[str] = mapped_column(String(60), default="")
    finish: Mapped[str] = mapped_column(String(60), default="")
    seating_capacity: Mapped[str] = mapped_column(String(30), default="")
    key_features: Mapped[str] = mapped_column(Text, default="")

    # inventory
    sku: Mapped[str | None] = mapped_column(String(60), nullable=True)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=5)
    warehouse: Mapped[str] = mapped_column(String(120), default="")

    # shipping and delivery
    delivery_time: Mapped[str] = mapped_column(String(40), default="")
    shipping_charge: Mapped[Decimal] = mapped_column(Money, default=0)
    assembly: Mapped[str] = mapped_column(String(30), default="")
    installation_charge: Mapped[Decimal] = mapped_column(Money, default=0)
    delivery_areas: Mapped[str] = mapped_column(String(255), default="")

    # returns and warranty
    return_period: Mapped[str] = mapped_column(String(30), default="")
    warranty: Mapped[str] = mapped_column(String(30), default="")
    return_policy: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()

    seller: Mapped[User] = relationship()
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.position"
    )


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(PK, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped[Product] = relationship(back_populates="images")


class DesignerService(Base):
    """A priced service a designer offers (shown on the Services page)."""

    __tablename__ = "designer_services"

    id: Mapped[int] = mapped_column(PK, primary_key=True)
    designer_id: Mapped[int] = mapped_column(
        ForeignKey("designer_profiles.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(40), default="")
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[Decimal] = mapped_column(Money)
    unit: Mapped[ServiceUnit] = mapped_column(enum_type(ServiceUnit, "service_unit"), default=ServiceUnit.DAY)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    designer: Mapped[DesignerProfile] = relationship(back_populates="services")


class PortfolioItem(Base):
    __tablename__ = "portfolio_items"

    id: Mapped[int] = mapped_column(PK, primary_key=True)
    designer_id: Mapped[int] = mapped_column(
        ForeignKey("designer_profiles.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(40), default="")
    location: Mapped[str] = mapped_column(String(120), default="")
    area_sqft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_url: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = created_at_col()

    designer: Mapped[DesignerProfile] = relationship(back_populates="portfolio")
