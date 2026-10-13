"""Create the demo accounts. Run from backend/:  python -m app.seed

Every demo account gets the password in the SEED_PASSWORD environment variable.
Safe to run again: accounts that already exist are left alone.
"""
import os

from sqlalchemy import select

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


def main() -> None:
    password = os.environ.get("SEED_PASSWORD")
    if not password:
        raise SystemExit("Set SEED_PASSWORD (see backend/.env.example) before seeding.")

    created = 0
    with SessionLocal() as db:
        for email, full_name, role in DEMO_USERS:
            if db.scalar(select(User).where(User.email == email)) is None:
                db.add(User(email=email, full_name=full_name, role=role, password_hash=hash_password(password)))
                created += 1
        db.commit()
    print(f"Created {created} demo account(s); {len(DEMO_USERS) - created} already existed.")


if __name__ == "__main__":
    main()
