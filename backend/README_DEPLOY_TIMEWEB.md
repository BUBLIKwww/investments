# Backend deploy on Timeweb

## Runtime

- Python `3.11`
- Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Required env

- `DATABASE_URL`
- `TINVEST_TOKEN`
- `TINVEST_USE_SANDBOX`

## Optional env

- `TINVEST_DEFAULT_ACCOUNT_ID`
- `APP_NAME`
- `DEBUG`
- `CORS_ALLOW_ALL`
- `CORS_ORIGINS`

## Docker

Backend Dockerfile already lives in `backend/Dockerfile`.

Build:

```bash
docker build -t investments-backend ./backend
```

Run:

```bash
docker run --rm -p 8000:8000 \
  -e DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST:PORT/DB" \
  -e TINVEST_TOKEN="YOUR_TOKEN" \
  -e TINVEST_USE_SANDBOX="false" \
  -e TINVEST_DEFAULT_ACCOUNT_ID="" \
  investments-backend
```

## Timeweb deploy order

1. Create a new app/container in Timeweb for the `backend` directory only.
2. Use `backend/Dockerfile`.
3. Set env vars:
   - `DATABASE_URL`
   - `TINVEST_TOKEN`
   - `TINVEST_USE_SANDBOX`
   - `TINVEST_DEFAULT_ACCOUNT_ID` (optional)
4. Expose port `8000`.
5. Deploy.

## Checks after start

- `GET /health`
- `GET /api/v1/users/me`
- `GET /api/v1/broker/accounts`
- `GET /api/v1/portfolio?source=simulation`
- `GET /api/v1/portfolio?source=live`
