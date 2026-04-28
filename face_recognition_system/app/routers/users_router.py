"""
Users router — company users, admin users, create company admin / user.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CustomUser, Company, RoleEnum
from ..schemas import CreateAdminRequest, CreateCompanyAdminRequest, CreateCompanyUserRequest
from ..auth import get_current_user, hash_password
from ..utils import is_super_admin, is_company_admin, get_request_company, log_action

router = APIRouter()


def _user_out(user: CustomUser) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_staff": user.is_staff,
        "is_camera": user.is_camera,
        "role": user.role.value if user.role else "user",
        "company": user.company_id,
        "company_name": user.company.name if user.company else None,
    }


# ── Company Users ────────────────────────────────────────────────────────────
@router.get("/users/")
def list_company_users(
    company_id: Optional[int] = None,
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not (is_company_admin(current_user) or is_super_admin(current_user)):
        raise HTTPException(status_code=403, detail="Company Admin permission required")

    company = get_request_company(current_user, company_id, db)
    if not company:
        raise HTTPException(status_code=400, detail="Company is required")

    users = (
        db.query(CustomUser)
        .filter(
            CustomUser.company_id == company.id,
            CustomUser.is_camera.is_(False),
            CustomUser.role != RoleEnum.SUPERADMIN,
        )
        .order_by(CustomUser.date_joined)
        .all()
    )
    return [_user_out(u) for u in users]


@router.post("/users/create/", status_code=status.HTTP_201_CREATED)
def create_company_user(
    body: CreateCompanyUserRequest,
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not (is_company_admin(current_user) or is_super_admin(current_user)):
        raise HTTPException(status_code=403, detail="Company Admin permission required")

    company = get_request_company(current_user, body.company_id, db)
    if not company:
        raise HTTPException(status_code=400, detail="Company is required")

    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    if db.query(CustomUser).filter(CustomUser.username == body.username).first():
        raise HTTPException(status_code=400, detail="This username is already taken")

    email = body.email or f"{body.username}@user.system"

    user = CustomUser(
        username=body.username,
        email=email,
        hashed_password=hash_password(body.password),
        is_staff=False,
        is_camera=False,
        role=RoleEnum.USER,
        company_id=company.id,
        owner_id=current_user.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_action(db, current_user, "Создание пользователя",
               f"Создан пользователь **{body.username}** для компании **{company.name}**")

    return {
        "message": "Company user created",
        "user_id": user.id,
        "username": user.username,
        "company_id": company.id,
    }


# ── Admin Users (Super Admin) ───────────────────────────────────────────────
@router.get("/admin-users/")
def list_admin_users(
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin permission required")

    admins = (
        db.query(CustomUser)
        .filter(CustomUser.role == RoleEnum.ADMIN)
        .order_by(CustomUser.date_joined.desc())
        .all()
    )
    return [_user_out(a) for a in admins]


@router.post("/admin-users/", status_code=status.HTTP_201_CREATED)
def create_admin_user(
    body: CreateAdminRequest,
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin permission required")

    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="username and password are required")

    if db.query(CustomUser).filter(CustomUser.username == body.username).first():
        raise HTTPException(status_code=400, detail="Username is already taken")

    email = body.email or f"{body.username}@company.system"

    base_company_name = body.company_name or f"{body.username} Company"
    final_company_name = base_company_name
    suffix = 1
    while db.query(Company).filter(Company.name == final_company_name).first():
        suffix += 1
        final_company_name = f"{base_company_name} {suffix}"

    company = Company(name=final_company_name)
    db.add(company)
    db.commit()
    db.refresh(company)

    admin_user = CustomUser(
        username=body.username,
        email=email,
        hashed_password=hash_password(body.password),
        is_staff=True,
        is_camera=False,
        role=RoleEnum.ADMIN,
        company_id=company.id,
        owner_id=current_user.id,
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    log_action(db, current_user, "Создание заявки",
               f"Создан администратор **{admin_user.username}** для компании **{company.name}**")

    return {
        "message": "Admin account created",
        "admin": _user_out(admin_user),
    }


# ── Company Admin creation ───────────────────────────────────────────────────
@router.post("/company-admins/create/", status_code=status.HTTP_201_CREATED)
def create_company_admin(
    body: CreateCompanyAdminRequest,
    current_user: CustomUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin permission required")

    if not body.company_name or not body.username or not body.password:
        raise HTTPException(status_code=400, detail="company_name, username and password are required")

    if db.query(CustomUser).filter(CustomUser.username == body.username).first():
        raise HTTPException(status_code=400, detail="Username is already taken")

    if db.query(Company).filter(Company.name == body.company_name).first():
        raise HTTPException(status_code=400, detail="Company already exists")

    email = body.email or f"{body.username}@company.system"

    company = Company(name=body.company_name)
    db.add(company)
    db.commit()
    db.refresh(company)

    admin_user = CustomUser(
        username=body.username,
        email=email,
        hashed_password=hash_password(body.password),
        is_staff=True,
        is_camera=False,
        role=RoleEnum.ADMIN,
        company_id=company.id,
        owner_id=current_user.id,
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    log_action(db, current_user, "Создание администратора компании",
               f"Компания **{company.name}**, администратор **{admin_user.username}**")

    return {
        "message": "Company admin created",
        "company_id": company.id,
        "company_name": company.name,
        "admin_id": admin_user.id,
        "admin_username": admin_user.username,
    }
