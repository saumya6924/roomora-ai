"""Furniture: the public catalogue, seller CRUD, and admin approval.

Route order matters: fixed paths such as /mine must be declared BEFORE /{product_id},
or FastAPI would try to read "mine" as a product id.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import NotificationType, ProductStatus, Role
from app.core.security import require_role
from app.db.session import get_db
from app.models import OrderItem, Product, ProductImage, User
from app.routers._common import parse_enum
from app.schemas.catalog import ProductCreate, ProductOut, ProductUpdate
from app.schemas.common import Message, StatusUpdate
from app.services.notifications import notify
from app.services.platform import require_enabled

router = APIRouter(prefix="/products", tags=["Furniture / Products"])

seller_or_admin = require_role(Role.SELLER, Role.ADMIN)
admin_only = require_role(Role.ADMIN)


def _set_images(product: Product, urls: list[str]) -> None:
    product.images = [ProductImage(url=url, position=i) for i, url in enumerate(urls)]
    product.image_url = urls[0] if urls else product.image_url


def _get_own_product(product_id: int, user: User, db: Session) -> Product:
    """Find a product and make sure this user may touch it."""
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if user.role != Role.ADMIN and product.seller_id != user.id:
        raise HTTPException(status_code=403, detail="This is not your product")
    return product


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="That SKU is already used by another of your products"
        ) from None


@router.get("", response_model=list[ProductOut])
def list_products(
    search: str | None = None,
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    skip: int = 0,
    limit: int = Query(default=50, le=100),
    db: Session = Depends(get_db),
):
    """Customers only ever see approved products."""
    query = db.query(Product).filter(Product.status == ProductStatus.APPROVED)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    if category:
        query = query.filter(Product.category == category)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    return query.order_by(Product.id).offset(skip).limit(limit).all()


@router.get("/mine", response_model=list[ProductOut])
def my_products(seller: User = Depends(seller_or_admin), db: Session = Depends(get_db)):
    return db.query(Product).filter(Product.seller_id == seller.id).order_by(Product.id.desc()).all()


@router.get("/pending", response_model=list[ProductOut])
def pending_products(admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    return db.query(Product).filter(Product.status == ProductStatus.PENDING).all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None or product.status != ProductStatus.APPROVED:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("", response_model=ProductOut, status_code=201)
def add_product(
    data: ProductCreate,
    seller: User = Depends(seller_or_admin),
    db: Session = Depends(get_db),
):
    require_enabled(db, "marketplace_enabled", "The marketplace is temporarily closed")
    fields = data.model_dump()
    image_urls = fields.pop("image_urls")
    product = Product(**fields, seller_id=seller.id)
    # A seller's product needs admin approval first; an admin's own products go live at once.
    product.status = ProductStatus.APPROVED if seller.role == Role.ADMIN else ProductStatus.PENDING
    if image_urls:
        _set_images(product, image_urls)
    db.add(product)
    _commit(db)
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    data: ProductUpdate,
    user: User = Depends(seller_or_admin),
    db: Session = Depends(get_db),
):
    product = _get_own_product(product_id, user, db)
    changes = data.model_dump(exclude_unset=True)
    image_urls = changes.pop("image_urls", None)
    for field, value in changes.items():
        if value is None and field in {"name", "price", "stock"}:
            continue  # required columns cannot be cleared
        setattr(product, field, value)
    if image_urls is not None:
        _set_images(product, image_urls)
    _commit(db)
    db.refresh(product)
    return product


@router.delete("/{product_id}", response_model=Message)
def delete_product(
    product_id: int,
    user: User = Depends(seller_or_admin),
    db: Session = Depends(get_db),
):
    product = _get_own_product(product_id, user, db)
    # Old orders point at this product, so deleting it would break order history.
    if db.query(OrderItem).filter(OrderItem.product_id == product_id).first():
        raise HTTPException(status_code=400, detail="This product has orders. Set its stock to 0 instead.")
    db.delete(product)
    db.commit()
    return {"message": "Product deleted"}


class StockUpdate(BaseModel):
    stock: int = Field(ge=0)


@router.patch("/{product_id}/stock", response_model=ProductOut)
def set_stock(
    product_id: int,
    data: StockUpdate,
    user: User = Depends(seller_or_admin),
    db: Session = Depends(get_db),
):
    """The Restock button on the seller's Inventory page."""
    product = _get_own_product(product_id, user, db)
    product.stock = data.stock
    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}/status", response_model=ProductOut)
def set_product_status(
    product_id: int,
    data: StatusUpdate,
    admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    new_status = parse_enum(ProductStatus, data.status)
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    product.status = new_status
    notify(
        db,
        product.seller_id,
        NotificationType.PRODUCT,
        f"Product {new_status.value}",
        f"{product.name} is now {new_status.value}",
    )
    db.commit()
    db.refresh(product)
    return product
