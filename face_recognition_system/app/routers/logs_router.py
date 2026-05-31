"""
Logs router — CRUD for RecognitionLog, mirrors RecognitionLogViewSet.
"""
import base64
import binascii
import logging
from datetime import datetime, timezone
from time import perf_counter
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..facenet_bridge import (
    FaceEnrollmentError,
    FaceNetDependencyError,
    available_face_models,
    recognize_face_image,
)
from ..models import CustomUser, PersonFace, RecognitionLog
from ..schemas import RecognitionCheckRequest, RecognitionLogCreate
from ..auth import get_current_user
from ..utils import is_company_admin, is_super_admin

router = APIRouter()
logger = logging.getLogger(__name__)

MODEL_POWER_WATTS = {
    "facenet": 18.0,
    "mobilefacenet": 6.0,
    "efficientnet_lite0": 9.0,
}
MODEL_LABELS = {
    "facenet": "FaceNet",
    "mobilefacenet": "MobileFaceNet",
    "efficientnet_lite0": "EfficientNet-Lite0",
}
MODEL_ALIASES = {
    "facenet-cpu": "facenet",
    "facenet-gpu": "facenet",
    "efficientnet-lite0": "efficientnet_lite0",
    "efficientnet": "efficientnet_lite0",
}


def _normalize_model_name(model_name: Optional[str]) -> str:
    key = (model_name or "efficientnet_lite0").strip().lower()
    key = MODEL_ALIASES.get(key, key)
    return key if key in MODEL_POWER_WATTS else "efficientnet_lite0"


def _model_metrics(model_name: str, elapsed_seconds: float) -> dict:
    safe_elapsed = max(elapsed_seconds, 0.001)
    return {
        "model_name": MODEL_LABELS[model_name],
        "processing_time_ms": round(safe_elapsed * 1000, 2),
        "average_fps": round(1 / safe_elapsed, 2),
        "energy_consumption_wh": round((MODEL_POWER_WATTS[model_name] * safe_elapsed) / 3600, 6),
    }


def _utc_isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


@router.get("/models/")
def recognition_models(current_user: CustomUser = Depends(get_current_user)):
    try:
        models = available_face_models()
    except FaceNetDependencyError as exc:
        raise HTTPException(status_code=503, detail=f"FaceNet dependencies are not installed: {exc}") from exc

    return [
        {
            "key": model["key"],
            "label": model["label"],
            "input_size": model["input_size"],
            "embedding_size": model["embedding_size"],
        }
        for model in models
    ]


def _log_out(log: RecognitionLog) -> dict:
    return {
        "id": log.id,
        "camera_account": log.camera_account_id,
        "camera_username": log.camera_account.username if log.camera_account else None,
        "person": log.person_id,
        "person_name": log.person.full_name if log.person else None,
        "unknown_face": log.unknown_face,
        "confidence": log.confidence,
        "model_name": log.model_name or "EfficientNet-Lite0",
        "processing_time_ms": float(log.processing_time_ms or 0.0),
        "average_fps": float(log.average_fps or 0.0),
        "energy_consumption_wh": float(log.energy_consumption_wh or 0.0),
        "timestamp": _utc_isoformat(log.timestamp),
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
    model_name = _normalize_model_name(body.model_name)

    try:
        started_at = perf_counter()
        result = recognize_face_image(image_bytes, threshold, model_name)
        result_model_name = _normalize_model_name(result.get("model_key", model_name))
        metrics = _model_metrics(result_model_name, perf_counter() - started_at)
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
    elif float(result.get("score", 0.0)) > 0:
        message = "Точность ниже порога"

    effective_accuracy = float(result.get("accuracy", 0.0)) if person else 0.0
    log = None
    if body.save_log:
        log = RecognitionLog(
            camera_account_id=camera.id,
            person_id=person.id if person else None,
            unknown_face=not bool(person),
            confidence=effective_accuracy,
            **metrics,
        )
        db.add(log)
        db.commit()
        db.refresh(log)

    return {
        "log": _log_out(log) if log else None,
        "recognized": bool(person),
        "person_name": person.full_name if person else None,
        "accuracy": effective_accuracy,
        "threshold": round(threshold * 100, 1),
        "similarity": float(result.get("score", 0.0)),
        "detection_confidence": float(result.get("detection_confidence", 0.0)),
        "model_name": metrics["model_name"],
        "processing_time_ms": metrics["processing_time_ms"],
        "average_fps": metrics["average_fps"],
        "energy_consumption_wh": metrics["energy_consumption_wh"],
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
        model_name=body.model_name or "EfficientNet-Lite0",
        processing_time_ms=body.processing_time_ms or 0.0,
        average_fps=body.average_fps or 0.0,
        energy_consumption_wh=body.energy_consumption_wh or 0.0,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return _log_out(log)
