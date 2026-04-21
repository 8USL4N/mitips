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

Основной пользовательский сценарий:

1. Пользователь вводит известные значения характеристик на странице `/`.
2. Backend выполняет rule-based фильтрацию диагнозов:
   - при противоречии критерию диагноз исключается;
   - при отсутствии критерия по характеристике диагноз не исключается, но получает меньший вес.
3. Если после правил остаётся несколько кандидатов, запускается ML-ranker (синтетическое обучение на базе знаний).
4. API возвращает:
   - `status`: `determined`, `likely`, `ml_selected`, `not_determined`;
   - `selection_method`: `rules`, `ml`, `fallback`;
   - `confidence` (для ML-сценария);
   - `ranked_candidates` + альтернативные гипотезы.

Дополнительно (deprecated, для совместимости API):

- `POST /api/solver/solve` сохраняется как внутренний режим `validate_selected`.
- UI редактора больше не использует этот режим.

## Редактор знаний

Страница `/editor` содержит 4 вкладки:

- Системы организма
- Характеристики (полный CRUD)
- Диагнозы (визуальный редактор критериев, без JSON)
- Лечения (полный CRUD)

Во всех вкладках используется явное разделение режимов:

- Добавить новый объект
- Изменить существующий объект

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
