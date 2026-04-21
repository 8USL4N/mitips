# FAQ: запуск проекта с нуля

## 1) Первый запуск (после `git clone`)

```bash
git clone <URL_ВАШЕГО_РЕПО>
cd mitips
cp .env.example .env
docker compose up --build -d
```

Для Windows PowerShell вместо `cp`:

```powershell
Copy-Item .env.example .env
```

## 2) Проверка, что всё поднялось

```bash
docker compose ps
```

Открыть в браузере:

- `http://localhost:3000` — frontend
- `http://localhost:8000/docs` — Swagger API

## 3) Полезные команды

Перезапуск после изменений:

```bash
docker compose up --build -d
```

Логи:

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f postgres
```

Тесты backend:

```bash
docker compose exec -T backend pytest -q
```

Smoke-проверка:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke.ps1
```

Экспорт БЗ в JSON:

```bash
docker compose exec -T backend python scripts/export_kb.py
```

## 4) Что изменилось в решателе

- Основной endpoint: `POST /api/solver/determine`.
- При нескольких кандидатов используется ML-ranker (`status=ml_selected`).
- Endpoint `POST /api/solver/solve` сохранён как deprecated для совместимости, но UI его не использует.

## 5) Остановка проекта

```bash
docker compose down
```

## 6) Полный сброс

```bash
docker compose down -v
docker compose up --build -d
```
