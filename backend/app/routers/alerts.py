"""Inactivity alert endpoints. Each one validates the request and hands it to alert_service."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models import User
from app.schemas.alerts import AlertOut, DismissAlertIn
from app.services import alert_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return alert_service.list_alerts(db, user)


@router.post("/dismiss", status_code=204)
def dismiss_alert(body: DismissAlertIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    alert_service.dismiss_alert(db, user, body.course_id, body.learner_id)
