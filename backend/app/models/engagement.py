from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ImageKind, NotificationType, PayoutStatus
from app.db.base import PK, Base, Money, created_at_col, enum_type, updated_at_col
from app.models.user import User


class Review(Base):
    """A rating for either a product or a designer (exactly one of the two)."""

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),
        CheckConstraint(
            "(product_id IS NOT NULL AND designer_id IS NULL)"
            " OR (product_id IS NULL AND designer_id IS NOT NULL)",
            name="one_target",
        ),
        UniqueConstraint("user_id", "product_id", name="user_product"),
        UniqueConstraint("user_id", "designer_id", name="user_designer"),
    )

    id: Mapped[int] = mapped_column(PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    designer_id: Mapped[int | None] = mapped_column(
        ForeignKey("designer_profiles.id", ondelete="CASCADE"), index=True
    )
    rating: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(120), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = created_at_col()

    user: Mapped[User] = relationship()


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[NotificationType] = mapped_column(
        enum_type(NotificationType, "notification_type"), default=NotificationType.SYSTEM
    )
    title: Mapped[str] = mapped_column(String(150))
    body: Mapped[str] = mapped_column(String(400), default="")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = created_at_col()


class Payout(Base):
    """A mock settlement request by a seller or designer. No money moves."""

    __tablename__ = "payouts"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    id: Mapped[int] = mapped_column(PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Money)
    status: Mapped[PayoutStatus] = mapped_column(
        enum_type(PayoutStatus, "payout_status"), default=PayoutStatus.REQUESTED, index=True
    )
    reference: Mapped[str] = mapped_column(String(40), default="")
    requested_at: Mapped[datetime] = created_at_col()
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship()


class DesignImage(Base):
    """Room photos and AI results. Every edit is a new row pointing at its parent (version chain)."""

    __tablename__ = "design_images"

    id: Mapped[int] = mapped_column(PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("design_images.id", ondelete="SET NULL"))
    kind: Mapped[ImageKind] = mapped_column(enum_type(ImageKind, "image_kind"))
    storage_path: Mapped[str] = mapped_column(String(300))
    prompt: Mapped[str] = mapped_column(Text, default="")
    provider: Mapped[str] = mapped_column(String(30), default="")
    created_at: Mapped[datetime] = created_at_col()


class SavedDesign(Base):
    """The 'Save Design' button on the AI result."""

    __tablename__ = "saved_designs"

    id: Mapped[int] = mapped_column(PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(150), default="My design")
    prompt: Mapped[str] = mapped_column(Text, default="")
    space_type: Mapped[str] = mapped_column(String(30), default="Home")
    requirements: Mapped[dict] = mapped_column(JSON, default=dict)
    image_url: Mapped[str] = mapped_column(String(500), default="")
    design_image_id: Mapped[int | None] = mapped_column(
        ForeignKey("design_images.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = created_at_col()


class PlatformSetting(Base):
    """Admin-controlled switches, e.g. allow_registration."""

    __tablename__ = "platform_settings"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = updated_at_col()
