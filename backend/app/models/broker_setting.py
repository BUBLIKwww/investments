from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BrokerSetting(Base):
    """Singleton‑настройки брокера (один выбранный счёт T‑Invest на деплой)."""

    __tablename__ = "broker_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    selected_account_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
