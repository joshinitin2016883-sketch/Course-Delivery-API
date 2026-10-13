"""Goal 1, accounts and roles: signing in, and the server working out who is calling."""
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy.exc import IntegrityError

from app.core.config import JWT_SECRET
from app.core.security import verify_password
from app.models import Role, User


def login(client, email, password):
    return client.post("/auth/login", json={"email": email, "password": password})


def make_token(user_id, secret=JWT_SECRET, algorithm="HS256", expires_at=None):
    """Build a token by hand, so tests can make tokens the server itself would never issue."""
    expires_at = expires_at or datetime.now(timezone.utc) + timedelta(hours=1)
    return jwt.encode({"sub": str(user_id), "exp": expires_at}, secret, algorithm=algorithm)


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


# --- Signing in -------------------------------------------------------------------------------


def test_login_with_the_right_password_returns_a_token_for_that_user(client, make_user):
    user = make_user(email="sam@example.com", password="right-password")

    response = login(client, "sam@example.com", "right-password")

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    me = client.get("/auth/me", headers=bearer(response.json()["access_token"]))
    assert me.json()["id"] == user.id


def test_login_ignores_case_and_spaces_around_the_email(client, make_user):
    make_user(email="sam@example.com", password="right-password")

    response = login(client, "  Sam@Example.COM ", "right-password")

    assert response.status_code == 200


def test_wrong_password_and_unknown_email_get_the_same_401(client, make_user):
    make_user(email="sam@example.com", password="right-password")

    wrong_password = login(client, "sam@example.com", "wrong-password")
    unknown_email = login(client, "nobody@example.com", "right-password")

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    # Identical answers, so the login form can't be used to discover which emails have accounts.
    assert wrong_password.json() == unknown_email.json() == {"detail": "Incorrect email or password."}


def test_password_longer_than_bcrypt_allows_is_a_401_not_a_crash(client, make_user):
    make_user(email="sam@example.com", password="right-password")

    response = login(client, "sam@example.com", "x" * 100)

    assert response.status_code == 401


# --- Who is calling: GET /auth/me --------------------------------------------------------------


def test_me_returns_the_signed_in_user_without_the_password_hash(client, make_user, auth_header):
    user = make_user(email="priya@example.com", role=Role.INSTRUCTOR, full_name="Priya Shah")

    response = client.get("/auth/me", headers=auth_header(user))

    assert response.status_code == 200
    assert response.json() == {
        "id": user.id,
        "email": "priya@example.com",
        "full_name": "Priya Shah",
        "role": "instructor",
    }


def test_me_without_a_token_is_401(client):
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_me_with_a_malformed_token_is_401(client):
    response = client.get("/auth/me", headers=bearer("not-a-real-token"))

    assert response.status_code == 401


def test_me_with_a_non_bearer_authorization_header_is_401(client):
    response = client.get("/auth/me", headers={"Authorization": "Basic c2FtOnBhc3N3b3Jk"})

    assert response.status_code == 401


def test_me_with_a_token_signed_by_someone_else_is_401(client, make_user):
    user = make_user()
    forged = make_token(user.id, secret="a-secret-the-server-does-not-know-0123456789")

    response = client.get("/auth/me", headers=bearer(forged))

    assert response.status_code == 401


def test_me_with_an_unsigned_alg_none_token_is_401(client, make_user):
    user = make_user()
    unsigned = make_token(user.id, secret=None, algorithm="none")

    response = client.get("/auth/me", headers=bearer(unsigned))

    assert response.status_code == 401


def test_me_with_an_expired_token_is_401(client, make_user):
    user = make_user()
    expired = make_token(user.id, expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))

    response = client.get("/auth/me", headers=bearer(expired))

    assert response.status_code == 401


def test_me_with_a_token_for_a_deleted_user_is_401(client, db, make_user, auth_header):
    user = make_user()
    header = auth_header(user)
    db.delete(user)
    db.commit()

    response = client.get("/auth/me", headers=header)

    assert response.status_code == 401


def test_role_is_read_from_the_database_not_the_token(client, db, make_user, auth_header):
    user = make_user(role=Role.LEARNER)
    header = auth_header(user)
    user.role = Role.INSTRUCTOR
    db.commit()

    response = client.get("/auth/me", headers=header)

    assert response.json()["role"] == "instructor"


# --- Stored passwords and the users table ------------------------------------------------------


def test_passwords_are_stored_as_bcrypt_hashes(make_user):
    user = make_user(password="right-password")

    assert user.password_hash != "right-password"
    assert user.password_hash.startswith("$2b$")
    assert verify_password("right-password", user.password_hash)
    assert not verify_password("wrong-password", user.password_hash)


def test_database_rejects_an_unknown_role(db):
    db.add(User(email="x@example.com", full_name="X", role="admin", password_hash="x"))

    with pytest.raises(IntegrityError, match="ck_users_role_allowed"):
        db.flush()


def test_database_rejects_an_email_that_is_not_trimmed_and_lower_case(db):
    db.add(User(email="Sam@Example.com", full_name="Sam", role=Role.LEARNER, password_hash="x"))

    with pytest.raises(IntegrityError, match="ck_users_email_normalized"):
        db.flush()


def test_database_rejects_a_second_account_with_the_same_email(db, make_user):
    make_user(email="sam@example.com")
    db.add(User(email="sam@example.com", full_name="Other Sam", role=Role.LEARNER, password_hash="x"))

    with pytest.raises(IntegrityError, match="uq_users_email"):
        db.flush()
