"""Удаление демо-инструментов (mock-*) и связанных строк."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.fund import Fund
from app.models.investment_transaction import InvestmentTransaction
from app.models.portfolio_position import PortfolioPosition
from app.models.strategy_category import StrategyCategory
from app.models.topup_item import TopupItem


def cleanup_demo_instruments(db: Session) -> int:
    """Удаляет фонды с figi_or_uid LIKE mock-% и связанные записи. Возвращает число удалённых фондов."""
    mock_ids = list(db.scalars(select(Fund.id).where(Fund.figi_or_uid.like("mock-%"))).all())
    if not mock_ids:
        return 0
    db.execute(delete(InvestmentTransaction).where(InvestmentTransaction.fund_id.in_(mock_ids)))
    db.execute(delete(PortfolioPosition).where(PortfolioPosition.fund_id.in_(mock_ids)))
    db.execute(delete(TopupItem).where(TopupItem.fund_id.in_(mock_ids)))
    db.execute(delete(StrategyCategory).where(StrategyCategory.fund_id.in_(mock_ids)))
    db.execute(delete(Fund).where(Fund.id.in_(mock_ids)))
    db.flush()
    return len(mock_ids)
