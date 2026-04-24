"""
Auth router — register, login, profile, token refresh.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CustomUser, RoleEnum
from ..schemas import RegisterRequest, LoginRequest, TokenRefreshRequest, UserOut, AuthResponse, TokenPair
from ..auth import hash_password, verify_password, get_tokens_for_user, decode_token, create_access_token, get_current_user
from ..utils import log_action

router = APIRouter()


def _user_out(user: CustomUser) -> dict:
    """Convert a user ORM object to a dict matching the frontend format."""
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


@router.post("/register/", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if body.password != body.password_confirm:
        raise HTTPException(status_code=400, detail={"password": ["Passwords do not match."]})

    if db.query(CustomUser).filter(CustomUser.username == body.username).first():
        raise HTTPException(status_code=400, detail={"username": ["A user with that username already exists."]})

    if db.query(CustomUser).filter(CustomUser.email == body.email).first():
        raise HTTPException(status_code=400, detail={"email": ["A user with that email already exists."]})

    user = CustomUser(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=RoleEnum.USER,
        is_staff=False,
        is_camera=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_action(db, user, "Регистрация", f"Пользователь **{user.username}** зарегистрирован")
    tokens = get_tokens_for_user(user.id)

    return {
        "message": "Registration successful.",
        "user": _user_out(user),
        "tokens": tokens,
    }


@router.post("/login/")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(CustomUser).filter(CustomUser.username == body.login).first()
    if not user:
        user = db.query(CustomUser).filter(CustomUser.email == body.login).first()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect Credentials")

    tokens = get_tokens_for_user(user.id)
    return {
        "message": "Login successful.",
        "user": _user_out(user),
        "tokens": tokens,
    }


@router.post("/token/refresh/")
def token_refresh(body: TokenRefreshRequest, db: Session = Depends(get_db)):
    user_id = decode_token(body.refresh, expected_type="refresh")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.query(CustomUser).filter(CustomUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {
        "access": create_access_token(user.id),
    }


@router.get("/profile/")
def profile(current_user: CustomUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return _user_out(current_user)
