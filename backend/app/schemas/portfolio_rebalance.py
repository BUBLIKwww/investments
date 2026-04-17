from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class RebalancePreviewRequest(BaseModel):
    amount: Decimal | None = Field(
        default=None,
        description="Макс. доля кэша для сдвига к целям; null — весь доступный баланс",
    )
    mode: Literal["simulation", "live"] = Field(
        default="simulation",
        description="simulation — внутренний журнал; live — котировки и кэш с реального счёта T‑Invest",
    )


class RebalanceActionRead(BaseModel):
    fund_id: int
    ticker: str
    action: Literal["buy", "sell"]
    amount: Decimal = Field(description="Сумма сделки в валюте портфеля (руб.)", ge=0)
    quantity: int = Field(default=0, ge=0, description="Количество бумаг (штук)")
    lots: int = Field(default=0, ge=0, description="Количество лотов")
    instrument_id: str = Field(default="", description="instrument_uid или figi для PostOrder")


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
    mode: Literal["simulation", "live"] = "simulation"
    plan_fingerprint: str = Field(description="SHA256 нормализованного плана; нужен для execute-live")
    account_id: str | None = Field(default=None, description="Счёт T‑Invest для live; в simulation = null")


class RebalanceExecuteRequest(BaseModel):
    amount: Decimal | None = Field(default=None, description="Как в preview: лимит использования кэша")


class RebalanceExecuteResponse(BaseModel):
    created_transaction_ids: list[int]


class RebalanceLiveExecuteRequest(BaseModel):
    amount: Decimal | None = Field(default=None, description="Должно совпадать с последним live preview")
    plan_fingerprint: str = Field(description="Из ответа preview (mode=live)")
    confirm: bool = Field(default=False, description="Обязательно true для реальных заявок")
    dry_run: bool = Field(default=False, description="Проверить план и fingerprint без PostOrder")


class RebalanceLiveOrderResult(BaseModel):
    ticker: str
    action: Literal["buy", "sell"]
    instrument_id: str
    lots: int
    success: bool
    order_id: str | None = None
    execution_status: str | None = None
    message: str | None = None


class RebalanceLiveExecuteResponse(BaseModel):
    orders: list[RebalanceLiveOrderResult]
    dry_run: bool = False
