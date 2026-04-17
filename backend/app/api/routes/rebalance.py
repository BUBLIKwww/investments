from typing import Literal

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.rebalance import RebalanceRead
from app.services.rebalance_service import RebalanceService

router = APIRouter()


@router.get("", response_model=RebalanceRead)
def get_rebalance(
    user: CurrentUser,
    db: DbSession,
    source: Literal["simulation", "live"] = Query("simulation"),
) -> RebalanceRead:
    return RebalanceService(db).get_rebalance(int(user.id), source=source)
