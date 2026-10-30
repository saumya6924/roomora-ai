"""Designer profiles and customer bookings."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.enums import BookingStatus, DesignerStatus, Role
from app.core.security import get_current_user, require_role
from app.db.session import get_db
from app.models import Booking, DesignerProfile, User
from app.routers._common import parse_enum
from app.schemas.catalog import DesignerOut, DesignerProfileCreate
from app.schemas.commerce import BookingCreate, BookingOut
from app.schemas.common import StatusUpdate
from app.services.platform import require_enabled

router = APIRouter(prefix="/designers", tags=["Designers"])
bookings_router = APIRouter(prefix="/bookings", tags=["Designer Bookings"])

admin_only = require_role(Role.ADMIN)

# Who may move a booking to which status. Admins may set any status.
BOOKING_FLOW = {
    BookingStatus.PENDING: {BookingStatus.ACCEPTED, BookingStatus.DECLINED},
    BookingStatus.ACCEPTED: {BookingStatus.COMPLETED},
}


def designer_out(profile: DesignerProfile) -> dict:
    """Mix profile and user data into the shape the frontend needs."""
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "name": profile.user.name,
        "title": profile.title,
        "speciality": profile.speciality,
        "location": profile.location,
        "price_per_day": profile.price_per_day,
        "is_available": profile.is_available,
        "status": profile.status,
    }


def profile_for(user: User, db: Session) -> DesignerProfile:
    profile = db.query(DesignerProfile).filter(DesignerProfile.user_id == user.id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Designer profile not found")
    return profile


# ================================================================== DESIGNERS
@router.get("", response_model=list[DesignerOut])
def list_designers(db: Session = Depends(get_db)):
    """The public list: approved and visible designers only."""
    profiles = (
        db.query(DesignerProfile)
        .filter(DesignerProfile.status == DesignerStatus.APPROVED, DesignerProfile.is_visible.is_(True))
        .order_by(DesignerProfile.id)
        .all()
    )
    return [designer_out(p) for p in profiles]


@router.post("", response_model=DesignerOut, status_code=201)
def create_designer(
    data: DesignerProfileCreate,
    admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    """Admin turns an existing user into a designer."""
    user = db.get(User, data.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if db.query(DesignerProfile).filter(DesignerProfile.user_id == user.id).first():
        raise HTTPException(status_code=400, detail="This user is already a designer")

    user.role = Role.DESIGNER
    profile = DesignerProfile(
        user_id=user.id,
        speciality=data.speciality,
        price_per_day=data.price_per_day,
        status=DesignerStatus.APPROVED,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return designer_out(profile)


@router.patch("/me/availability", response_model=DesignerOut)
def toggle_availability(
    designer: User = Depends(require_role(Role.DESIGNER)),
    db: Session = Depends(get_db),
):
    """The available / not available switch on the designer dashboard."""
    profile = profile_for(designer, db)
    profile.is_available = not profile.is_available
    db.commit()
    return designer_out(profile)


@router.patch("/{designer_id}/status", response_model=DesignerOut)
def set_designer_status(
    designer_id: int,
    data: StatusUpdate,
    admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    new_status = parse_enum(DesignerStatus, data.status)
    profile = db.get(DesignerProfile, designer_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Designer not found")
    profile.status = new_status
    db.commit()
    return designer_out(profile)


# ================================================================== BOOKINGS
@bookings_router.post("", response_model=BookingOut, status_code=201)
def create_booking(
    data: BookingCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_enabled(db, "designer_bookings_enabled", "Designer bookings are temporarily closed")
    profile = db.get(DesignerProfile, data.designer_id)
    if profile is None or profile.status != DesignerStatus.APPROVED or not profile.is_visible:
        raise HTTPException(status_code=404, detail="Designer not found")
    if not profile.is_available:
        raise HTTPException(status_code=400, detail="This designer is not available right now")
    if profile.user_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot book yourself")

    booking = Booking(
        user_id=user.id,
        designer_id=profile.id,
        total_amount=profile.price_per_day * data.days,  # the server calculates the money
        **data.model_dump(exclude={"designer_id"}),
    )
    booking.email = booking.email.lower()
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@bookings_router.get("/mine", response_model=list[BookingOut])
def my_bookings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Booking).filter(Booking.user_id == user.id).order_by(Booking.id.desc()).all()


@bookings_router.get("/designer", response_model=list[BookingOut])
def designer_bookings(
    designer: User = Depends(require_role(Role.DESIGNER)),
    db: Session = Depends(get_db),
):
    profile = db.query(DesignerProfile).filter(DesignerProfile.user_id == designer.id).first()
    if profile is None:
        return []
    return db.query(Booking).filter(Booking.designer_id == profile.id).order_by(Booking.id.desc()).all()


@bookings_router.patch("/{booking_id}/status", response_model=BookingOut)
def update_booking_status(
    booking_id: int,
    data: StatusUpdate,
    user: User = Depends(require_role(Role.DESIGNER, Role.ADMIN)),
    db: Session = Depends(get_db),
):
    """Designer presses Accept / Decline / Mark completed."""
    new_status = parse_enum(BookingStatus, data.status)
    if new_status == BookingStatus.PENDING:
        raise HTTPException(status_code=400, detail="A booking cannot go back to pending")

    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    if user.role == Role.DESIGNER and booking.designer.user_id != user.id:
        raise HTTPException(status_code=403, detail="This booking is not yours")
    if user.role == Role.DESIGNER and new_status not in BOOKING_FLOW.get(booking.status, set()):
        raise HTTPException(
            status_code=400, detail=f"A {booking.status.value} booking cannot become {new_status.value}"
        )

    booking.status = new_status
    if new_status == BookingStatus.COMPLETED:
        booking.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(booking)
    return booking
