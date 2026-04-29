"""
Logs router — CRUD for RecognitionLog, mirrors RecognitionLogViewSet.
"""
import base64
import binascii
import logging
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..facenet_bridge import FaceEnrollmentError, FaceNetDependencyError, recognize_face_image
from ..models import CustomUser, PersonFace, RecognitionLog
from ..schemas import RecognitionCheckRequest, RecognitionLogCreate
from ..auth import get_current_user
from ..utils import is_company_admin, is_super_admin

router = APIRouter()
logger = logging.getLogger(__name__)


def _log_out(log: RecognitionLog) -> dict:
    return {
        "id": log.id,
        "camera_account": log.camera_account_id,
        "camera_username": log.camera_account.username if log.camera_account else None,
        "person": log.person_id,
        "person_name": log.person.full_name if log.person else None,
        "unknown_face": log.unknown_face,
        "confidence": log.confidence,
        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
    }


def _decode_image_data(image_data: str) -> bytes:
    if not image_data:
        raise HTTPException(status_code=400, detail="Image data is required")

    payload = image_data.split(",", 1)[1] if "," in image_data else image_data
    try:
        image_bytes = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid image data") from exc

    if not image_bytes:
        raise HTTPException(status_code=400, detail="Image data is empty")
    return image_bytes


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


def _can_access_log(user: CustomUser, log: RecognitionLog) -> bool:
    if is_super_admin(user):
        return True
    if user.is_camera:
        return log.camera_account_id == user.id
    return bool(log.camera_account and log.camera_account.company_id == user.company_id)


def _can_delete_log(user: CustomUser, log: RecognitionLog) -> bool:
    if is_super_admin(user):
        return True
    if not is_company_admin(user):
        return False
    return bool(log.camera_account and log.camera_account.company_id == user.company_id)


def _get_visible_camera(user: CustomUser, camera_id: Optional[int], db: Session) -> CustomUser:
    if user.is_camera:
        return user

    query = db.query(CustomUser).filter(CustomUser.is_camera.is_(True))
    if camera_id is not None:
        query = query.filter(CustomUser.id == camera_id)
    if not is_super_admin(user):
        query = query.filter(CustomUser.company_id == user.company_id)

    camera = query.order_by(CustomUser.id.asc()).first()
    if camera:
        return camera

    if camera_id is not None:
        raise HTTPException(status_code=404, detail="Camera not found")
    return user


def _person_id_from_embedding_key(name: str, db: Session) -> Optional[int]:
    if not name.startswith("personface:"):
        return None

    parts = name.split(":", 2)
    if len(parts) < 2 or not parts[1].isdigit():
        return None

    face = db.query(PersonFace).filter(PersonFace.id == int(parts[1])).first()
    return face.id if face else None


def _resolve_allowed_person(name: str, camera: CustomUser, db: Session) -> Tuple[Optional[PersonFace], Optional[str]]:
    if not name.startswith("personface:"):
        return None, None

    parts = name.split(":", 2)
    if len(parts) < 2 or not parts[1].isdigit():
        return None, None

    face = db.query(PersonFace).filter(PersonFace.id == int(parts[1])).first()
    if not face:
        return None, None

    allowed_camera_ids = {allowed_camera.id for allowed_camera in face.allowed_cameras}
    if not allowed_camera_ids:
        return None, "У пользователя нету разрешенных камер"
    if camera.id not in allowed_camera_ids:
        return None, "У пользователя нет доступа к этой камере"
    return face, None


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


@router.get("/{log_id}/")
def get_log(
    log_id: int,
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log = db.query(RecognitionLog).filter(RecognitionLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Not found.")
    if not _can_access_log(current_user, log):
        raise HTTPException(status_code=403, detail="Forbidden for this company")
    return _log_out(log)


@router.post("/check/", status_code=status.HTTP_201_CREATED)
def check_recognition(
    body: RecognitionCheckRequest,
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    image_bytes = _decode_image_data(body.image_data)
    camera = _get_visible_camera(current_user, body.camera_id, db)
    threshold = max(0.0, min(float(body.threshold), 100.0)) / 100.0

    try:
        result = recognize_face_image(image_bytes, threshold)
    except FaceNetDependencyError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"FaceNet dependencies are not installed: {exc}",
        ) from exc
    except FaceEnrollmentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Could not run recognition check")
        raise HTTPException(status_code=500, detail="Could not run recognition check") from exc

    person = None
    message = None
    if result.get("recognized"):
        person, message = _resolve_allowed_person(result.get("name", ""), camera, db)

    log = RecognitionLog(
        camera_account_id=camera.id,
        person_id=person.id if person else None,
        unknown_face=not bool(person),
        confidence=float(result.get("accuracy", 0.0)),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return {
        "log": _log_out(log),
        "recognized": bool(person),
        "person_name": log.person.full_name if log.person else None,
        "accuracy": float(result.get("accuracy", 0.0)),
        "threshold": round(threshold * 100, 1),
        "similarity": float(result.get("score", 0.0)),
        "detection_confidence": float(result.get("detection_confidence", 0.0)),
        "message": message or ("Пользователь распознан" if person else "Пользователь не распознан"),
    }


@router.delete("/{log_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_log(
    log_id: int,
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log = db.query(RecognitionLog).filter(RecognitionLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Not found.")
    if not _can_delete_log(current_user, log):
        raise HTTPException(status_code=403, detail="Forbidden for this company")

    db.delete(log)
    db.commit()


@router.delete("/", status_code=status.HTTP_200_OK)
def delete_logs(
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if is_super_admin(current_user):
        deleted = db.query(RecognitionLog).delete(synchronize_session=False)
    elif is_company_admin(current_user):
        company_camera_ids = [
            camera.id
            for camera in db.query(CustomUser.id)
            .filter(CustomUser.is_camera.is_(True), CustomUser.company_id == current_user.company_id)
            .all()
        ]
        if not company_camera_ids:
            deleted = 0
        else:
            deleted = (
                db.query(RecognitionLog)
                .filter(RecognitionLog.camera_account_id.in_(company_camera_ids))
                .delete(synchronize_session=False)
            )
    else:
        raise HTTPException(status_code=403, detail="Not enough permissions to delete recognition logs")

    db.commit()
    return {"deleted": deleted}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_log(
    body: RecognitionLogCreate,
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_camera:
        raise HTTPException(status_code=403, detail="Only camera accounts can create recognition logs")

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
