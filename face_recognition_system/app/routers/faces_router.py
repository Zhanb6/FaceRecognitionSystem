"""
Faces router — CRUD for PersonFace, mirrors PersonFaceViewSet.
"""
import base64
import binascii
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import BASE_DIR, get_db
from ..facenet_bridge import FaceEnrollmentError, FaceNetDependencyError, enroll_face_image
from ..models import CustomUser, FaceEnrollment, PersonFace
from ..schemas import FaceEnrollmentRequest, PersonFaceCreate, PersonFaceUpdate
from ..auth import get_current_user
from ..utils import is_super_admin, can_manage_faces, log_action

router = APIRouter()
FACE_ENROLLMENT_DIR = BASE_DIR / "media" / "face_enrollments"
logger = logging.getLogger(__name__)


def _face_out(face: PersonFace) -> dict:
    """Serialise a PersonFace to match the DRF format the frontend expects."""
    return {
        "id": face.id,
        "owner": face.owner_id,
        "company": face.company_id,
        "full_name": face.full_name,
        "role": face.role,
        "created_at": face.created_at.isoformat() if face.created_at else None,
        "allowed_cameras": [cam.id for cam in face.allowed_cameras],
    }


def _get_faces_queryset(user: CustomUser, db: Session):
    """Return the queryset of faces visible to the user."""
    if is_super_admin(user):
        return db.query(PersonFace).order_by(PersonFace.created_at.desc()).all()

    if user.is_camera:
        return (
            db.query(PersonFace)
            .filter(PersonFace.allowed_cameras.any(CustomUser.id == user.id))
            .filter(PersonFace.company_id == user.company_id)
            .order_by(PersonFace.created_at.desc())
            .all()
        )

    return (
        db.query(PersonFace)
        .filter(PersonFace.company_id == user.company_id)
        .order_by(PersonFace.created_at.desc())
        .all()
    )


def _can_access_face(user: CustomUser, face: PersonFace) -> bool:
    if is_super_admin(user):
        return True
    if user.is_camera:
        return face.company_id == user.company_id and user in face.allowed_cameras
    return face.company_id == user.company_id


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


@router.get("/all_faces/")
def all_faces(
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    faces = _get_faces_queryset(current_user, db)
    return [_face_out(f) for f in faces]


@router.get("/")
def list_faces(
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    faces = _get_faces_queryset(current_user, db)
    return [_face_out(f) for f in faces]


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_face(
    body: PersonFaceCreate,
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not can_manage_faces(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions to create faces")

    face = PersonFace(
        full_name=body.full_name,
        role=body.role,
        owner_id=current_user.id,
        company_id=current_user.company_id,
    )
    db.add(face)
    db.commit()
    db.refresh(face)

    # Link cameras
    if body.allowed_cameras:
        for cam_id in body.allowed_cameras:
            cam = db.query(CustomUser).filter(CustomUser.id == cam_id, CustomUser.is_camera.is_(True)).first()
            if cam:
                face.allowed_cameras.append(cam)

    log_action(db, current_user, "Создание профиля", f"Создан профиль: **{face.full_name}**")

    if current_user.is_camera:
        face.allowed_cameras.append(current_user)
        log_action(db, current_user, "Привязка к камере",
                   f"Профиль **{face.full_name}** привязан к **{current_user.username}**")

    db.commit()
    db.refresh(face)
    return _face_out(face)


@router.get("/{face_id}/")
def get_face(
    face_id: int,
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    face = db.query(PersonFace).filter(PersonFace.id == face_id).first()
    if not face:
        raise HTTPException(status_code=404, detail="Not found.")
    if not _can_access_face(current_user, face):
        raise HTTPException(status_code=403, detail="Forbidden for this company")
    return _face_out(face)


@router.post("/{face_id}/face-id")
@router.post("/{face_id}/face-id/")
def enroll_face_id(
    face_id: int,
    body: FaceEnrollmentRequest,
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not can_manage_faces(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions to enroll Face ID")

    face = db.query(PersonFace).filter(PersonFace.id == face_id).first()
    if not face:
        raise HTTPException(status_code=404, detail="Not found.")
    if not _can_access_face(current_user, face):
        raise HTTPException(status_code=403, detail="Forbidden for this company")

    image_bytes = _decode_image_data(body.image_data)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    person_dir = FACE_ENROLLMENT_DIR / str(face.id)
    person_dir.mkdir(parents=True, exist_ok=True)
    image_path = person_dir / f"{timestamp}.jpg"
    image_path.write_bytes(image_bytes)

    embedding_key = f"personface:{face.id}:{face.full_name}"
    try:
        result = enroll_face_image(embedding_key, image_bytes)
    except FaceNetDependencyError as exc:
        image_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=503,
            detail=f"FaceNet dependencies are not installed: {exc}",
        ) from exc
    except FaceEnrollmentError as exc:
        image_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Could not enroll Face ID for person %s", face.id)
        image_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Could not enroll Face ID") from exc

    enrollment = FaceEnrollment(
        person_id=face.id,
        image_path=str(image_path.relative_to(BASE_DIR)),
        embedding_key=embedding_key,
        detection_confidence=float(result.get("confidence", 0.0)),
    )
    db.add(enrollment)
    log_action(db, current_user, "Face ID", f"Добавлен Face ID для **{face.full_name}**")
    db.commit()
    db.refresh(enrollment)

    return {
        "message": "Face ID сохранен",
        "id": enrollment.id,
        "person": face.id,
        "image_path": enrollment.image_path,
        "embedding_key": enrollment.embedding_key,
        "detection_confidence": enrollment.detection_confidence,
        "samples": result.get("samples", 0),
    }


@router.api_route("/{face_id}/", methods=["PUT", "PATCH"])
def update_face(
    face_id: int,
    body: PersonFaceUpdate,
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not can_manage_faces(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions to update faces")

    face = db.query(PersonFace).filter(PersonFace.id == face_id).first()
    if not face:
        raise HTTPException(status_code=404, detail="Not found.")
    if not _can_access_face(current_user, face):
        raise HTTPException(status_code=403, detail="Forbidden for this company")

    old_name = face.full_name
    if body.full_name is not None:
        face.full_name = body.full_name
    if body.role is not None:
        face.role = body.role
    if body.allowed_cameras is not None:
        face.allowed_cameras.clear()
        for cam_id in body.allowed_cameras:
            cam = db.query(CustomUser).filter(CustomUser.id == cam_id, CustomUser.is_camera.is_(True)).first()
            if cam:
                face.allowed_cameras.append(cam)

    db.commit()
    db.refresh(face)
    log_action(db, current_user, "Изменение профиля",
               f"Профиль **{old_name}** обновлен. Новое ФИО: **{face.full_name}**, роль: {face.role}")
    return _face_out(face)


@router.delete("/{face_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_face(
    face_id: int,
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not can_manage_faces(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions to delete faces")

    face = db.query(PersonFace).filter(PersonFace.id == face_id).first()
    if not face:
        raise HTTPException(status_code=404, detail="Not found.")
    if not _can_access_face(current_user, face):
        raise HTTPException(status_code=403, detail="Forbidden for this company")

    name = face.full_name
    db.delete(face)
    db.commit()
    log_action(db, current_user, "Удаление профиля", f"Удален профиль: **{name}**")
