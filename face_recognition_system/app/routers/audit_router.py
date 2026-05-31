"""
Audit logs router — read-only for Super Admins.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CustomUser, AuditLog
from ..auth import get_current_user
from ..utils import is_super_admin

router = APIRouter()


def _utc_isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


@router.get("/")
def list_audit_logs(
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin permission required")

    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    return [
        {
            "id": log.id,
            "user": log.user_id,
            "username": log.user.username if log.user else None,
            "action": log.action,
            "details": log.details,
            "timestamp": _utc_isoformat(log.timestamp),
        }
        for log in logs
    ]
