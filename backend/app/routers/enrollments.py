"""Enrolment endpoints. Each one validates the request and hands it to enrollment_service."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models import User
from app.schemas.enrollments import BulkEnrollIn, BulkEnrollOut, EnrollmentOut, LearnerProgressOut, ProgressOut
from app.services import enrollment_service, export_service

router = APIRouter(tags=["enrolment"])


@router.post("/courses/{course_id}/enroll", response_model=EnrollmentOut, status_code=201)
def enroll(course_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return enrollment_service.enroll(db, user, course_id)


# 200, not 201: the answer is a report with an outcome per address, and some may not have enrolled anyone.
@router.post("/courses/{course_id}/enrollments/bulk", response_model=BulkEnrollOut)
def bulk_enroll(
    course_id: int, body: BulkEnrollIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return enrollment_service.bulk_enroll(db, user, course_id, body.text)


@router.post("/courses/{course_id}/lessons/{lesson_id}/complete", response_model=ProgressOut)
def complete_lesson(
    course_id: int, lesson_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return enrollment_service.complete_lesson(db, user, course_id, lesson_id)


@router.get("/courses/{course_id}/progress", response_model=list[LearnerProgressOut])
def course_progress(course_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return enrollment_service.course_progress(db, user, course_id)


# The same learners as GET /courses/{id}/progress, as a file to download.
@router.get("/courses/{course_id}/progress.csv")
def progress_csv(course_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    filename, text = export_service.progress_csv(db, user, course_id)
    return Response(
        content=text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/me/courses", response_model=list[EnrollmentOut])
def my_courses(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return enrollment_service.list_my_courses(db, user)
