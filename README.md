## DiplomaProjectAITU — Face Recognition System

### Структура

- `face_recognition_system/` — backend на **FastAPI**
  - `app/` — приложение FastAPI (роуты, модели, auth)
  - `requirements.txt` — зависимости backend
  - `create_superuser.py` — создание суперпользователя
- `face_recognition_system/frontend/` — frontend на **React + Vite**
- `docker-compose.yml` — запуск сайта целиком (frontend + backend)

### Запуск через Docker (рекомендуется)

```bash
docker compose up --build
```

- Frontend: `http://127.0.0.1:5173/`
- Backend API: `http://127.0.0.1:8000/`
- Swagger: `http://127.0.0.1:8000/docs`

Frontend обращается к API по `/api/...` через Vite proxy.

### Локальный запуск (без Docker)

Backend:

```bash
cd face_recognition_system
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd face_recognition_system/frontend
npm install
npm run dev
```

Открыть: `http://127.0.0.1:5173/`

# Auth Setup Guide

## 1. Install dependencies

```bash
pip install djangorestframework djangorestframework-simplejwt django-cors-headers
```

## 2. Create the accounts app (if not yet)

```bash
python manage.py startapp accounts
```

## 3. Copy files into your project

```
accounts/
  models.py        ← Custom user model
  serializers.py   ← Register + Login serializers
  views.py         ← API views
  urls.py          ← Auth URL routes
```

## 4. Update settings.py

Copy everything from `settings_additions.py` into your `core/settings.py`.

## 5. Update core/urls.py

```python
path("api/auth/", include("accounts.urls")),
```

## 6. Run migrations

```bash
python manage.py makemigrations accounts
python manage.py migrate
```

## 7. Create a superuser (optional)

```bash
python manage.py createsuperuser
```

---

## API Endpoints

| Method | URL                        | Auth?  | Description                        |
|--------|----------------------------|--------|------------------------------------|
| POST   | /api/auth/register/        | No     | Register new user                  |
| POST   | /api/auth/login/           | No     | Login (username OR email)          |
| POST   | /api/auth/token/refresh/   | No     | Refresh access token               |
| GET    | /api/auth/profile/         | Yes    | Get current user info              |

---

## Request / Response Examples

### Register
```json
POST /api/auth/register/
{
  "username": "john",
  "email": "john@example.com",
  "password": "securepass123",
  "password_confirm": "securepass123"
}

Response 201:
{
  "message": "Registration successful.",
  "user": { "id": 1, "username": "john", "email": "john@example.com" },
  "tokens": { "access": "...", "refresh": "..." },
  "redirect": "/dashboard"
}
```

### Login (username or email)
```json
POST /api/auth/login/
{
  "login": "john",         // ← username OR email
  "password": "securepass123"
}

Response 200:
{
  "message": "Login successful.",
  "user": { ... },
  "tokens": { "access": "...", "refresh": "..." },
  "redirect": "/dashboard"
}
```

### Using the access token
```
Authorization: Bearer <access_token>
```

---

## Frontend Usage (React example)

```js
// Login
const res = await fetch('/api/auth/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ login: username, password })
});
const data = await res.json();
localStorage.setItem('access', data.tokens.access);
localStorage.setItem('refresh', data.tokens.refresh);
navigate(data.redirect);  // redirect to /dashboard

// Authenticated request
const profile = await fetch('/api/auth/profile/', {
  headers: { Authorization: `Bearer ${localStorage.getItem('access')}` }
});
```