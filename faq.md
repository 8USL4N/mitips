# FAQ

## Как запустить проект

```bash
docker compose up --build -d
```

- Frontend: `http://localhost:3000`
- Swagger: `http://localhost:8000/docs`

## Как запустить backend-тесты

```bash
docker compose exec -T backend pytest -q
```

## Как прогнать smoke

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke.ps1
```

## Что изменилось в решателе

- Основной endpoint: `POST /api/solver/determine`.
- Если кандидатов несколько, используется нейросетевой классификатор.
- Финальный статус для такого случая: `neural_selected`.
- Метод выбора: `selection_method = neural`.
- `POST /api/solver/solve` оставлен как deprecated для совместимости.

## Где хранится модель

- По умолчанию: `backend/data/model-data.json`
- Можно переопределить через `MODEL_DATA_PATH`.

## Дисклеймер

Система является учебной и не предназначена для постановки реального медицинского диагноза.
