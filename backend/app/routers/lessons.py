"""Lesson endpoints, nested under their course. Each one validates the request and hands it to lesson_service."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models import User
from app.schemas.lessons import LessonIn, LessonOrder, LessonOut
from app.services import lesson_service

router = APIRouter(prefix="/courses/{course_id}/lessons", tags=["lessons"])


@router.post("", response_model=LessonOut, status_code=201)
def add_lesson(
    course_id: int, body: LessonIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return lesson_service.add_lesson(db, user, course_id, body)


# Declared before "/{lesson_id}", otherwise "order" would be read as a lesson id.
@router.put("/order", response_model=list[LessonOut])
def reorder_lessons(
    course_id: int, body: LessonOrder, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return lesson_service.reorder_lessons(db, user, course_id, body.lesson_ids)


@router.put("/{lesson_id}", response_model=LessonOut)
def edit_lesson(
    course_id: int,
    lesson_id: int,
    body: LessonIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return lesson_service.edit_lesson(db, user, course_id, lesson_id, body)


@router.delete("/{lesson_id}", status_code=204)
def remove_lesson(
    course_id: int, lesson_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    lesson_service.remove_lesson(db, user, course_id, lesson_id)
