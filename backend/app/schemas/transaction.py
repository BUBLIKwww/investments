from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import TransactionOperationType


class InvestmentTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    category_id: int
    fund_id: int
    operation_type: TransactionOperationType
    quantity: int = Field(ge=1)
    price_per_unit: Decimal = Field(gt=0)
    total_amount: Decimal
    executed_at: datetime
    note: str | None
    created_at: datetime
    updated_at: datetime


class InvestmentTransactionCreate(BaseModel):
    fund_id: int
    category_id: int | None = None
    operation_type: TransactionOperationType
    quantity: int = Field(ge=1)
    price_per_unit: Decimal = Field(gt=0)
    total_amount: Decimal = Field(gt=0)
    executed_at: datetime
    note: str | None = None


class InvestmentTransactionUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    fund_id: int | None = None
    category_id: int | None = None
    operation_type: TransactionOperationType | None = None
    quantity: int | None = None
    price_per_unit: Decimal | None = None
    total_amount: Decimal | None = None
    executed_at: datetime | None = None
    note: str | None = None
