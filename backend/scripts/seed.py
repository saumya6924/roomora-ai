"""Fill the database with demo data.

    python -m scripts.seed                 add demo data to an empty database
    python -m scripts.seed --reset         wipe every table first, then add demo data
    python -m scripts.seed --no-activity   accounts and catalogue only (no orders, bookings, reviews...)

Demo logins (change or delete these before real use):
    admin@roomora.com    / Admin@1234
    seller@roomora.com   / Seller@1234
    user@roomora.com     / User@1234     (also nancy@, arjun@, meera@, riya@, kabir@roomora.com)
    saumya@roomora.com   / Designer@1234 (and the other five designers)
"""

import argparse
from decimal import Decimal

from app.core.enums import DesignerStatus, ProductStatus, Role
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal
from app.models import DesignerProfile, Product, SellerProfile, User

UNSPLASH = "https://images.unsplash.com/{}?auto=format&fit=crop&w=900&q=80"

# (name, price, category, image) - the Marble Coffee Table photo ships with the frontend.
PRODUCTS = [
    ("Modern Boucle Sofa", 42999, "Sofa", UNSPLASH.format("photo-1555041469-a586c61ea9bc")),
    ("Oak Lounge Chair", 18499, "Chair", UNSPLASH.format("photo-1567538096630-e0c55bd6374c")),
    ("Marble Coffee Table", 14999, "Table", "assets/img/products/marble-coffee-table.avif"),
    ("Arched Floor Lamp", 7999, "Lighting", UNSPLASH.format("photo-1507473885765-e6ed057f782c")),
    ("Minimal Bed", 36500, "Bed", UNSPLASH.format("photo-1505693416388-ac5ce068fe85")),
    ("Oak Dining Set", 29990, "Dining", UNSPLASH.format("photo-1617806118233-18e1de247200")),
    ("Accent Armchair", 16750, "Chair", UNSPLASH.format("photo-1598300042247-d088f8ab3a91")),
    ("Console Table", 12499, "Table", UNSPLASH.format("photo-1538688525198-9b88f6f53126")),
    ("Pendant Light", 5499, "Lighting", UNSPLASH.format("photo-1524484485831-a92ffc0de03f")),
    ("Designer Rug", 9999, "Decor", UNSPLASH.format("photo-1600166898405-da9535204843")),
]

DESIGNERS = [
    ("Saumya Bhatiya", "saumya@roomora.com", 4500, "Modern homes · Space planning · 3D concepts"),
    ("Ruchi", "ruchi@roomora.com", 6000, "Luxury interiors · Hotels · Hospitality"),
    ("Shreyash Patel", "shreyash@roomora.com", 3500, "Cafes · Retail · Budget transformations"),
    ("Dhwanit Agrawal", "dhwanit@roomora.com", 5000, "Minimalist homes · Furniture styling"),
    ("Rich Kapoor", "rich@roomora.com", 7500, "Premium hotels · Commercial spaces"),
    ("Anaya Panday", "anaya@roomora.com", 4000, "Color planning · Home makeovers"),
]


def wipe(db) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()


def make_user(db, name: str, email: str, password: str, role: Role) -> User:
    user = User(name=name, email=email, mobile="9876543210", password_hash=hash_password(password), role=role)
    db.add(user)
    db.flush()  # gives the user an id without finishing the save
    return user


def seed_all(db, activity: bool = True) -> None:
    """Accounts and catalogue, plus (by default) linked demo activity."""
    make_user(db, "Roomora Admin", "admin@roomora.com", "Admin@1234", Role.ADMIN)
    seller = make_user(db, "Urban Living", "seller@roomora.com", "Seller@1234", Role.SELLER)
    db.add(SellerProfile(user_id=seller.id, store_name="Urban Living", business_email="seller@roomora.com"))
    make_user(db, "Demo User", "user@roomora.com", "User@1234", Role.USER)

    for name, price, category, image in PRODUCTS:
        db.add(
            Product(
                seller_id=seller.id,
                name=name,
                category=category,
                price=Decimal(price),
                mrp=Decimal(round(price * 1.15)),
                stock=25,
                short_description=f"{name} for modern interiors",
                image_url=image,
                status=ProductStatus.APPROVED,
            )
        )

    for name, email, price, speciality in DESIGNERS:
        user = make_user(db, name, email, "Designer@1234", Role.DESIGNER)
        db.add(
            DesignerProfile(
                user_id=user.id,
                speciality=speciality,
                price_per_day=Decimal(price),
                status=DesignerStatus.APPROVED,
            )
        )
    db.commit()

    if activity:
        from scripts.demo_activity import add_demo_activity

        add_demo_activity(db)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="delete all existing data first")
    parser.add_argument("--no-activity", action="store_true", help="skip orders, bookings, reviews and so on")
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.reset:
            wipe(db)
        elif db.query(User).first():
            raise SystemExit("The database already has data. Run with --reset to start fresh.")
        seed_all(db, activity=not args.no_activity)
    print("Done. Demo data added.")


if __name__ == "__main__":
    main()
