# Экспертная система (учебный MVP)

Учебное веб-приложение для демонстрации работы экспертной системы по инфекционным заболеваниям.

## Дисклеймер

Система носит учебный характер и не является медицинским сервисом для постановки диагноза или назначения лечения.

## Стек

- Backend: Python 3.12, FastAPI
- Frontend: React 18, Vite
- Контейнеризация: Docker, Docker Compose
- Хранилище знаний: JSON

## Запуск

```bash
docker compose up --build
```

Открыть:

- Frontend: http://localhost:3000
- Backend docs: http://localhost:8000/docs

## Структура

- `backend/` — API, решатель, доступ к базе знаний
- `frontend/` — UI решателя и редактор базы знаний
- `backend/data/knowledge_base.json` — база знаний

## Тесты backend

Локально (без Docker):

```bash
cd backend
pip install -r requirements.txt
pytest
```
