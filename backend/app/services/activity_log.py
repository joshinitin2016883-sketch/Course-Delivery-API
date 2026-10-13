"""Writing to a course's activity log.

record() only adds the row to the current transaction. The service that made the change commits
once, so the change and its log row are saved together or not at all.
There is deliberately no function here that edits or deletes a log row.
"""
from typing import Any

from sqlalchemy.orm import Session

from app.models import ActivityLog, User


def record(db: Session, course_id: int, actor: User, action: str, details: dict[str, Any]) -> ActivityLog:
    entry = ActivityLog(course_id=course_id, actor_id=actor.id, action=action, details=details)
    db.add(entry)
    return entry


def apply_changes(target: Any, new_values: dict[str, Any]) -> dict[str, Any]:
    """Copy new_values onto target and return only what really changed: {field: {"from": old, "to": new}}."""
    changes = {}
    for field, new_value in new_values.items():
        old_value = getattr(target, field)
        if new_value != old_value:
            changes[field] = {"from": old_value, "to": new_value}
            setattr(target, field, new_value)
    return changes
