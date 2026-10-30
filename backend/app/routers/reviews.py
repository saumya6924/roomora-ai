"""Reviews. A customer can only review something they actually received (delivered) or used (completed)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import BookingStatus, NotificationType, OrderItemStatus, ProductStatus, Role
from app.core.security import get_current_user, require_role
from app.db.session import get_db
from app.models import Booking, DesignerProfile, Order, OrderItem, Product, Review, User
from app.schemas.common import ORMModel
from app.services.notifications import notify
from app.services.reviews import summarize

router = APIRouter(tags=["Reviews"])


class ReviewCreate(BaseModel):
    product_id: int | None = None
    designer_id: int | None = None
    rating: int = Field(ge=1, le=5)
    title: str = Field(default="", max_length=120)
    body: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def exactly_one_target(self):
        if (self.product_id is None) == (self.designer_id is None):
            raise ValueError("Review either a product or a designer")
        return self


class ReviewOut(ORMModel):
    id: int
    rating: int
    title: str
    body: str
    created_at: datetime
    customer_name: str
    subject: str


def review_out(review: Review, subject: str) -> dict:
    return {
        "id": review.id,
        "rating": review.rating,
        "title": review.title,
        "body": review.body,
        "created_at": review.created_at,
        "customer_name": review.user.name,
        "subject": subject,
    }


def subject_of(review: Review, db: Session) -> str:
    if review.product_id:
        product = db.get(Product, review.product_id)
        return product.name if product else "Product"
    designer = db.get(DesignerProfile, review.designer_id)
    return f"Designer · {designer.user.name}" if designer else "Designer"


@router.post("/reviews", response_model=ReviewOut, status_code=201)
def create_review(data: ReviewCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.product_id is not None:
        product = db.get(Product, data.product_id)
        if product is None or product.status != ProductStatus.APPROVED:
            raise HTTPException(status_code=404, detail="Product not found")
        received = (
            db.query(OrderItem.id)
            .join(Order, Order.id == OrderItem.order_id)
            .filter(
                Order.user_id == user.id,
                OrderItem.product_id == product.id,
                OrderItem.status == OrderItemStatus.DELIVERED,
            )
            .first()
        )
        if not received:
            raise HTTPException(
                status_code=403, detail="You can review a product once it has been delivered to you"
            )
        target_user, label = product.seller_id, product.name
    else:
        designer = db.get(DesignerProfile, data.designer_id)
        if designer is None:
            raise HTTPException(status_code=404, detail="Designer not found")
        done = (
            db.query(Booking.id)
            .filter(
                Booking.user_id == user.id,
                Booking.designer_id == designer.id,
                Booking.status == BookingStatus.COMPLETED,
            )
            .first()
        )
        if not done:
            raise HTTPException(status_code=403, detail="You can review a designer after a completed booking")
        target_user, label = designer.user_id, f"your design work ({designer.user.name})"

    review = Review(user_id=user.id, **data.model_dump())
    db.add(review)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="You have already reviewed this") from None
    notify(
        db,
        target_user,
        NotificationType.REVIEW,
        f"New {data.rating}-star review",
        f"{user.name} reviewed {label}.",
    )
    db.commit()
    db.refresh(review)
    return review_out(review, subject_of(review, db))


@router.get("/products/{product_id}/reviews", response_model=list[ReviewOut])
def product_reviews(product_id: int, db: Session = Depends(get_db)):
    reviews = db.query(Review).filter(Review.product_id == product_id).order_by(Review.id.desc()).all()
    return [review_out(r, subject_of(r, db)) for r in reviews]


@router.get("/designers/{designer_id}/reviews", response_model=list[ReviewOut])
def designer_reviews(designer_id: int, db: Session = Depends(get_db)):
    reviews = db.query(Review).filter(Review.designer_id == designer_id).order_by(Review.id.desc()).all()
    return [review_out(r, subject_of(r, db)) for r in reviews]


@router.get("/reviews/mine")
def reviews_i_wrote(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """So the order and booking history can show which items are already reviewed."""
    rows = db.query(Review).filter(Review.user_id == user.id).all()
    return [{"product_id": r.product_id, "designer_id": r.designer_id, "rating": r.rating} for r in rows]


@router.get("/reviews/received")
def reviews_i_received(
    user: User = Depends(require_role(Role.SELLER, Role.DESIGNER)), db: Session = Depends(get_db)
):
    query = db.query(Review)
    if user.role == Role.SELLER:
        query = query.join(Product, Product.id == Review.product_id).filter(Product.seller_id == user.id)
    else:
        profile = db.query(DesignerProfile).filter_by(user_id=user.id).first()
        query = query.filter(Review.designer_id == (profile.id if profile else -1))
    reviews = query.order_by(Review.id.desc()).all()
    return {
        **summarize(r.rating for r in reviews),
        "reviews": [review_out(r, subject_of(r, db)) for r in reviews],
    }
