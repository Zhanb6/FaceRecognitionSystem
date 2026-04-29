# Project Overview

## 1. Project Summary

DiplomaProjectAITU is a face-recognition administration system with a FastAPI backend and a React/Vite frontend. It supports JWT authentication, role-based dashboards, face profile management, camera accounts, recognition logs, and super-admin audit views.

Tech stack:
- Backend: Python 3, FastAPI 0.115.12, Uvicorn 0.32.1, SQLAlchemy 2.0.40, Pydantic 2.13.3, python-jose 3.3.0, bcrypt 4.2.1, SQLite.
- Frontend: React 19.2.4, React DOM 19.2.4, Vite 8.0.0, TypeScript 5.9.3, ESLint 9.39.4.
- Runtime/deployment: Docker Compose with separate backend and frontend services.

Directory structure:

```text
.
├── README.md
├── docker-compose.yml
└── face_recognition_system
    ├── Dockerfile
    ├── create_superuser.py
    ├── requirements.txt
    ├── app
    │   ├── __init__.py
    │   ├── auth.py
    │   ├── database.py
    │   ├── main.py
    │   ├── models.py
    │   ├── schemas.py
    │   ├── utils.py
    │   └── routers
    │       ├── __init__.py
    │       ├── audit_router.py
    │       ├── auth_router.py
    │       ├── cameras_router.py
    │       ├── faces_router.py
    │       ├── logs_router.py
    │       └── users_router.py
    └── frontend
        ├── Dockerfile
        ├── README.md
        ├── eslint.config.js
        ├── index.html
        ├── package-lock.json
        ├── package.json
        ├── tsconfig.app.json
        ├── tsconfig.json
        ├── tsconfig.node.json
        ├── vite.config.ts
        └── src
            ├── App.tsx
            ├── Dashboard.tsx
            ├── api.ts
            ├── index.css
            ├── main.tsx
            ├── types.ts
            └── assets
                └── aitu_logo.png
```

## 2. Architecture

The backend is a FastAPI application in `face_recognition_system/app/main.py`. It creates SQLite tables on startup and mounts routers under `/api/auth`, preserving a Django-like URL shape.

Backend layers:
- `database.py`: SQLAlchemy engine/session setup, fixed to `face_recognition_system/db.sqlite3`.
- `models.py`: ORM models for companies, users, face profiles, recognition logs, audit logs, and camera-to-face relationships.
- `schemas.py`: Pydantic request/response schemas.
- `auth.py`: password hashing, JWT creation/validation, and current-user dependency.
- `utils.py`: role helpers, company resolution, audit-log creation.
- `routers/auth_router.py`: registration, login, token refresh, profile.
- `routers/faces_router.py`: face profile CRUD.
- `routers/logs_router.py`: recognition log listing/creation.
- `routers/cameras_router.py`: camera account listing/creation and camera-face assignments.
- `routers/users_router.py`: company users, admin users, company admin creation.
- `routers/audit_router.py`: super-admin audit log listing.

The frontend entry point is `frontend/src/main.tsx`, which renders `App.tsx`. `App.tsx` handles login/registration and renders `Dashboard.tsx` once a token exists in `localStorage`. The dashboard fetches data from `/api/auth/...` through the Vite proxy and uses role flags from `user_data` to decide which navigation items and actions are visible.

Data flow:
- Login/register calls return JWT tokens and user data.
- Tokens and user data are stored in `localStorage`.
- Dashboard reads the access token and calls faces, logs, cameras, users, admin-users, and audit endpoints.
- User actions mutate backend state, then refresh dashboard data.

## 3. Known Issues (found during analysis)

- `frontend/src/Dashboard.tsx`: `+ Face ID` button is visible but has no handler or implemented feature.
- `frontend/src/Dashboard.tsx`: `Экспорт CSV` button is visible but has no handler.
- `frontend/src/Dashboard.tsx`: `Фильтр` button is visible but has no handler.
- `frontend/src/Dashboard.tsx`: camera `Просмотр логов` button is visible but has no handler.
- `frontend/src/Dashboard.tsx`: camera `Настройки` button is visible but has no handler.
- `frontend/src/Dashboard.tsx`: face update uses `PATCH /api/auth/faces/{id}/`, but the backend only exposes `PUT /api/auth/faces/{id}/`.
- `frontend/src/Dashboard.tsx`: raw `fetch` calls are scattered through the component instead of centralized API logic.
- `frontend/src/Dashboard.tsx`: async errors often only log to the console and do not show user-facing errors.
- `frontend/src/Dashboard.tsx`: data fetches do not use request cancellation on component unmount.
- `frontend/src/Dashboard.tsx`: `handleToggleCameraFaces` and `handleAddExistingFace` can leave loading flags active if the auth token is missing after state changes.
- `frontend/src/Dashboard.tsx`: ESLint fails on `Unexpected any` and a missing React hook dependency.
- `frontend/src/App.tsx`: ESLint fails on `Unexpected any` for stored user data.
- `frontend/src/App.tsx`: forgot-password action only calls an empty parent callback, so the button is a UI dead end.
- `frontend/src/App.tsx`: ECP auth step has an unimplemented certificate button, though the step is not reachable in the current UI.
- `frontend/src/App.tsx`: raw auth `fetch` calls are not centralized and do not use cancellation.
- `frontend/src/App.css`: contains unused default Vite template styles.
- `frontend/src/index.css`: contains default Vite template selectors and colors unrelated to the application.
- `app/auth.py`: JWT secret is hard-coded instead of coming from environment.
- `app/database.py`: SQLite database URL is hard-coded instead of configurable by environment.
- `app/routers/*.py`: several schema imports are unused.
- `app/routers/faces_router.py`: visibility checks are missing on individual get/update/delete operations, allowing cross-company access if the caller has a manageable role.
- `app/routers/cameras_router.py`: adding a face to a camera does not check whether the camera is actually a camera account and can append duplicates.
- `app/routers/logs_router.py`: any authenticated user can create recognition logs; intended behavior appears to be camera-only logging.
- `create_superuser.py`: the database session is not closed on early exits.
- `README.md`: includes a stale Django REST Framework authentication guide that does not match the FastAPI implementation.

Validation results before fixes:
- `npm run build`: passed.
- `npm run lint`: failed with two `no-explicit-any` errors and one hook dependency warning.
- `python3 -m compileall face_recognition_system/app face_recognition_system/create_superuser.py`: passed.

## 4. Dependencies & Environment

Required environment variables:
- `SECRET_KEY` is needed for production JWT signing but is currently not required because `app/auth.py` has an insecure fallback.
- `DATABASE_URL` is needed for configurable deployments but is currently not required because `app/database.py` defaults to local SQLite.
- `VITE_PROXY_TARGET` is optional for the frontend dev server and defaults to `http://127.0.0.1:8000`.

External services/APIs:
- No third-party runtime API integration is implemented.
- Frontend loads Google Fonts from `fonts.googleapis.com`.
- No NCALayer/ECP integration is implemented.

Setup instructions:

```bash
docker compose up --build
```

Backend only:

```bash
cd face_recognition_system
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend only:

```bash
cd face_recognition_system/frontend
npm install
npm run dev
```

Create a superuser:

```bash
cd face_recognition_system
python3 create_superuser.py
```

## 5. Change Log

- [frontend/src/types.ts] — added shared frontend data types to remove duplicated `any` usage.
- [frontend/src/api.ts] — centralized frontend API requests and error parsing.
- [frontend/src/api.ts] — made API response parsing tolerate non-JSON error bodies.
- [app/auth.py] — made the JWT secret configurable through `SECRET_KEY`.
- [app/database.py] — made the database connection configurable through `DATABASE_URL`.
- [app/routers/faces_router.py] — added per-face access checks, PATCH compatibility, and removed unused imports.
- [app/routers/cameras_router.py] — required camera accounts for camera-face actions, prevented duplicate links, and removed unused imports.
- [app/routers/logs_router.py] — restricted recognition-log creation to camera accounts.
- [app/routers/auth_router.py] — removed unused schema imports.
- [app/routers/users_router.py] — removed unused schema imports.
- [create_superuser.py] — ensured the database session closes on all exit paths.
- [frontend/src/App.tsx] — replaced raw auth fetches with the shared API helper, removed `any`, handled bad stored user data, disabled the unimplemented forgot-password action, and removed unreachable ECP UI.
- [frontend/src/Dashboard.tsx] — centralized API calls, added request cancellation for initial dashboard loading, surfaced async errors in the UI, fixed lint errors, implemented recognition CSV export/filter actions, fixed camera log navigation, and disabled unsupported Face ID/camera settings actions.
- [frontend/src/Dashboard.tsx] — fixed expired-token detection to use typed API status codes.
- [README.md] — removed stale Django setup instructions and aligned documented endpoints with the FastAPI app.
- [frontend/src/index.css] — replaced unused Vite template styles with minimal global app styles.
- [frontend/src/App.css] — removed unused Vite template CSS.
- [app/routers/cameras_router.py] — replaced SQLAlchemy boolean equality comparisons with `.is_(...)`.
- [app/routers/faces_router.py] — replaced SQLAlchemy boolean equality comparisons with `.is_(...)`.
- [app/routers/users_router.py] — replaced SQLAlchemy boolean equality comparisons with `.is_(...)`.
- [app/routers/users_router.py] — allowed superadmins without a company to list all non-camera company users instead of returning `Company is required`.
- [frontend/src/Dashboard.tsx] — made optional dashboard requests independent so a users-fetch error no longer blocks the administrators list.
- [frontend/src/Dashboard.tsx] — replaced hardcoded overview stats and activity bars with values derived from loaded faces, logs, cameras, and company users, falling back to zero when data is absent.
- [frontend/src/Dashboard.tsx] — implemented the dark-theme setting with persisted theme state and dashboard color variables.
- [db.sqlite3] — cleared all users and operational records, leaving only the `developer` superadmin account.
- [frontend/src/Dashboard.tsx] — split administrators into a separate `Администраторы` registry, moved administrator creation there, and returned `Камеры` to a dedicated camera registry.
- [frontend/src/Dashboard.tsx] — stopped loading the company-users registry for the `developer` superadmin so a missing company cannot show `Company is required`.
- [app/routers/users_router.py] — added a superadmin-only companies endpoint for real company counts.
- [frontend/src/types.ts] — added company and camera-account fields used by overview and camera-specific logs.
- [frontend/src/Dashboard.tsx] — showed company count for superadmin, filtered recognition logs by selected camera, and marked camera activation/deactivation as disabled future actions.
- [frontend/src/Dashboard.tsx] — made company-count loading non-blocking and added an admin-company fallback so stale backends do not show `Not Found`.
- [frontend/src/Dashboard.tsx] — fixed user edit role selection to preserve custom roles and allow changing to a new custom role.
- [frontend/src/Dashboard.tsx] — unified add/edit user role options so `Работник` is available in both forms.
- [frontend/src/Dashboard.tsx] — allowed creating users without camera access by removing the automatic first-camera assignment.
- [frontend/src/Dashboard.tsx] — changed the add-user role default to `-` and required an explicit role selection before saving.
- [frontend/src/Dashboard.tsx] — limited the company-account count to superadmins and added an inactive-user count for profiles without camera access.
- [frontend/src/Dashboard.tsx] — removed superadmin overview requests to `/api/auth/users/` and `/api/auth/companies/` to avoid stale-backend 400/404 console errors.
- [frontend/src/Dashboard.tsx] — removed the `Аккаунтов компании` overview card.
- [facenet_recognition.py] — exposed FaceNet enrollment from image bytes with returned sample count while keeping standalone webcam mode.
- [app/models.py] — added persistent Face ID enrollment records linked to each created user profile.
- [app/schemas.py] — added the request schema for browser-captured Face ID photos.
- [app/facenet_bridge.py] — connected the FastAPI backend to the root FaceNet recognition script and database file.
- [app/routers/faces_router.py] — added `/faces/{id}/face-id/` to save a user photo, create the FaceNet embedding, and record the enrollment.
- [requirements.txt] — documented FaceNet, Torch, OpenCV, NumPy, and Pillow runtime dependencies.
- [frontend/src/Dashboard.tsx] — connected the `+ Face ID` button to a camera capture modal and Face ID upload flow.
- [app/routers/faces_router.py] — added a no-trailing-slash Face ID route alias to avoid proxy slash mismatches.
- [frontend/src/Dashboard.tsx] — retries Face ID upload without the trailing slash when a proxy returns 404 for the slash variant.
- [app/facenet_bridge.py] — made FaceNet script lookup work from local, Docker, and explicit `FACENET_SCRIPT_PATH` environments.
- [face_recognition_system/facenet_recognition.py] — copied the FaceNet enrollment script into the backend package so Docker builds include it.
- [requirements.txt] — pinned Pillow to the `facenet-pytorch` compatible 10.2.x line.
- [Dockerfile] — switched the backend image to Python 3.11 and installed OpenCV runtime libraries for FaceNet dependencies.
- [requirements.txt] — added `httpx` so FastAPI/Starlette test tooling is available with the backend dependencies.
- [facenet_recognition.py] — added image-byte recognition against the FaceNet database with returned accuracy.
- [app/facenet_bridge.py] — exposed FaceNet recognition checks to FastAPI.
- [app/schemas.py] — added the recognition-check request schema.
- [app/routers/logs_router.py] — added `/logs/check/` to run AI recognition, resolve the matched profile, and write a recognition log.
- [frontend/src/types.ts] — added recognition-check response typing and camera usernames on log rows.
- [frontend/src/Dashboard.tsx] — added a `Проверить` camera modal in `Лог распознаваний` that shows the matched user and accuracy.
- [facenet_recognition.py] — made recognition threshold configurable per check instead of using only the hardcoded default.
- [app/routers/logs_router.py] — applied the requested confidence threshold and rejected matched users without access to the selected camera.
- [frontend/src/Dashboard.tsx] — sends the configured confidence threshold during recognition checks and shows permission-denied messages.
- [app/models.py] — added `person_name` to Face ID enrollment records so saved photos are linked to both ID and full name.
- [app/routers/faces_router.py] — stores and returns the full user name for every new Face ID enrollment.
- [app/migrations.py] — added a lightweight SQLite schema update that backfills existing Face ID enrollments with profile names.
- [app/main.py] — runs lightweight schema updates after table creation on startup.
- [facenet_recognition.py] — added deletion of FaceNet embedding records by `personface:{id}:` prefix.
- [app/facenet_bridge.py] — exposed FaceNet embedding deletion to FastAPI.
- [app/routers/faces_router.py] — strengthened `DELETE /faces/{id}/` to remove Face ID photos, FaceNet embeddings, camera links, and recognition-log person references.
- [app/routers/logs_router.py] — added `GET /logs/{id}/` and `DELETE /logs/{id}/` with company-scoped access and delete checks.
- [README.md] — documented the recognition-log deletion endpoint.
- [app/routers/logs_router.py] — added `DELETE /logs/` for deleting all visible recognition logs with superadmin/company-admin scoping.
- [README.md] — documented bulk recognition-log deletion.
