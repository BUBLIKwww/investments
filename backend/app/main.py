from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 — регистрация моделей в Base.metadata для create_all
from app.api.router import api_router
from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.schema_bootstrap import ensure_funds_schema
from app.db.base import Base
from app.services.portfolio_recalculation_service import PortfolioRecalculationService
from app.services.seed_service import SeedService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Railway / деплой: таблицы есть даже без успешного `alembic upgrade` (Alembic в проекте остаётся).
    Base.metadata.create_all(bind=engine)
    ensure_funds_schema(engine)
    db = SessionLocal()
    try:
        SeedService(db, settings).ensure_seeded()
        PortfolioRecalculationService(db).rebuild_positions_for_all_users()
        db.commit()
    finally:
        db.close()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# CORS: при allow_origins=["*"] спецификация запрещает allow_credentials=True — иначе preflight/ответ не пройдут.
_cors_origins = ["*"] if settings.CORS_ALLOW_ALL else settings.CORS_ORIGINS
_cors_credentials = False if settings.CORS_ALLOW_ALL else True

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok"}

# force deploy
