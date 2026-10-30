"""Import every model so Base.metadata (and Alembic) sees all tables."""

from app.models.catalog import DesignerService, PortfolioItem, Product, ProductImage
from app.models.commerce import Booking, Order, OrderItem
from app.models.engagement import (
    DesignImage,
    Notification,
    Payout,
    PlatformSetting,
    Review,
    SavedDesign,
)
from app.models.user import DesignerProfile, SellerProfile, User

__all__ = [
    "Booking",
    "DesignImage",
    "DesignerProfile",
    "DesignerService",
    "Notification",
    "Order",
    "OrderItem",
    "Payout",
    "PlatformSetting",
    "PortfolioItem",
    "Product",
    "ProductImage",
    "Review",
    "SavedDesign",
    "SellerProfile",
    "User",
]
