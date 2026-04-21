# ROADMAP: Экспертная система (текущее состояние MVP)

## 1. Цель

Собрать учебную экспертную систему с редактируемой базой знаний и объяснимым решателем, где неоднозначность между несколькими кандидатами разрешается через ML-ranker.

## 2. Что реализовано

- Backend на FastAPI + SQLAlchemy с PostgreSQL.
- Редактор знаний на React:
  - системы организма;
  - характеристики (CRUD);
  - диагнозы (визуальные критерии);
  - лечения (CRUD).
- Решатель `POST /api/solver/determine`:
  - rule-based фильтрация;
  - выбор одного кандидата через ML-ranker при множестве совпадений;
  - fallback-гипотезы при отсутствии кандидатов.
- Статусы решателя: `determined`, `likely`, `ml_selected`, `not_determined`.
- В ответе решателя: `selection_method`, `confidence`, `ranked_candidates`.

## 3. API-акценты

- Характеристики:
  - `GET /api/characteristics`
  - `GET /api/characteristics/{id}`
  - `GET /api/characteristics/{id}/usage`
  - `POST /api/characteristics`
  - `PUT /api/characteristics/{id}`
  - `DELETE /api/characteristics/{id}`
- Лечения:
  - `GET /api/treatments`
  - `GET /api/treatments/{id}`
  - `POST /api/treatments`
  - `PUT /api/treatments/{id}`
  - `DELETE /api/treatments/{id}`
  - `PUT /api/treatments/{id}/actions` (legacy)
- Решатель:
  - `POST /api/solver/determine` (основной endpoint)
  - `POST /api/solver/solve` (deprecated, сохранён для совместимости)

## 4. Ограничения и безопасность

- Система учебная, без клинической валидации.
- Изменения характеристик защищены от разрушения связей:
  - запрет опасной смены типа используемой характеристики;
  - запрет удаления используемых enum-ключей;
  - запрет удаления используемых характеристик/лечений без явного force.
- Неизвестные ID характеристик в `patient_values` приводят к ошибке `400`.

## 5. Следующие шаги

- Добавить отдельный набор реальных/экспертных patient-cases вместо синтетики.
- Вынести метрики качества ranker-а (offline evaluation).
- Опционально полностью удалить deprecated `POST /api/solver/solve` после стабилизации.
