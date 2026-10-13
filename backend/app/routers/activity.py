"""Comments on a course, and its activity feed. Each endpoint validates the request and hands it to activity_service."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models import User
from app.schemas.activity import ActivityOut, CommentIn
from app.services import activity_service

router = APIRouter(prefix="/courses/{course_id}", tags=["activity"])


@router.post("/comments", response_model=ActivityOut, status_code=201)
def add_comment(
    course_id: int, body: CommentIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return activity_service.add_comment(db, user, course_id, body.text)


@router.get("/activity", response_model=list[ActivityOut])
def list_activity(
    course_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    before: int | None = Query(default=None, ge=1, description="Only entries older than this entry id"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return activity_service.list_activity(db, user, course_id, limit, before)
