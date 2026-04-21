# Экспертная система (учебный MVP)

Учебное веб-приложение для демонстрации экспертной диагностики инфекционных заболеваний.

## Дисклеймер

Система учебная и не предназначена для постановки реального медицинского диагноза.

## Стек

- Backend: Python 3.12, FastAPI, SQLAlchemy, Alembic
- Frontend: React 18, Vite
- БД: PostgreSQL 16
- Контейнеризация: Docker, Docker Compose

## Запуск

```bash
docker compose up --build -d
```

- Frontend: `http://localhost:3000`
- Backend docs: `http://localhost:8000/docs`

## Архитектура данных

- Runtime-хранилище: PostgreSQL
- Seed-источник: `backend/data/knowledge_base.json`
- Файл знаний JSON не используется как рабочая БД

## Архитектура решателя

Основной endpoint: `POST /api/solver/determine`.

Pipeline:

1. Нормализация и валидация `patient_values` (включая ошибку 400 для неизвестных characteristic id).
2. Rule-based фильтрация кандидатов.
3. Если кандидатов больше одного, выбирается диагноз через нейросетевой ранкер.

Ответ содержит:

- `status`: `determined`, `likely`, `neural_selected`, `not_determined`
- `selection_method`: `rules`, `neural`, `fallback`
- `confidence`
- `ranked_candidates`

`POST /api/solver/solve` сохранён как deprecated endpoint для совместимости.

## Нейронная сеть

Используется самописная полносвязная сеть прямого распространения.

- Архитектура: `N -> 16 -> M`
- Для текущей БЗ: `25 -> 16 -> 9`
- Скрытый слой: `tanh`
- Выход: `softmax`
- Обучение: `backpropagation + gradient descent`
- Данные: синтетическая выборка из базы знаний
- Файл модели: `backend/data/model-data.json` (или `MODEL_DATA_PATH`)

## Редактор знаний

Страница `/editor` содержит:

- Системы организма
- Характеристики (полный CRUD)
- Диагнозы (визуальный редактор критериев)
- Лечения (полный CRUD)

Во всех вкладках есть явные режимы: создание и редактирование.

## Тесты backend

```bash
docker compose exec -T backend pytest -q
```

## Smoke-проверка

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke.ps1
```
