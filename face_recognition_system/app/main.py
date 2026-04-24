"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .routers import auth_router, faces_router, logs_router, cameras_router, users_router, audit_router

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Face Recognition System API",
    description="FastAPI backend for the Face Recognition System (AITU Diploma Project)",
    version="2.0.0",
)

# ── CORS — same origins as the original Django config ────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://frontend:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount routers under /api/auth — matching original Django URL structure ───
app.include_router(auth_router.router,   prefix="/api/auth",           tags=["Auth"])
app.include_router(faces_router.router,  prefix="/api/auth/faces",     tags=["Faces"])
app.include_router(logs_router.router,   prefix="/api/auth/logs",      tags=["Logs"])
app.include_router(cameras_router.router,prefix="/api/auth/cameras",   tags=["Cameras"])
app.include_router(users_router.router,  prefix="/api/auth",           tags=["Users"])
app.include_router(audit_router.router,  prefix="/api/auth/audit-logs",tags=["Audit Logs"])


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "Face Recognition System API"}
