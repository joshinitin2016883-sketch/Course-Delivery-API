"""Course endpoints. Each one validates the request and hands it to course_service."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models import User
from app.schemas.courses import CourseIn, CourseOut
from app.services import course_service

router = APIRouter(prefix="/courses", tags=["courses"])


@router.post("", response_model=CourseOut, status_code=201)
def create_course(body: CourseIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return course_service.create_course(db, user, body)


@router.get("/{course_id}", response_model=CourseOut)
def get_course(course_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return course_service.get_course(db, user, course_id)


@router.put("/{course_id}", response_model=CourseOut)
def update_course(
    course_id: int, body: CourseIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return course_service.update_course(db, user, course_id, body)
