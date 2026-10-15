"""Create the demo accounts, and with --demo the demo data too. Run from backend/:
    python -m app.seed           the 7 demo accounts
    python -m app.seed --demo    the accounts, then demo courses, learners and progress (app/demo_seed.py)

Every demo account gets the password in the SEED_PASSWORD environment variable.
Safe to run again: accounts that already exist are left alone, and the demo data is only added to a
database that has no courses yet.
"""
import argparse
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import demo_seed
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import Role, User

DEMO_USERS = [
    ("instructor@example.com", "Priya Shah", Role.INSTRUCTOR),
    ("instructor2@example.com", "Daniel Okafor", Role.INSTRUCTOR),
    ("learner@example.com", "Alex Chen", Role.LEARNER),
    ("maria@example.com", "Maria Garcia", Role.LEARNER),
    ("sam@example.com", "Sam Taylor", Role.LEARNER),
    ("jordan@example.com", "Jordan Lee", Role.LEARNER),
    ("fatima@example.com", "Fatima Khan", Role.LEARNER),
]


def create_demo_accounts(db: Session, password_hash: str) -> int:
    """Add the demo accounts that don't exist yet, and return how many were added."""
    created = 0
    for email, full_name, role in DEMO_USERS:
        if db.scalar(select(User).where(User.email == email)) is None:
            db.add(User(email=email, full_name=full_name, role=role, password_hash=password_hash))
            created += 1
    db.commit()
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the demo accounts.")
    parser.add_argument("--demo", action="store_true", help="also add demo courses, learners and progress")
    demo = parser.parse_args().demo

    password = os.environ.get("SEED_PASSWORD")
    if not password:
        raise SystemExit("Set SEED_PASSWORD (see backend/.env.example) before seeding.")
    # Every account has the same password, so one hash serves them all (bcrypt is slow on purpose).
    password_hash = hash_password(password)

    with SessionLocal() as db:
        created = create_demo_accounts(db, password_hash)
        print(f"Created {created} demo account(s); {len(DEMO_USERS) - created} already existed.")
        if demo:
            added = demo_seed.add_demo_data(db, password_hash)
            print(added or "Courses already exist, so no demo data was added (it only goes into an empty database).")


if __name__ == "__main__":
    main()
