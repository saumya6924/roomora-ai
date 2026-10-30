"""Believable activity for the demo accounts, so every dashboard has something to show.

Deterministic (fixed random seed): the same data every time. Dates are relative to "now".
"""

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.enums import (
    BookingStatus,
    NotificationType,
    OrderItemStatus,
    PaymentStatus,
    PayoutStatus,
    Role,
    ServiceUnit,
)
from app.core.security import hash_password
from app.models import (
    Booking,
    DesignerProfile,
    DesignerService,
    Notification,
    Order,
    OrderItem,
    Payout,
    PortfolioItem,
    Product,
    Review,
    SellerProfile,
    User,
)

UNSPLASH = "https://images.unsplash.com/{}?auto=format&fit=crop&w=900&q=80"

CUSTOMERS = [
    ("Nancy Panchal", "nancy@roomora.com", "Ahmedabad"),
    ("Arjun Patel", "arjun@roomora.com", "Mumbai"),
    ("Meera Joshi", "meera@roomora.com", "Pune"),
    ("Riya Shah", "riya@roomora.com", "Surat"),
    ("Kabir Mehta", "kabir@roomora.com", "Delhi"),
]
CITIES = {"Ahmedabad": "380001", "Mumbai": "400001", "Pune": "411001", "Surat": "395003", "Delhi": "110001"}

PRODUCT_REVIEWS = [
    (5, "Beautiful quality!", "Looks exactly like the pictures and it transformed my living room."),
    (5, "Great purchase", "Very premium finish and the delivery was smooth. Sturdy and elegant."),
    (4, "Good value", "Nice design and comfortable. The colour is slightly lighter than the photo."),
    (5, "Love it", "Easy to assemble and it looks wonderful in our home."),
    (4, "Solid and stylish", "Well built. Delivery took a day longer than promised."),
]
DESIGNER_REVIEWS = [
    (
        5,
        "Excellent designer",
        "Understood my requirements perfectly. The final concept was better than I expected.",
    ),
    (
        5,
        "Beautiful work",
        "Helped us choose the right furniture and colours. Very creative and easy to work with.",
    ),
    (4, "Professional", "Great ideas and on time. Would book again."),
]

SERVICES = [
    (
        "RESIDENTIAL",
        "Room Redesign",
        "Complete redesign of bedrooms, living rooms and dining rooms.",
        1.0,
        "day",
    ),
    (
        "COMMERCIAL",
        "Cafe & Restaurant",
        "Concept design for cafes, restaurants and hospitality spaces.",
        1.5,
        "day",
    ),
    (
        "CONSULTATION",
        "Design Consultation",
        "One-to-one consultation on colours, furniture and layout.",
        0.45,
        "session",
    ),
]
PORTFOLIO = [
    ("RESIDENTIAL", "Modern Luxury Apartment", "Mumbai", 2400, "photo-1600210492486-724fe5c67fb0"),
    ("COMMERCIAL", "Minimal Cafe Concept", "Ahmedabad", 1200, "photo-1554118811-1e0d58224f24"),
    ("HOSPITALITY", "Boutique Hotel Lobby", "Goa", 3800, "photo-1564501049412-61c2a3083791"),
    ("OFFICE", "Contemporary Workspace", "Bangalore", 2100, "photo-1497366754035-f200968a6e72"),
]


def _ago(now: datetime, days: float) -> datetime:
    return now - timedelta(days=days)


def add_demo_activity(db: Session) -> None:
    rng = random.Random(7)
    now = datetime.now(UTC)

    seller = db.query(User).filter_by(email="seller@roomora.com").one()
    admin = db.query(User).filter_by(email="admin@roomora.com").one()
    demo_user = db.query(User).filter_by(email="user@roomora.com").one()
    products = db.query(Product).filter_by(seller_id=seller.id).all()
    designers = db.query(DesignerProfile).order_by(DesignerProfile.id).all()

    # ---------------------------------------------------------------- people
    customers = [demo_user]
    for name, email, city in CUSTOMERS:
        user = User(
            name=name,
            email=email,
            mobile="9876543210",
            password_hash=hash_password("User@1234"),
            role=Role.USER,
            location=city,
            last_login_at=_ago(now, rng.randint(0, 25)),
            created_at=_ago(now, rng.randint(60, 200)),
        )
        db.add(user)
        customers.append(user)
    demo_user.last_login_at = _ago(now, 1)
    admin.last_login_at = now
    db.flush()

    profile = db.query(SellerProfile).filter_by(user_id=seller.id).one()
    profile.gst_number = "24ABCDE1234F1Z5"
    profile.bank_holder = "Urban Living"
    profile.bank_account_masked = "HDFC Bank •••• 2381"
    profile.ifsc = "HDFC0001234"

    # ---------------------------------------------------------------- furniture orders, spread over ~8 months
    for p in products:
        p.sku = f"UL-{p.category[:3].upper()}-{p.id:03d}"
        p.low_stock_threshold = 5
        p.warehouse = "Ahmedabad Warehouse"
        p.material = rng.choice(["Solid Wood", "Fabric", "Metal", "Marble"])
        p.created_at = _ago(now, rng.randint(40, 220))

    reviewed: set[tuple[int, int]] = set()
    review_i = 0
    for n in range(18):
        age = 235 - n * 13 + rng.randint(0, 6)  # oldest first, newest within the last fortnight
        age = max(age, 1)
        buyer = customers[n % len(customers)]
        city = buyer.location or "Ahmedabad"
        method = ["COD", "UPI", "Card"][n % 3]
        order = Order(
            user_id=buyer.id,
            payment_method=method,
            full_name=buyer.name,
            mobile=buyer.mobile,
            address=f"{rng.randint(1, 99)} Rose Apartments, MG Road",
            city=city,
            state="",
            pincode=CITIES.get(city, "380001"),
            created_at=_ago(now, age),
        )
        total = Decimal("0")
        for product in rng.sample(products, rng.randint(1, 3)):
            qty = rng.randint(1, 2)
            if age > 20:
                status = OrderItemStatus.CANCELLED if rng.random() < 0.06 else OrderItemStatus.DELIVERED
            else:
                status = rng.choice([OrderItemStatus.PLACED, OrderItemStatus.PACKED, OrderItemStatus.SHIPPED])
            item = OrderItem(
                product_id=product.id,
                seller_id=seller.id,
                product_name=product.name,
                price=product.price,
                quantity=qty,
                status=status,
                updated_at=_ago(now, max(age - 4, 0)),
            )
            order.items.append(item)
            if status != OrderItemStatus.CANCELLED:
                total += product.price * qty
                product.stock = max(product.stock - qty, 2)
        order.total_amount = total
        live = [i for i in order.items if i.status != OrderItemStatus.CANCELLED]
        if method == "COD" and live and all(i.status == OrderItemStatus.DELIVERED for i in live):
            order.payment_status = PaymentStatus.PAID
        db.add(order)
        db.flush()

        for item in order.items:
            if (
                item.status == OrderItemStatus.DELIVERED
                and (buyer.id, item.product_id) not in reviewed
                and rng.random() < 0.55
            ):
                rating, title, body = PRODUCT_REVIEWS[review_i % len(PRODUCT_REVIEWS)]
                review_i += 1
                reviewed.add((buyer.id, item.product_id))
                db.add(
                    Review(
                        user_id=buyer.id,
                        product_id=item.product_id,
                        rating=rating,
                        title=title,
                        body=body,
                        created_at=_ago(now, max(age - 7, 0)),
                    )
                )

    # ------------------------------------------------ designers: profiles, services, portfolio
    for d in designers:
        d.title = "Interior Designer"
        d.experience = rng.choice(["3 - 5 Years", "5 - 10 Years", "10+ Years"])
        d.location = rng.choice(["Mumbai, Maharashtra", "Ahmedabad, Gujarat", "Pune, Maharashtra", "Delhi"])
        focus = d.speciality.split("·")[0].strip().lower()
        d.about = (
            f"I specialise in {focus}. I help clients transform their spaces through thoughtful "
            "layouts, colour palettes, furniture selection and personalised design concepts."
        )
        d.contract_terms = (
            "• Client must provide accurate room measurements and reference images.\n"
            "• Design revisions are limited to 3 rounds per project.\n"
            "• Cancellation terms are subject to the Roomora AI booking agreement."
        )
        d.bank_holder = d.user.name
        d.bank_account_masked = "HDFC Bank •••• 2381"
        d.ifsc = "HDFC0001234"
        d.view_count = rng.randint(120, 1800)
        for category, name, description, factor, unit in SERVICES:
            db.add(
                DesignerService(
                    designer_id=d.id,
                    category=category,
                    name=name,
                    description=description,
                    price=(d.price_per_day * Decimal(str(factor))).quantize(Decimal("1")),
                    unit=ServiceUnit(unit),
                )
            )
        for category, title, location, area, photo in rng.sample(PORTFOLIO, 3):
            db.add(
                PortfolioItem(
                    designer_id=d.id,
                    title=title,
                    category=category,
                    location=location,
                    area_sqft=area,
                    image_url=UNSPLASH.format(photo),
                )
            )

    # ---------------------------------------------------------------- bookings
    designer_review_i = 0
    plan = [  # (days ago created, status, days booked)
        (150, BookingStatus.COMPLETED, 3),
        (120, BookingStatus.COMPLETED, 2),
        (95, BookingStatus.COMPLETED, 5),
        (70, BookingStatus.COMPLETED, 2),
        (45, BookingStatus.COMPLETED, 3),
        (30, BookingStatus.DECLINED, 2),
        (12, BookingStatus.ACCEPTED, 4),
        (8, BookingStatus.ACCEPTED, 2),
        (5, BookingStatus.PENDING, 3),
        (3, BookingStatus.PENDING, 1),
        (2, BookingStatus.PENDING, 2),
        (1, BookingStatus.PENDING, 3),
    ]
    reviewed_designers: set[tuple[int, int]] = set()
    for n, (age, status, days) in enumerate(plan):
        designer = designers[
            n % 2 if n < 8 else n % len(designers)
        ]  # the first two designers get the busy history
        customer = customers[(n + 1) % len(customers)]
        created = _ago(now, age)
        start = (created + timedelta(days=rng.randint(3, 9))).date()
        if status == BookingStatus.ACCEPTED:
            start = (now + timedelta(days=rng.randint(-1, 6))).date()
        booking = Booking(
            user_id=customer.id,
            designer_id=designer.id,
            name=customer.name,
            mobile=customer.mobile,
            email=customer.email,
            project_type=rng.choice(["Home", "Cafe", "Office", "Hotel"]),
            location=customer.location or "",
            start_date=start,
            days=days,
            details=rng.choice(
                [
                    "Warm modern living room with neutral colours.",
                    "Cafe interior with wood and plants.",
                    "Minimal bedroom makeover.",
                    "Complete concept including furniture and lighting.",
                ]
            ),
            total_amount=designer.price_per_day * days,
            status=status,
            created_at=created,
        )
        if status != BookingStatus.PENDING:
            booking.responded_at = created + timedelta(hours=rng.randint(1, 20))
        if status == BookingStatus.COMPLETED:
            booking.completed_at = created + timedelta(days=days + 7)
        db.add(booking)
        if (
            status == BookingStatus.COMPLETED
            and (customer.id, designer.id) not in reviewed_designers
            and rng.random() < 0.8
        ):
            reviewed_designers.add((customer.id, designer.id))
            rating, title, body = DESIGNER_REVIEWS[designer_review_i % len(DESIGNER_REVIEWS)]
            designer_review_i += 1
            db.add(
                Review(
                    user_id=customer.id,
                    designer_id=designer.id,
                    rating=rating,
                    title=title,
                    body=body,
                    created_at=_ago(now, max(age - days - 8, 0)),
                )
            )

    # ---------------------------------------------------------------- payouts
    db.add(
        Payout(
            user_id=seller.id,
            amount=Decimal("142500"),
            status=PayoutStatus.COMPLETED,
            reference="PAY-1",
            requested_at=_ago(now, 70),
            processed_at=_ago(now, 68),
        )
    )
    db.add(
        Payout(
            user_id=seller.id,
            amount=Decimal("118200"),
            status=PayoutStatus.COMPLETED,
            reference="PAY-2",
            requested_at=_ago(now, 35),
            processed_at=_ago(now, 33),
        )
    )
    first, second = designers[0], designers[1]
    db.add(
        Payout(
            user_id=first.user_id,
            amount=Decimal("18000"),
            status=PayoutStatus.COMPLETED,
            reference="PAY-3",
            requested_at=_ago(now, 40),
            processed_at=_ago(now, 38),
        )
    )
    db.add(
        Payout(
            user_id=second.user_id,
            amount=Decimal("9000"),
            status=PayoutStatus.REQUESTED,
            reference="PAY-4",
            requested_at=_ago(now, 2),
        )
    )

    # ---------------------------------------------------------------- notifications
    def note(
        user_id: int, kind: NotificationType, title: str, body: str, days: float, read: bool = False
    ) -> None:
        db.add(
            Notification(
                user_id=user_id, type=kind, title=title, body=body, is_read=read, created_at=_ago(now, days)
            )
        )

    note(seller.id, NotificationType.ORDER, "New order received", "Order #18 · 2 item(s)", 0.1)
    note(seller.id, NotificationType.STOCK, "Low stock alert", f"{products[3].name} · 5 units left", 0.4)
    note(
        seller.id,
        NotificationType.REVIEW,
        "New 5-star review",
        "Nancy Panchal reviewed Modern Boucle Sofa.",
        1.2,
        True,
    )
    note(seller.id, NotificationType.PAYOUT, "Payout completed", "PAY-2 is now completed", 33, True)
    for d in designers[:2]:
        note(d.user_id, NotificationType.BOOKING, "New booking request", "Riya Shah · Cafe · 3 day(s)", 0.2)
        note(
            d.user_id,
            NotificationType.REVIEW,
            "New 5-star review",
            "A client reviewed your design work.",
            2.1,
            True,
        )
    note(admin.id, NotificationType.PAYOUT, "Payout requested", "A designer requested PAY-4.", 2)
    note(
        admin.id,
        NotificationType.SYSTEM,
        "Welcome to the admin panel",
        "Review products, designers and payouts here.",
        30,
        True,
    )
    note(demo_user.id, NotificationType.ORDER, "Order update", "Your furniture order has shipped.", 0.5)

    db.commit()
