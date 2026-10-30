from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import DesignerStatus, Role, SellerStatus
from app.db.base import PK, Base, Money, created_at_col, enum_type, updated_at_col


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(PK, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    mobile: Mapped[str] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[Role] = mapped_column(enum_type(Role, "user_role"), default=Role.USER, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    location: Mapped[str] = mapped_column(String(120), default="")
    notification_prefs: Mapped[dict] = mapped_column(JSON, default=dict)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()


class SellerProfile(Base):
    """Store details for a user whose role is 'seller'."""

    __tablename__ = "seller_profiles"

    id: Mapped[int] = mapped_column(PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    store_name: Mapped[str] = mapped_column(String(120), default="")
    business_email: Mapped[str] = mapped_column(String(150), default="")
    gst_number: Mapped[str] = mapped_column(String(20), default="")
    bank_holder: Mapped[str] = mapped_column(String(100), default="")
    bank_account_masked: Mapped[str] = mapped_column(String(40), default="")
    ifsc: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[SellerStatus] = mapped_column(
        enum_type(SellerStatus, "seller_status"), default=SellerStatus.ACTIVE
    )
    created_at: Mapped[datetime] = created_at_col()

    user: Mapped[User] = relationship()


class DesignerProfile(Base):
    """Public profile and settings for a user whose role is 'designer'."""

    __tablename__ = "designer_profiles"

    id: Mapped[int] = mapped_column(PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    title: Mapped[str] = mapped_column(String(120), default="Interior Designer")
    speciality: Mapped[str] = mapped_column(String(255), default="")
    experience: Mapped[str] = mapped_column(String(40), default="")
    location: Mapped[str] = mapped_column(String(120), default="")
    about: Mapped[str] = mapped_column(Text, default="")
    contract_terms: Mapped[str] = mapped_column(Text, default="")
    price_per_day: Mapped[Decimal] = mapped_column(Money, default=0)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[DesignerStatus] = mapped_column(
        enum_type(DesignerStatus, "designer_status"), default=DesignerStatus.PENDING, index=True
    )
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    bank_holder: Mapped[str] = mapped_column(String(100), default="")
    bank_account_masked: Mapped[str] = mapped_column(String(40), default="")
    ifsc: Mapped[str] = mapped_column(String(20), default="")
    created_at: Mapped[datetime] = created_at_col()

    user: Mapped[User] = relationship()
    services: Mapped[list["DesignerService"]] = relationship(  # noqa: F821
        back_populates="designer", cascade="all, delete-orphan"
    )
    portfolio: Mapped[list["PortfolioItem"]] = relationship(  # noqa: F821
        back_populates="designer", cascade="all, delete-orphan"
    )
