# Инвестиционный помощник (Telegram Mini App)

Монорепозиторий из трёх сервисов: **`backend/`**, **`bot/`**, **`frontend/`**.

## Статус по частям

- **`backend/`**: рабочий **MVP** — модели, миграции, репозитории, сервисы, расчёт пополнения (режимы `strict` / `maximize` / `smart`), портфель, стратегия, rebalance, mock‑ценник через `Fund.price` (архитектурно выделен `PricingProvider`).
- **`bot/`** и **`frontend/`**: по‑прежнему стартовый каркас (без доработок в рамках текущего этапа).

## Backend: быстрый старт

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
mkdir -p data
PYTHONPATH=. alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

При старте приложения выполняется **автосид**: если таблица `funds` пустая, создаются mock‑фонды, mock‑пользователь и стратегия по умолчанию (40/25/20/15).

Отдельно (например, в CI) можно вызвать:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. python -m app.scripts.seed
```

## Backend: основные эндпоинты (`/api/v1`)

- `GET /api/v1/users/me` — mock‑пользователь (через `get_current_user()`).
- `GET /api/v1/strategy`, `PUT /api/v1/strategy` — категории стратегии с привязкой к фонду, валидация суммы процентов активных категорий = 100.
- `GET /api/v1/funds`, `GET /api/v1/funds/{fund_id}` — список активных фондов и карточка.
- `GET /api/v1/portfolio` — инвестировано, текущая оценка по mock‑цене, сводка по категориям, позиции.
- `POST /api/v1/topups/calculate` — расчёт пополнения без сохранения.
- `POST /api/v1/topups` — пересчёт + сохранение истории + обновление позиций.
- `GET /api/v1/topups/history` — история пополнений.
- `GET /api/v1/rebalance` — упрощённые рекомендации (текущие/целевые веса, дельта, under/over).

Служебно: `GET /health`, `GET /docs`.

## PostgreSQL (позже)

Поменяйте `DATABASE_URL` на `postgresql+psycopg://...`, добавьте драйвер (`psycopg[binary]`) и прогоните `alembic upgrade head` на новой базе.

## Примеры запросов (curl)

```bash
BASE=http://127.0.0.1:8000

curl -s "$BASE/api/v1/users/me" | jq
curl -s "$BASE/api/v1/strategy" | jq
curl -s "$BASE/api/v1/funds" | jq

curl -s -X POST "$BASE/api/v1/topups/calculate" \
  -H 'Content-Type: application/json' \
  -d '{"total_amount":"10000.00","mode":"strict"}' | jq

curl -s -X POST "$BASE/api/v1/topups" \
  -H 'Content-Type: application/json' \
  -d '{"total_amount":"10000.00","mode":"maximize"}' | jq

curl -s "$BASE/api/v1/portfolio" | jq
curl -s "$BASE/api/v1/rebalance" | jq
curl -s "$BASE/api/v1/topups/history" | jq
```

## Bot

```bash
cd bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
PYTHONPATH=. python -m app.bot
```

## Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
