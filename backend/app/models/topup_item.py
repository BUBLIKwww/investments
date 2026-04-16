from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.fund import Fund
    from app.models.strategy_category import StrategyCategory
    from app.models.topup_history import TopupHistory


class TopupItem(Base):
    __tablename__ = "topup_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    topup_history_id: Mapped[int] = mapped_column(ForeignKey("topup_history.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("strategy_categories.id"), index=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("funds.id"), index=True)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    actual_allocated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    cash_remainder: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    price_used: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    lot_size: Mapped[int] = mapped_column(Integer, nullable=False)
    purchased_lots: Mapped[int] = mapped_column(Integer, nullable=False)
    purchased_units: Mapped[int] = mapped_column(Integer, nullable=False)

    topup: Mapped["TopupHistory"] = relationship(back_populates="items")
    category: Mapped["StrategyCategory"] = relationship(back_populates="topup_items")
    fund: Mapped["Fund"] = relationship(back_populates="topup_items")
