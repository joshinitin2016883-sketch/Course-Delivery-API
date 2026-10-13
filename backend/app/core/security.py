"""Password hashing (bcrypt) and login tokens (JWT). Plain functions: no database, no HTTP."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import JWT_EXPIRE_MINUTES, JWT_SECRET

JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    password_bytes = password.encode("utf-8")
    # bcrypt raises an error for input over 72 bytes, so no stored hash can belong to a longer password.
    if len(password_bytes) > 72:
        return False
    return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))


def create_access_token(user_id: int) -> str:
    """A signed token that says "this is user <user_id>" until it expires. It holds nothing else."""
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expires_at}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def read_access_token(token: str) -> int | None:
    """Return the user id inside a valid token, or None if it is malformed, forged or expired."""
    try:
        # Only HS256 is accepted, so a token claiming another algorithm (such as "none") is rejected.
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"require": ["exp", "sub"]})
        return int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError):
        return None
