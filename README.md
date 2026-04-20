# Экспертная система (учебный MVP)

Учебное веб-приложение для демонстрации работы экспертной системы по инфекционным заболеваниям.

## Дисклеймер

Система носит учебный характер и не является медицинским сервисом для постановки диагноза или назначения лечения.

## Стек

- Backend: Python 3.12, FastAPI, SQLAlchemy, Alembic
- Frontend: React 18, Vite
- БД: PostgreSQL 16
- Контейнеризация: Docker, Docker Compose

## Запуск

```bash
docker compose up --build -d
```

Открыть:

- Frontend: http://localhost:3000
- Backend docs: http://localhost:8000/docs

## Архитектура данных

- Runtime-хранилище: PostgreSQL
- Seed-источник: `backend/data/knowledge_base.json`
- JSON не используется как рабочая БД

## Архитектура решателя

Система работает в двух режимах:

1. Определение диагноза по симптомам (главная страница `/`)
- Пользователь вводит известные значения признаков без выбора диагноза.
- Backend рассчитывает статус (`determined`, `likely`, `ambiguous`, `not_determined`) и возвращает лечение/объяснение.
- При неоднозначности показываются альтернативные гипотезы и недостающие характеристики.

2. Проверка эталона (редактор `/editor`, вкладка `Проверка эталона`)
- Эксперт выбирает конкретный диагноз.
- Система проверяет введённые значения на соответствие эталонным критериям диагноза (`validate_selected`).
- Режим предназначен для верификации и сопровождения базы знаний.

## Миграции

В контейнере backend при старте автоматически выполняется:

```bash
alembic upgrade head
```

## Тесты backend

```bash
docker compose exec -T backend pytest -q
```

## Smoke-проверка

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke.ps1
```

Ожидаемый финал: `SMOKE RESULT: PASS`.

## Экспорт БЗ в JSON

```bash
docker compose exec -T backend python scripts/export_kb.py
```

По умолчанию экспорт создаётся в `/app/data/knowledge_base.export.json` внутри контейнера.
