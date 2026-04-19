# Backend Deploy

## Runtime

- Python `3.11.9`
- Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Required env

- `APP_NAME`
- `DATABASE_URL`
- `TINVEST_TOKEN`

## Optional env

- `DEBUG`
- `TINVEST_USE_SANDBOX`
- `TINVEST_DEFAULT_ACCOUNT_ID`
- `CORS_ALLOW_ALL`
- `CORS_ORIGINS`

See `backend/.env.example` for sample values.

## Local run

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Docker run

```bash
docker build -t investments-backend ./backend
docker run --rm -p 8000:8000 --env-file ./backend/.env investments-backend
```

## Check after start

- `GET /health`
- `GET /api/v1/users/me`
- `GET /api/v1/broker/accounts`
- `GET /api/v1/portfolio?source=simulation`
- `GET /api/v1/portfolio?source=live`
