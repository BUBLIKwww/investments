from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.investment_transaction import InvestmentTransaction
    from app.models.portfolio_position import PortfolioPosition
    from app.models.strategy_category import StrategyCategory
    from app.models.topup_item import TopupItem


class Fund(Base):
    __tablename__ = "funds"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    ticker: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    # Историческое поле: дублирует instrument_uid для обратной совместимости API (GetLastPrices).
    figi_or_uid: Mapped[str] = mapped_column(String(128), index=True)
    instrument_uid: Mapped[str | None] = mapped_column(String(128), unique=True, index=True, nullable=True)
    figi: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lot: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, server_default="RUB")
    last_price_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")

    strategy_categories: Mapped[list["StrategyCategory"]] = relationship(back_populates="fund")
    positions: Mapped[list["PortfolioPosition"]] = relationship(back_populates="fund")
    topup_items: Mapped[list["TopupItem"]] = relationship(back_populates="fund")
    investment_transactions: Mapped[list["InvestmentTransaction"]] = relationship(back_populates="fund")
