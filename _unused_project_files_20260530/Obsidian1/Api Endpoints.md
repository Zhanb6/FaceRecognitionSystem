# API Endpoints

Основные API endpoints проекта.

## Auth

| Method | URL | Описание |
|---|---|---|
| POST | `/api/auth/register/` | Регистрация пользователя |
| POST | `/api/auth/login/` | Вход в систему |
| POST | `/api/auth/token/refresh/` | Обновление access token |
| GET | `/api/auth/profile/` | Получение профиля текущего пользователя |

## Faces

| Method | URL | Описание |
|---|---|---|
| GET | `/api/auth/faces/all_faces/` | Список пользователей/лиц |
| POST | `/api/auth/faces/` | Создание профиля лица |
| PATCH | `/api/auth/faces/{id}/` | Изменение профиля |
| DELETE | `/api/auth/faces/{id}/` | Удаление профиля |
| POST | `/api/auth/faces/{id}/face-id/` | Добавление Face ID |

## Cameras

| Method | URL | Описание |
|---|---|---|
| GET | `/api/auth/cameras/` | Список камер |
| POST | `/api/auth/cameras/create/` | Создание аккаунта камеры |

## Logs

| Method | URL | Описание |
|---|---|---|
| GET | `/api/auth/logs/` | Получение логов распознавания |
| POST | `/api/auth/logs/check/` | Проверка лица и создание лога |
| DELETE | `/api/auth/logs/` | Удаление всех видимых логов |
| DELETE | `/api/auth/logs/{id}/` | Удаление одного лога |

## Users

| Method | URL | Описание |
|---|---|---|
| GET | `/api/auth/users/` | Список пользователей компании |
| POST | `/api/auth/users/` | Создание пользователя |
| PATCH | `/api/auth/users/{id}/` | Обновление пользователя |
| DELETE | `/api/auth/users/{id}/` | Удаление пользователя |

## Audit

| Method | URL | Описание |
|---|---|---|
| GET | `/api/auth/audit/` | Логи действий администратора |
