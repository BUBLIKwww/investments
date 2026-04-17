from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.fund import FundRead


class PortfolioPositionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    category_id: int
    fund_id: int
    category_name: str
    total_lots: int = Field(ge=0)
    total_units: int = Field(ge=0)
    invested_amount: Decimal = Field(ge=0)
    average_buy_price: Decimal = Field(ge=0)
    current_amount: Decimal = Field(ge=0)
    current_weight_percent: Decimal = Field(ge=0)
    fund: FundRead
    current_price: Decimal = Field(description="Цена за шт. из каталога (Fund.price)", gt=0)
    quantity: int = Field(ge=0, description="Количество штук в позиции (= total_units)")
    current_value: Decimal = Field(ge=0, description="Рыночная оценка позиции")
    invested_value: Decimal = Field(ge=0, description="Себестоимость (вложено)")
    pnl: Decimal = Field(description="current_value − invested_value")
    pnl_percent: Decimal = Field(description="PnL / invested_value * 100, 0 если вложено 0")
    last_price_updated_at: datetime | None = Field(
        default=None,
        description="Момент обновления last price (как у fund.last_price_updated_at)",
    )


class CategorySummary(BaseModel):
    category_id: int
    category_name: str
    target_percent: Decimal
    current_weight_percent: Decimal
    current_amount: Decimal
    invested_amount: Decimal


class PortfolioRead(BaseModel):
    source: Literal["simulation", "live"] = Field(
        default="simulation",
        description="simulation — расчёт по журналу приложения; live — портфель с брокерского счёта T‑Invest",
    )
    total_invested_amount: Decimal
    total_current_amount: Decimal
    total_pnl: Decimal = Field(description="Сумма PnL по позициям")
    total_pnl_percent: Decimal = Field(
        description="total_pnl / total_invested_amount * 100, 0 если вложено 0",
    )
    categories: list[CategorySummary]
    positions: list[PortfolioPositionRead]
