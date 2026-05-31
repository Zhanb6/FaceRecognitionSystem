"""
Cameras router — list, create, manage faces on cameras.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditLog, CustomUser, PersonFace, RecognitionLog, RoleEnum
from ..schemas import CameraCreate, AddRemoveFaceRequest
from ..auth import get_current_user, hash_password
from ..utils import is_super_admin, is_company_admin, get_request_company, log_action

router = APIRouter()


def _face_out(face: PersonFace) -> dict:
    return {
        "id": face.id,
        "owner": face.owner_id,
        "company": face.company_id,
        "full_name": face.full_name,
        "role": face.role,
        "created_at": face.created_at.isoformat() if face.created_at else None,
        "allowed_cameras": [cam.id for cam in face.allowed_cameras],
    }


def _get_manageable_camera(camera_id: int, current_user: CustomUser, db: Session) -> CustomUser:
    if not (is_company_admin(current_user) or is_super_admin(current_user)):
        raise HTTPException(status_code=403, detail="Admin permission required")

    camera = db.query(CustomUser).filter(CustomUser.id == camera_id, CustomUser.is_camera.is_(True)).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    if not is_super_admin(current_user) and camera.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Forbidden for this company")

    return camera


@router.get("/")
def list_cameras(
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if is_super_admin(current_user):
        cameras = db.query(CustomUser).filter(CustomUser.is_camera.is_(True)).all()
    else:
        cameras = (
            db.query(CustomUser)
            .filter(CustomUser.company_id == current_user.company_id, CustomUser.is_camera.is_(True))
            .all()
        )

    return [
        {
            "id": c.id,
            "username": c.username,
            "is_active": c.is_active,
            "date_joined": c.date_joined.isoformat() if c.date_joined else None,
            "company_id": c.company_id,
            "owner_id": c.owner_id,
            "owner__username": c.owner.username if c.owner else None,
        }
        for c in cameras
    ]


@router.post("/create/", status_code=status.HTTP_201_CREATED)
def create_camera(
    body: CameraCreate,
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not (is_company_admin(current_user) or is_super_admin(current_user)):
        raise HTTPException(status_code=403, detail="Admin permission required")

    company = get_request_company(current_user, body.company_id, db)
    if not company:
        raise HTTPException(status_code=400, detail="Company is required")

    email = body.email or f"{body.username}@camera.system"

    if not body.username:
        raise HTTPException(status_code=400, detail="Camera name is required")

    if db.query(CustomUser).filter(CustomUser.username == body.username).first():
        raise HTTPException(status_code=400, detail="This camera name is already taken")

    camera = CustomUser(
        username=body.username,
        email=email,
        hashed_password=hash_password(f"camera-account:{body.username}"),
        is_camera=True,
        is_staff=False,
        role=RoleEnum.CAMERA,
        company_id=company.id,
        owner_id=current_user.id,
    )
    db.add(camera)
    db.commit()
    db.refresh(camera)

    log_action(db, current_user, "Создание камеры",
               f"Создана камера: **{body.username}** (компания: **{company.name}**) ")

    return {
        "message": "Camera account created",
        "camera_id": camera.id,
        "username": camera.username,
        "company_id": company.id,
    }


@router.patch("/{camera_id}/active/")
def toggle_camera_active(
    camera_id: int,
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    camera = _get_manageable_camera(camera_id, current_user, db)
    camera.is_active = not camera.is_active
    db.commit()
    db.refresh(camera)

    action = "Активация камеры" if camera.is_active else "Деактивация камеры"
    status_text = "активирована" if camera.is_active else "деактивирована"
    log_action(db, current_user, action, f"Камера **{camera.username}** {status_text}")

    return {
        "message": f"Camera {status_text}",
        "camera_id": camera.id,
        "is_active": camera.is_active,
    }


@router.delete("/{camera_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_camera(
    camera_id: int,
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    camera = _get_manageable_camera(camera_id, current_user, db)
    camera_name = camera.username

    camera.faces.clear()
    db.query(AuditLog).filter(AuditLog.user_id == camera.id).delete(synchronize_session=False)
    db.query(RecognitionLog).filter(RecognitionLog.camera_account_id == camera.id).delete(synchronize_session=False)
    db.query(PersonFace).filter(PersonFace.owner_id == camera.id).update(
        {PersonFace.owner_id: None},
        synchronize_session=False,
    )
    db.query(CustomUser).filter(CustomUser.owner_id == camera.id).update(
        {CustomUser.owner_id: None},
        synchronize_session=False,
    )
    db.delete(camera)
    db.commit()

    log_action(db, current_user, "Удаление камеры", f"Удалена камера: **{camera_name}**")


@router.get("/{camera_id}/faces/")
def camera_faces(
    camera_id: int,
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    camera = db.query(CustomUser).filter(CustomUser.id == camera_id, CustomUser.is_camera.is_(True)).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    if not is_super_admin(current_user) and camera.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Forbidden for this company")

    faces = (
        db.query(PersonFace)
        .filter(PersonFace.allowed_cameras.any(CustomUser.id == camera_id))
        .filter(PersonFace.company_id == camera.company_id)
        .all()
    )
    return [_face_out(f) for f in faces]


@router.post("/{camera_id}/add_face/")
def camera_add_face(
    camera_id: int,
    body: AddRemoveFaceRequest,
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not (is_company_admin(current_user) or is_super_admin(current_user)):
        raise HTTPException(status_code=403, detail="Company Admin permission required")

    face = db.query(PersonFace).filter(PersonFace.id == body.face_id).first()
    if not face:
        raise HTTPException(status_code=404, detail="Face not found")

    camera = db.query(CustomUser).filter(CustomUser.id == camera_id, CustomUser.is_camera.is_(True)).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    if camera.company_id != face.company_id:
        raise HTTPException(status_code=400, detail="Face and camera belong to different companies")

    if not is_super_admin(current_user) and camera.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Forbidden for this company")

    if camera not in face.allowed_cameras:
        face.allowed_cameras.append(camera)
    db.commit()

    log_action(db, current_user, "Добавление в группу",
               f"Пользователь **{face.full_name}** добавлен в камеру **{camera.username}**")
    return {"message": "Face added to camera successfully"}


@router.post("/{camera_id}/remove_face/")
def camera_remove_face(
    camera_id: int,
    body: AddRemoveFaceRequest,
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not (is_company_admin(current_user) or is_super_admin(current_user)):
        raise HTTPException(status_code=403, detail="Company Admin permission required")

    face = db.query(PersonFace).filter(PersonFace.id == body.face_id).first()
    if not face:
        raise HTTPException(status_code=404, detail="Face not found")

    camera = db.query(CustomUser).filter(CustomUser.id == camera_id, CustomUser.is_camera.is_(True)).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    if not is_super_admin(current_user) and camera.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Forbidden for this company")

    if camera in face.allowed_cameras:
        face.allowed_cameras.remove(camera)
        db.commit()

    log_action(db, current_user, "Удаление из группы",
               f"Пользователь **{face.full_name}** удален из камеры **{camera.username}**")
    return {"message": "Face removed from camera successfully"}
