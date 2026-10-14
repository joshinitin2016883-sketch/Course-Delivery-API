"""The list of instructors, for the course list's instructor filter. It hands the request to catalogue_service."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.schemas.courses import InstructorOut
from app.services import catalogue_service

router = APIRouter(prefix="/instructors", tags=["courses"])


# Any signed-in user may ask; get_current_user answers 401 for anyone else. InstructorOut has no email field.
@router.get("", response_model=list[InstructorOut], dependencies=[Depends(get_current_user)])
def list_instructors(db: Session = Depends(get_db)):
    return catalogue_service.list_instructors(db)
