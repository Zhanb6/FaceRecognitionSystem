"""
Pydantic schemas — replace Django REST Framework serializers.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


# ── Auth ─────────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    password_confirm: str


class LoginRequest(BaseModel):
    login: str
    password: Optional[str] = None


class TokenRefreshRequest(BaseModel):
    refresh: str


class TokenPair(BaseModel):
    refresh: str
    access: str


# ── User ─────────────────────────────────────────────────────────────────────
class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_staff: bool
    is_camera: bool
    role: str
    company: Optional[int] = None
    company_name: Optional[str] = None

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    message: str
    user: UserOut
    tokens: TokenPair


# ── PersonFace ───────────────────────────────────────────────────────────────
class PersonFaceCreate(BaseModel):
    full_name: str
    role: str = "Студент"
    allowed_cameras: list[int] = []


class PersonFaceUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    allowed_cameras: Optional[list[int]] = None


class PersonFaceOut(BaseModel):
    id: int
    owner: Optional[int] = None
    company: Optional[int] = None
    full_name: str
    role: str
    created_at: datetime
    allowed_cameras: list[int] = []

    model_config = {"from_attributes": True}


class FaceEnrollmentRequest(BaseModel):
    image_data: str


# ── RecognitionLog ───────────────────────────────────────────────────────────
class RecognitionLogCreate(BaseModel):
    person: Optional[int] = None
    unknown_face: bool = False
    confidence: float = 0.0
    model_name: Optional[str] = None
    processing_time_ms: Optional[float] = None
    average_fps: Optional[float] = None
    energy_consumption_wh: Optional[float] = None


class RecognitionCheckRequest(BaseModel):
    image_data: str
    camera_id: Optional[int] = None
    threshold: float =50.0
    model_name: Optional[str] = None
    save_log: bool = True


class RecognitionLogOut(BaseModel):
    id: int
    camera_account: int
    person: Optional[int] = None
    person_name: Optional[str] = None
    unknown_face: bool
    confidence: float
    model_name: Optional[str] = None
    processing_time_ms: float = 0.0
    average_fps: float = 0.0
    energy_consumption_wh: float = 0.0
    timestamp: datetime

    model_config = {"from_attributes": True}


# ── AuditLog ─────────────────────────────────────────────────────────────────
class AuditLogOut(BaseModel):
    id: int
    user: int
    username: Optional[str] = None
    action: str
    details: str
    timestamp: datetime

    model_config = {"from_attributes": True}


# ── Camera ───────────────────────────────────────────────────────────────────
class CameraCreate(BaseModel):
    username: str
    password: Optional[str] = None
    email: Optional[str] = None
    company_id: Optional[int] = None


class CameraOut(BaseModel):
    id: int
    username: str
    is_active: bool
    date_joined: datetime
    company_id: Optional[int] = None
    owner_id: Optional[int] = None
    owner__username: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Company Admin / User creation ────────────────────────────────────────────
class CreateAdminRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    company_name: Optional[str] = None
    company_id: Optional[int] = None


class CreateCompanyAdminRequest(BaseModel):
    company_name: str
    username: str
    password: str
    email: Optional[str] = None


class CreateCompanyUserRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    company_id: Optional[int] = None


class AddRemoveFaceRequest(BaseModel):
    face_id: int
