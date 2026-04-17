from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.repositories.user_repository import MOCK_TELEGRAM_ID, UserRepository
from app.services.demo_cleanup import cleanup_demo_instruments
from app.models.user import User

logger = logging.getLogger(__name__)


class SeedService:
    """Старт: очистка демо-инструментов и mock-пользователь. Каталог фондов не заполняется."""

    def __init__(self, db: Session, settings: object | None = None) -> None:
        _ = settings
        self._db = db

    def ensure_seeded(self) -> None:
        removed = cleanup_demo_instruments(self._db)
        if removed:
            logger.info("Удалены демо-инструменты (mock-*), фондов=%s", removed)

        users = UserRepository(self._db)
        if users.get_mock_user() is None:
            self._db.add(User(telegram_id=MOCK_TELEGRAM_ID, username="mock_user"))
            self._db.flush()

        self._db.commit()
