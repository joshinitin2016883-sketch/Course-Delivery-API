"""Enrolment endpoints. Each one validates the request and hands it to enrollment_service."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models import User
from app.schemas.enrollments import EnrollmentOut
from app.services import enrollment_service

router = APIRouter(tags=["enrolment"])


@router.post("/courses/{course_id}/enroll", response_model=EnrollmentOut, status_code=201)
def enroll(course_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return enrollment_service.enroll(db, user, course_id)


@router.get("/me/courses", response_model=list[EnrollmentOut])
def my_courses(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return enrollment_service.list_my_courses(db, user)
