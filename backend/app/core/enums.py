"""Every status and role value lives here, so no route compares against a bare string."""

from enum import StrEnum


class Role(StrEnum):
    USER = "user"
    SELLER = "seller"
    DESIGNER = "designer"
    ADMIN = "admin"


class ProductStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class DesignerStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    SUSPENDED = "suspended"


class SellerStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class BookingStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    COMPLETED = "completed"


class OrderItemStatus(StrEnum):
    PLACED = "placed"
    PACKED = "packed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"


class PayoutStatus(StrEnum):
    REQUESTED = "requested"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"


class ImageKind(StrEnum):
    ORIGINAL = "original"
    GENERATED = "generated"


class ServiceUnit(StrEnum):
    DAY = "day"
    SESSION = "session"


class NotificationType(StrEnum):
    ORDER = "order"
    BOOKING = "booking"
    REVIEW = "review"
    PRODUCT = "product"
    STOCK = "stock"
    PAYOUT = "payout"
    SYSTEM = "system"


PAYMENT_METHODS = ("COD", "UPI", "Card", "Net Banking")
SPACE_TYPES = ("Home", "Cafe", "Hotel", "Office", "College", "Restaurant", "Shop")
