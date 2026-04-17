from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.portfolio import PortfolioRead
from app.schemas.portfolio_rebalance import (
    RebalanceExecuteRequest,
    RebalanceExecuteResponse,
    RebalancePreviewRequest,
    RebalancePreviewResponse,
)
from app.services.portfolio_rebalance_service import PortfolioRebalanceService
from app.services.portfolio_service import PortfolioService

router = APIRouter()


@router.get("", response_model=PortfolioRead)
def get_portfolio(user: CurrentUser, db: DbSession) -> PortfolioRead:
    return PortfolioService(db).get_portfolio(int(user.id))


@router.post("/rebalance/preview", response_model=RebalancePreviewResponse)
def rebalance_preview(
    user: CurrentUser,
    db: DbSession,
    payload: RebalancePreviewRequest,
) -> RebalancePreviewResponse:
    return PortfolioRebalanceService(db).preview(int(user.id), payload.amount)


@router.post("/rebalance/execute", response_model=RebalanceExecuteResponse)
def rebalance_execute(
    user: CurrentUser,
    db: DbSession,
    payload: RebalanceExecuteRequest,
) -> RebalanceExecuteResponse:
    return PortfolioRebalanceService(db).execute(int(user.id), payload.amount)
