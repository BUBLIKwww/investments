from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class FundRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    ticker: str
    figi_or_uid: str
    lot: int = Field(ge=1)
    price: Decimal = Field(gt=0)
    currency: str
    last_price_updated_at: datetime
    is_active: bool


class FundsPricesRefreshResponse(BaseModel):
    updated: int
    funds: list[FundRead]
