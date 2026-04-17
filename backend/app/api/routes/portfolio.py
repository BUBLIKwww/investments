from typing import Literal

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.portfolio import PortfolioRead
from app.schemas.portfolio_rebalance import (
    RebalanceExecuteRequest,
    RebalanceExecuteResponse,
    RebalanceLiveExecuteRequest,
    RebalanceLiveExecuteResponse,
    RebalancePreviewRequest,
    RebalancePreviewResponse,
)
from app.services.portfolio_rebalance_service import PortfolioRebalanceService
from app.services.portfolio_service import PortfolioService

router = APIRouter()


@router.get("", response_model=PortfolioRead)
def get_portfolio(
    user: CurrentUser,
    db: DbSession,
    source: Literal["simulation", "live"] = Query("simulation", description="live — портфель с T‑Invest"),
) -> PortfolioRead:
    return PortfolioService(db).get_portfolio(int(user.id), source=source)


@router.post("/rebalance/preview", response_model=RebalancePreviewResponse)
def rebalance_preview(
    user: CurrentUser,
    db: DbSession,
    payload: RebalancePreviewRequest,
) -> RebalancePreviewResponse:
    return PortfolioRebalanceService(db).preview(int(user.id), payload.amount, mode=payload.mode)


@router.post("/rebalance/execute", response_model=RebalanceExecuteResponse)
def rebalance_execute(
    user: CurrentUser,
    db: DbSession,
    payload: RebalanceExecuteRequest,
) -> RebalanceExecuteResponse:
    return PortfolioRebalanceService(db).execute(int(user.id), payload.amount)


@router.post("/rebalance/execute-live", response_model=RebalanceLiveExecuteResponse)
def rebalance_execute_live(
    user: CurrentUser,
    db: DbSession,
    payload: RebalanceLiveExecuteRequest,
) -> RebalanceLiveExecuteResponse:
    return PortfolioRebalanceService(db).execute_live(int(user.id), payload)
