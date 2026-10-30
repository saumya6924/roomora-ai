from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, create_model

from app.core.enums import DesignerStatus, ProductStatus
from app.schemas.common import Money, ORMModel


class ProductCreate(BaseModel):
    """Everything on the seller's Add Product form."""

    model_config = ConfigDict(validate_default=True)  # so numeric defaults become Decimal like input values

    # basic information
    name: str = Field(min_length=2, max_length=150)
    category: str = Field(default="Furniture", max_length=60)
    product_type: str = Field(default="New", max_length=30)
    short_description: str = Field(default="", max_length=255)
    description: str = ""
    image_urls: list[str] = Field(default_factory=list, max_length=5)

    # pricing and tax
    price: Money = Field(gt=0)
    mrp: Money | None = Field(default=None, gt=0)
    gst_percent: Money = Field(default=12, ge=0, le=100)
    discount_percent: Money = Field(default=0, ge=0, le=90)

    # dimensions and weight
    length_cm: Money | None = Field(default=None, ge=0)
    width_cm: Money | None = Field(default=None, ge=0)
    height_cm: Money | None = Field(default=None, ge=0)
    weight_kg: Money | None = Field(default=None, ge=0)

    # material and features
    material: str = Field(default="", max_length=60)
    color: str = Field(default="", max_length=60)
    finish: str = Field(default="", max_length=60)
    seating_capacity: str = Field(default="", max_length=30)
    key_features: str = ""

    # inventory
    sku: str | None = Field(default=None, max_length=60)
    stock: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=5, ge=0)
    warehouse: str = Field(default="", max_length=120)

    # shipping and delivery
    delivery_time: str = Field(default="", max_length=40)
    shipping_charge: Money = Field(default=0, ge=0)
    assembly: str = Field(default="", max_length=30)
    installation_charge: Money = Field(default=0, ge=0)
    delivery_areas: str = Field(default="", max_length=255)

    # returns and warranty
    return_period: str = Field(default="", max_length=30)
    warranty: str = Field(default="", max_length=30)
    return_policy: str = ""


def _optional(field):
    """The same field, but optional, with its constraints (gt, max_length, ...) kept."""
    annotation = Annotated[(field.annotation, *field.metadata)] if field.metadata else field.annotation
    return (annotation | None, None)


# Every ProductCreate field made optional: send only what you want to change.
ProductUpdate = create_model(
    "ProductUpdate",
    __base__=BaseModel,
    **{name: _optional(field) for name, field in ProductCreate.model_fields.items()},
)


class ProductImageOut(ORMModel):
    url: str
    position: int


class ProductOut(ORMModel):
    id: int
    seller_id: int
    status: ProductStatus
    name: str
    category: str
    product_type: str
    short_description: str
    description: str
    image_url: str
    images: list[ProductImageOut]
    price: Money
    mrp: Money | None
    gst_percent: Money
    discount_percent: Money
    length_cm: Money | None
    width_cm: Money | None
    height_cm: Money | None
    weight_kg: Money | None
    material: str
    color: str
    finish: str
    seating_capacity: str
    key_features: str
    sku: str | None
    stock: int
    low_stock_threshold: int
    warehouse: str
    delivery_time: str
    shipping_charge: Money
    assembly: str
    installation_charge: Money
    delivery_areas: str
    return_period: str
    warranty: str
    return_policy: str


class DesignerOut(BaseModel):
    id: int
    user_id: int
    name: str
    title: str
    speciality: str
    location: str
    price_per_day: Money
    is_available: bool
    status: DesignerStatus


class DesignerProfileCreate(BaseModel):
    user_id: int
    speciality: str = ""
    price_per_day: Money = Field(gt=0)
