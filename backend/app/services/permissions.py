"""Role checks shared by the services."""
from app.models import Role, User
from app.services.errors import PermissionDenied


def require_instructor(user: User) -> None:
    """Stop the request unless the caller is an instructor."""
    if user.role != Role.INSTRUCTOR:
        raise PermissionDenied("Only instructors can do this.")
