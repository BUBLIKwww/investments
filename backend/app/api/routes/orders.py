"""Live‑ордера T‑Invest: POST buy/sell и GET history."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.order import OrderHistoryItem, OrderRequest, OrderResult
from app.services.order_service import OrderService

router = APIRouter()


@router.post("/buy", response_model=OrderResult, status_code=status.HTTP_200_OK)
def order_buy(user: CurrentUser, db: DbSession, payload: OrderRequest) -> OrderResult:
    return OrderService(db).place_market_order(
        int(user.id),
        fund_id=int(payload.fund_id),
        quantity=int(payload.quantity),
        action="buy",
    )


@router.post("/sell", response_model=OrderResult, status_code=status.HTTP_200_OK)
def order_sell(user: CurrentUser, db: DbSession, payload: OrderRequest) -> OrderResult:
    return OrderService(db).place_market_order(
        int(user.id),
        fund_id=int(payload.fund_id),
        quantity=int(payload.quantity),
        action="sell",
    )


@router.get("/history", response_model=list[OrderHistoryItem])
def orders_history(user: CurrentUser, db: DbSession) -> list[OrderHistoryItem]:
    return OrderService(db).history(int(user.id))
