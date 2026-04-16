from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.repositories.topup_repository import TopupRepository
from app.schemas.topup import TopupCalculateRequest, TopupCalculateResponse, TopupHistoryRead
from app.services.topup_service import TopupService

router = APIRouter()


@router.post("/calculate", response_model=TopupCalculateResponse)
def calculate_topup(user: CurrentUser, db: DbSession, payload: TopupCalculateRequest) -> TopupCalculateResponse:
    return TopupService(db).calculate(int(user.id), payload)


@router.post("", response_model=TopupCalculateResponse)
def execute_topup(user: CurrentUser, db: DbSession, payload: TopupCalculateRequest) -> TopupCalculateResponse:
    return TopupService(db).execute(int(user.id), payload)


@router.get("/history", response_model=list[TopupHistoryRead])
def topup_history(user: CurrentUser, db: DbSession) -> list[TopupHistoryRead]:
    rows = TopupRepository(db).list_history(int(user.id))
    return [TopupHistoryRead.model_validate(r) for r in rows]
