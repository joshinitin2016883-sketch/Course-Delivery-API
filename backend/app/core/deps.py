"""FastAPI dependencies: a database session per request, and the user making the request."""
from collections.abc import Iterator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import User
from app.services import auth_service

# auto_error=False: a missing header is passed on as None and auth_service answers with our own 401.
bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Iterator[Session]:
    """Open one session for the request and close it when the request is finished."""
    with SessionLocal() as db:
        yield db


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """The signed-in user, found from the "Authorization: Bearer <token>" header."""
    token = credentials.credentials if credentials else None
    return auth_service.get_user_for_token(db, token)
