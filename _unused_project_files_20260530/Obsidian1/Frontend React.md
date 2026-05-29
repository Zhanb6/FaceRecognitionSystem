# Frontend React

Frontend находится в папке:

`face_recognition_system/frontend`

## Технологии

- React
- TypeScript
- Vite
- CSS

## Основные файлы

- `src/App.tsx` — вход, регистрация и проверка авторизации
- `src/Dashboard.tsx` — главная панель управления
- `src/api.ts` — функции для запросов к backend
- `src/types.ts` — TypeScript-типы
- `src/index.css` — стили интерфейса

## Основные функции

- регистрация пользователя
- вход в систему
- хранение access и refresh token в localStorage
- отображение dashboard
- управление пользователями
- управление камерами
- просмотр логов распознавания
- добавление Face ID
- проверка распознавания лица через камеру

## Связь с backend

Frontend отправляет запросы на API через путь:

`/api/auth/...`

Во время разработки Vite перенаправляет эти запросы на backend:

`http://127.0.0.1:8000`
