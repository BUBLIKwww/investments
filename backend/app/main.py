from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 — регистрация моделей в Base.metadata для create_all
from app.api.router import api_router
from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.db.base import Base
from app.services.seed_service import SeedService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Railway / деплой: таблицы есть даже без успешного `alembic upgrade` (Alembic в проекте остаётся).
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        SeedService(db).ensure_seeded()
    finally:
        db.close()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok"}
