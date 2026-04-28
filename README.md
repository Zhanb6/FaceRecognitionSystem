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

### Создание суперпользователя

```bash
cd face_recognition_system
python3 create_superuser.py
```

В production задайте `SECRET_KEY` и, при необходимости, `DATABASE_URL`.

---

## API Endpoints

| Method | URL                        | Auth?  | Description                        |
|--------|----------------------------|--------|------------------------------------|
| POST   | /api/auth/register/        | No     | Register new user                  |
| POST   | /api/auth/login/           | No     | Login (username OR email)          |
| POST   | /api/auth/token/refresh/   | No     | Refresh access token               |
| GET    | /api/auth/profile/         | Yes    | Get current user info              |
| GET    | /api/auth/faces/all_faces/ | Yes    | List visible face profiles         |
| POST   | /api/auth/faces/           | Yes    | Create a face profile              |
| PATCH  | /api/auth/faces/{id}/      | Yes    | Update a face profile              |
| DELETE | /api/auth/faces/{id}/      | Yes    | Delete a face profile              |
| GET    | /api/auth/cameras/         | Yes    | List camera accounts               |
| POST   | /api/auth/cameras/create/  | Yes    | Create a camera account            |

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
  "user": {
    "id": 1,
    "username": "john",
    "email": "john@example.com",
    "is_staff": false,
    "is_camera": false,
    "role": "user",
    "company": null,
    "company_name": null
  },
  "tokens": { "access": "...", "refresh": "..." }
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
  "tokens": { "access": "...", "refresh": "..." }
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
localStorage.setItem('user_data', JSON.stringify(data.user));

// Authenticated request
const profile = await fetch('/api/auth/profile/', {
  headers: { Authorization: `Bearer ${localStorage.getItem('access')}` }
});
```
