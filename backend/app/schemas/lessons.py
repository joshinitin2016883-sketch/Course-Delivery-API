"""Request and response bodies for lessons."""
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

# Spaces around the text are removed before the length is checked, so "   " counts as empty.
LessonTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
LessonContent = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)]


class LessonIn(BaseModel):
    """Body for adding a lesson, and for editing one (both fields are sent every time)."""

    title: LessonTitle
    content: LessonContent


class LessonOrder(BaseModel):
    """Every lesson id of the course, in the new order."""

    lesson_ids: list[int]


class LessonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    position: int
