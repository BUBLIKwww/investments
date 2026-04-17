from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class RebalancePreviewRequest(BaseModel):
    amount: Decimal | None = Field(
        default=None,
        description="Макс. доля кэша для сдвига к целям; null — весь доступный баланс",
    )


class RebalanceActionRead(BaseModel):
    fund_id: int
    ticker: str
    action: Literal["buy", "sell"]
    amount: Decimal = Field(description="Сумма сделки в валюте портфеля (руб.)", ge=0)


class RebalanceInstrumentPreview(BaseModel):
    ticker: str
    fund_id: int
    current_percent: Decimal = Field(description="Доля категории в капитале до плана, %", ge=0)
    target_percent: Decimal = Field(description="Целевая доля стратегии, %", ge=0)
    after_percent: Decimal = Field(description="Доля категории в капитале после симуляции ног, %", ge=0)


class RebalancePreviewResponse(BaseModel):
    cash_balance: Decimal
    scale: Decimal = Field(description="Доля применённого сдвига (1 = полный ребаланс)")
    actions: list[RebalanceActionRead]
    total_used: Decimal = Field(
        description="Чистый отток кэша: сумма покупок − сумма продаж по плану",
    )
    before_percent: Decimal = Field(
        default=Decimal("0"),
        description="Доля рынка в капитале до плана (оценка позиций / (рынок+кэш)) × 100, %",
        ge=0,
    )
    after_percent: Decimal = Field(
        default=Decimal("0"),
        description="Доля рынка в капитале после симуляции ног, %",
        ge=0,
    )
    instruments: list[RebalanceInstrumentPreview] = Field(
        default_factory=list,
        description="По каждой активной категории стратегии: текущая / целевая / после плана доля капитала, %",
    )


class RebalanceExecuteRequest(BaseModel):
    amount: Decimal | None = Field(default=None, description="Как в preview: лимит использования кэша")


class RebalanceExecuteResponse(BaseModel):
    created_transaction_ids: list[int]
