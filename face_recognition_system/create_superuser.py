"""
Script to create a superuser for the FastAPI backend.
Usage:
    python create_superuser.py
"""
import sys
from getpass import getpass

from app.database import SessionLocal, engine, Base
from app.models import CustomUser, RoleEnum
from app.auth import hash_password

# Ensure tables exist
Base.metadata.create_all(bind=engine)

db = SessionLocal()

print("=== Create Superuser ===")
username = input("Username: ").strip()
if not username:
    print("Username is required.")
    sys.exit(1)

email = input("Email: ").strip()
if not email:
    email = f"{username}@admin.system"

password = getpass("Password: ")
if not password:
    print("Password is required.")
    sys.exit(1)

password_confirm = getpass("Confirm password: ")
if password != password_confirm:
    print("Passwords do not match.")
    sys.exit(1)

existing = db.query(CustomUser).filter(CustomUser.username == username).first()
if existing:
    print(f"User '{username}' already exists.")
    sys.exit(1)

user = CustomUser(
    username=username,
    email=email,
    hashed_password=hash_password(password),
    role=RoleEnum.SUPERADMIN,
    is_staff=True,
    is_superuser=True,
    is_active=True,
)
db.add(user)
db.commit()
db.refresh(user)
db.close()

print(f"Superuser '{username}' created successfully (id={user.id}).")
