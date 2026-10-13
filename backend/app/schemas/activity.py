"""Request and response bodies for comments and the activity feed."""
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, StringConstraints

# Spaces around the text are removed before the length is checked, so "   " counts as empty.
CommentText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class CommentIn(BaseModel):
    text: CommentText


class ActorOut(BaseModel):
    """Who made an entry. The role lets the frontend mark an instructor's replies."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    role: str


class ActivityOut(BaseModel):
    """One entry of a course's activity log: a change to the course, or a comment."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    details: dict[str, Any]
    created_at: datetime
    actor: ActorOut
