"""
Faces router — CRUD for PersonFace, mirrors PersonFaceViewSet.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CustomUser, PersonFace, person_face_cameras
from ..schemas import PersonFaceCreate, PersonFaceUpdate, PersonFaceOut
from ..auth import get_current_user
from ..utils import is_super_admin, can_manage_faces, log_action

router = APIRouter()


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
            cam = db.query(CustomUser).filter(CustomUser.id == cam_id, CustomUser.is_camera == True).first()
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
    return _face_out(face)


@router.put("/{face_id}/")
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

    old_name = face.full_name
    if body.full_name is not None:
        face.full_name = body.full_name
    if body.role is not None:
        face.role = body.role
    if body.allowed_cameras is not None:
        face.allowed_cameras.clear()
        for cam_id in body.allowed_cameras:
            cam = db.query(CustomUser).filter(CustomUser.id == cam_id, CustomUser.is_camera == True).first()
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

    name = face.full_name
    db.delete(face)
    db.commit()
    log_action(db, current_user, "Удаление профиля", f"Удален профиль: **{name}**")
