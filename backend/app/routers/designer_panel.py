"""Everything the designer panel needs beyond bookings and the availability switch.

Registered BEFORE routers/designers.py so "/designers/me/..." is never read as "/designers/{id}".
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.enums import BookingStatus, Role, ServiceUnit
from app.core.security import require_role
from app.db.session import get_db
from app.models import Booking, DesignerProfile, DesignerService, PortfolioItem, Review, User
from app.schemas.common import Message, Money
from app.services.reviews import summarize
from app.services.stats import as_utc, growth, now_utc, this_and_last_month

router = APIRouter(prefix="/designers/me", tags=["Designer Panel"])

designer_only = require_role(Role.DESIGNER)


def my_profile(db: Session, user: User) -> DesignerProfile:
    profile = db.query(DesignerProfile).filter_by(user_id=user.id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Designer profile not found")
    return profile


def _bookings(db: Session, profile: DesignerProfile) -> list[Booking]:
    return db.query(Booking).filter(Booking.designer_id == profile.id).order_by(Booking.id.desc()).all()


def _rating(db: Session, profile: DesignerProfile) -> dict:
    return summarize(r[0] for r in db.query(Review.rating).filter(Review.designer_id == profile.id))


def profile_out(db: Session, profile: DesignerProfile) -> dict:
    bookings = _bookings(db, profile)
    answered = [b for b in bookings if b.responded_at]
    hours = [(as_utc(b.responded_at) - as_utc(b.created_at)).total_seconds() / 3600 for b in answered]
    rating = _rating(db, profile)
    user = profile.user
    return {
        "id": profile.id,
        "name": user.name,
        "email": user.email,
        "mobile": user.mobile,
        "title": profile.title,
        "speciality": profile.speciality,
        "experience": profile.experience,
        "location": profile.location,
        "about": profile.about,
        "contract_terms": profile.contract_terms,
        "price_per_day": profile.price_per_day,
        "is_available": profile.is_available,
        "is_visible": profile.is_visible,
        "status": profile.status,
        "bank_holder": profile.bank_holder,
        "bank_account_masked": profile.bank_account_masked,
        "ifsc": profile.ifsc,
        "verified_since": profile.created_at,
        "notification_prefs": user.notification_prefs or {},
        "projects_completed": sum(1 for b in bookings if b.status == BookingStatus.COMPLETED),
        "rating": rating["average"],
        "review_count": rating["count"],
        "response_rate": round(100 * len(answered) / len(bookings)) if bookings else None,
        "response_hours": round(sum(hours) / len(hours), 1) if hours else None,
    }


class DesignerProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    mobile: str | None = Field(default=None, min_length=10, max_length=20)
    title: str | None = Field(default=None, max_length=120)
    speciality: str | None = Field(default=None, max_length=255)
    experience: str | None = Field(default=None, max_length=40)
    location: str | None = Field(default=None, max_length=120)
    about: str | None = None
    contract_terms: str | None = None
    is_visible: bool | None = None
    bank_holder: str | None = Field(default=None, max_length=100)
    bank_account_masked: str | None = Field(default=None, max_length=40)
    ifsc: str | None = Field(default=None, max_length=20)


@router.get("")
def get_me(user: User = Depends(designer_only), db: Session = Depends(get_db)):
    return profile_out(db, my_profile(db, user))


@router.put("")
def update_me(
    data: DesignerProfileUpdate, user: User = Depends(designer_only), db: Session = Depends(get_db)
):
    profile = my_profile(db, user)
    for field, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(user if field in ("name", "mobile") else profile, field, value)
    db.commit()
    return profile_out(db, profile)


@router.get("/dashboard")
def dashboard(user: User = Depends(designer_only), db: Session = Depends(get_db)):
    profile = my_profile(db, user)
    bookings = _bookings(db, profile)
    today = now_utc().date()
    accepted = [b for b in bookings if b.status == BookingStatus.ACCEPTED]
    pending = [b for b in bookings if b.status == BookingStatus.PENDING]
    month_now, month_before = this_and_last_month(
        (b.completed_at, b.total_amount)
        for b in bookings
        if b.status == BookingStatus.COMPLETED and b.completed_at
    )
    rating = _rating(db, profile)
    recent_review = (
        db.query(Review).filter(Review.designer_id == profile.id).order_by(Review.id.desc()).first()
    )
    requests_30d = [b for b in bookings if as_utc(b.created_at) >= now_utc() - timedelta(days=30)]
    won = [b for b in bookings if b.status in (BookingStatus.ACCEPTED, BookingStatus.COMPLETED)]

    def span(b: Booking) -> dict:
        return {
            "id": b.id,
            "client": b.name,
            "project_type": b.project_type,
            "location": b.location,
            "start_date": b.start_date,
            "end_date": b.start_date + timedelta(days=b.days - 1),
            "days": b.days,
            "amount": b.total_amount,
        }

    return {
        "name": user.name,
        "is_available": profile.is_available,
        "pending_requests": len(pending),
        "active_projects": len(accepted),
        "starting_this_week": sum(1 for b in accepted if today <= b.start_date <= today + timedelta(days=7)),
        "month_earnings": month_now,
        "earnings_growth": growth(month_now, month_before),
        "rating": rating["average"],
        "review_count": rating["count"],
        "new_requests": [span(b) for b in pending[:3]],
        "upcoming": [span(b) for b in sorted(accepted, key=lambda b: b.start_date) if b.start_date >= today][
            :3
        ],
        "performance": {
            "profile_views": profile.view_count,
            "booking_requests": len(requests_30d),
            "conversion_rate": round(100 * len(won) / len(bookings)) if bookings else 0,
        },
        "recent_review": (
            {
                "customer": recent_review.user.name,
                "rating": recent_review.rating,
                "body": recent_review.body,
                "created_at": recent_review.created_at,
            }
            if recent_review
            else None
        ),
    }


# ---------------------------------------------------------------- services
class ServiceIn(BaseModel):
    category: str = Field(default="", max_length=40)
    name: str = Field(min_length=2, max_length=120)
    description: str = ""
    price: Money = Field(gt=0)
    unit: ServiceUnit = ServiceUnit.DAY
    is_active: bool = True


def service_out(s: DesignerService) -> dict:
    return {
        "id": s.id,
        "category": s.category,
        "name": s.name,
        "description": s.description,
        "price": s.price,
        "unit": s.unit,
        "is_active": s.is_active,
    }


def sync_price(db: Session, profile: DesignerProfile) -> None:
    """Bookings are priced per day, so the profile's day rate follows the cheapest active per-day service."""
    db.flush()
    db.refresh(profile)
    prices = [s.price for s in profile.services if s.is_active and s.unit == ServiceUnit.DAY]
    if prices:
        profile.price_per_day = min(prices)


def _own_service(db: Session, profile: DesignerProfile, service_id: int) -> DesignerService:
    service = db.get(DesignerService, service_id)
    if service is None or service.designer_id != profile.id:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


@router.get("/services")
def list_services(user: User = Depends(designer_only), db: Session = Depends(get_db)):
    profile = my_profile(db, user)
    return [service_out(s) for s in sorted(profile.services, key=lambda s: s.id)]


@router.post("/services", status_code=201)
def add_service(data: ServiceIn, user: User = Depends(designer_only), db: Session = Depends(get_db)):
    profile = my_profile(db, user)
    service = DesignerService(designer_id=profile.id, **data.model_dump())
    db.add(service)
    sync_price(db, profile)
    db.commit()
    return service_out(service)


@router.put("/services/{service_id}")
def update_service(
    service_id: int, data: ServiceIn, user: User = Depends(designer_only), db: Session = Depends(get_db)
):
    profile = my_profile(db, user)
    service = _own_service(db, profile, service_id)
    for field, value in data.model_dump().items():
        setattr(service, field, value)
    sync_price(db, profile)
    db.commit()
    return service_out(service)


@router.delete("/services/{service_id}", response_model=Message)
def delete_service(service_id: int, user: User = Depends(designer_only), db: Session = Depends(get_db)):
    profile = my_profile(db, user)
    db.delete(_own_service(db, profile, service_id))
    sync_price(db, profile)
    db.commit()
    return {"message": "Service deleted"}


# ---------------------------------------------------------------- portfolio
class PortfolioIn(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    category: str = Field(default="", max_length=40)
    location: str = Field(default="", max_length=120)
    area_sqft: int | None = Field(default=None, ge=0)
    image_url: str = Field(default="", max_length=500)


def portfolio_out(p: PortfolioItem) -> dict:
    return {
        "id": p.id,
        "title": p.title,
        "category": p.category,
        "location": p.location,
        "area_sqft": p.area_sqft,
        "image_url": p.image_url,
    }


@router.get("/portfolio")
def list_portfolio(user: User = Depends(designer_only), db: Session = Depends(get_db)):
    profile = my_profile(db, user)
    return [portfolio_out(p) for p in sorted(profile.portfolio, key=lambda p: p.id, reverse=True)]


@router.post("/portfolio", status_code=201)
def add_portfolio(data: PortfolioIn, user: User = Depends(designer_only), db: Session = Depends(get_db)):
    profile = my_profile(db, user)
    item = PortfolioItem(designer_id=profile.id, **data.model_dump())
    db.add(item)
    db.commit()
    return portfolio_out(item)


@router.delete("/portfolio/{item_id}", response_model=Message)
def delete_portfolio(item_id: int, user: User = Depends(designer_only), db: Session = Depends(get_db)):
    profile = my_profile(db, user)
    item = db.get(PortfolioItem, item_id)
    if item is None or item.designer_id != profile.id:
        raise HTTPException(status_code=404, detail="Portfolio item not found")
    db.delete(item)
    db.commit()
    return {"message": "Portfolio item deleted"}
