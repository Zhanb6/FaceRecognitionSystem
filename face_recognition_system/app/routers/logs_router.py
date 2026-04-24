"""
Logs router — CRUD for RecognitionLog, mirrors RecognitionLogViewSet.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CustomUser, RecognitionLog
from ..schemas import RecognitionLogCreate
from ..auth import get_current_user
from ..utils import is_super_admin

router = APIRouter()


def _log_out(log: RecognitionLog) -> dict:
    return {
        "id": log.id,
        "camera_account": log.camera_account_id,
        "person": log.person_id,
        "person_name": log.person.full_name if log.person else None,
        "unknown_face": log.unknown_face,
        "confidence": log.confidence,
        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
    }


def _get_logs_queryset(user: CustomUser, db: Session):
    if is_super_admin(user):
        return db.query(RecognitionLog).order_by(RecognitionLog.timestamp.desc()).all()
    if user.is_camera:
        return (
            db.query(RecognitionLog)
            .filter(RecognitionLog.camera_account_id == user.id)
            .order_by(RecognitionLog.timestamp.desc())
            .all()
        )
    return (
        db.query(RecognitionLog)
        .join(CustomUser, RecognitionLog.camera_account_id == CustomUser.id)
        .filter(CustomUser.company_id == user.company_id)
        .order_by(RecognitionLog.timestamp.desc())
        .all()
    )


@router.get("/all_logs/")
def all_logs(
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logs = _get_logs_queryset(current_user, db)[:100]
    return [_log_out(l) for l in logs]


@router.get("/")
def list_logs(
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logs = _get_logs_queryset(current_user, db)
    return [_log_out(l) for l in logs]


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_log(
    body: RecognitionLogCreate,
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log = RecognitionLog(
        camera_account_id=current_user.id,
        person_id=body.person,
        unknown_face=body.unknown_face,
        confidence=body.confidence,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return _log_out(log)
