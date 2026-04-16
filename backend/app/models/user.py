from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.portfolio_position import PortfolioPosition
    from app.models.strategy_category import StrategyCategory
    from app.models.topup_history import TopupHistory


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    strategy_categories: Mapped[list["StrategyCategory"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    portfolio_positions: Mapped[list["PortfolioPosition"]] = relationship(back_populates="user")
    topups: Mapped[list["TopupHistory"]] = relationship(back_populates="user")
