"""
Utility / helper functions — replaces Django view helpers.
"""
from typing import Optional

from sqlalchemy.orm import Session

from .models import AuditLog, CustomUser, Company, RoleEnum


def log_action(db: Session, user: CustomUser, action: str, details: str = "") -> None:
    """Create an audit-log entry."""
    entry = AuditLog(user_id=user.id, action=action, details=details)
    db.add(entry)
    db.commit()


def is_super_admin(user: CustomUser) -> bool:
    return bool(
        user.is_superuser
        or user.role == RoleEnum.SUPERADMIN
        or user.username == "developer"
    )


def is_company_admin(user: CustomUser) -> bool:
    return user.role == RoleEnum.ADMIN


def get_request_company(user: CustomUser, company_id: Optional[int], db: Session) -> Optional[Company]:
    """Resolve the company for the current request."""
    if not is_super_admin(user):
        return user.company

    if company_id:
        return db.query(Company).filter(Company.id == company_id).first()
    return user.company


def can_manage_faces(user: CustomUser) -> bool:
    return bool(is_super_admin(user) or is_company_admin(user) or user.is_camera)
