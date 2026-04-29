"""
SQLAlchemy ORM models — mirrors the original Django models exactly.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Boolean, Float, Text, DateTime,
    ForeignKey, Enum, Table,
)
from sqlalchemy.orm import relationship

from .database import Base


# ── Many-to-many: PersonFace ↔ Camera (CustomUser) ──────────────────────────
person_face_cameras = Table(
    "person_face_cameras",
    Base.metadata,
    Column("personface_id", Integer, ForeignKey("person_faces.id"), primary_key=True),
    Column("camera_id", Integer, ForeignKey("users.id"), primary_key=True),
)


class RoleEnum(str, enum.Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    USER = "user"
    CAMERA = "camera"


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    users = relationship("CustomUser", back_populates="company")
    faces = relationship("PersonFace", back_populates="company")


class CustomUser(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(50), default="")
    last_name = Column(String(50), default="")
    role = Column(Enum(RoleEnum), default=RoleEnum.USER)
    is_active = Column(Boolean, default=True)
    is_staff = Column(Boolean, default=False)
    is_camera = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    date_joined = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="users")
    owner = relationship("CustomUser", remote_side=[id], backref="owned_cameras")
    owned_faces = relationship("PersonFace", back_populates="owner", foreign_keys="PersonFace.owner_id")
    logs = relationship("RecognitionLog", back_populates="camera_account")
    audit_logs = relationship("AuditLog", back_populates="user")

    # faces linked through M2M (camera side)
    faces = relationship("PersonFace", secondary=person_face_cameras, back_populates="allowed_cameras")


class PersonFace(Base):
    __tablename__ = "person_faces"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    full_name = Column(String(255), nullable=False)
    role = Column(String(100), default="Студент")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("CustomUser", back_populates="owned_faces", foreign_keys=[owner_id])
    company = relationship("Company", back_populates="faces")
    allowed_cameras = relationship("CustomUser", secondary=person_face_cameras, back_populates="faces")
    recognition_logs = relationship("RecognitionLog", back_populates="person")
    face_enrollments = relationship("FaceEnrollment", back_populates="person", cascade="all, delete-orphan")


class FaceEnrollment(Base):
    __tablename__ = "face_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("person_faces.id"), nullable=False)
    image_path = Column(String(500), nullable=False)
    embedding_key = Column(String(255), nullable=False)
    detection_confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    person = relationship("PersonFace", back_populates="face_enrollments")


class RecognitionLog(Base):
    __tablename__ = "recognition_logs"

    id = Column(Integer, primary_key=True, index=True)
    camera_account_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    person_id = Column(Integer, ForeignKey("person_faces.id"), nullable=True)
    unknown_face = Column(Boolean, default=False)
    confidence = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    camera_account = relationship("CustomUser", back_populates="logs")
    person = relationship("PersonFace", back_populates="recognition_logs")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(255), nullable=False)
    details = Column(Text, default="")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("CustomUser", back_populates="audit_logs")
