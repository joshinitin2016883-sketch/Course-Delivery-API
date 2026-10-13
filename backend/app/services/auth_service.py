"""Signing in, and working out who is making a request."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, read_access_token, verify_password
from app.models import User
from app.services.errors import NotAuthenticated


def normalize_email(email: str) -> str:
    """Emails are compared trimmed and lower-case everywhere, so "Sam@X.com " finds sam@x.com."""
    return email.strip().lower()


def login(db: Session, email: str, password: str) -> str:
    """Check the email and password, and return a new access token for that user."""
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None or not verify_password(password, user.password_hash):
        # One message for both cases, so the response doesn't reveal which emails have accounts.
        raise NotAuthenticated("Incorrect email or password.")
    return create_access_token(user.id)


def get_user_for_token(db: Session, token: str | None) -> User:
    """Return the user a token belongs to. The role is read from the database, never from the token."""
    user_id = read_access_token(token) if token else None
    user = db.get(User, user_id) if user_id is not None else None
    if user is None:
        raise NotAuthenticated("You are not signed in, or your session has expired. Please sign in.")
    return user
