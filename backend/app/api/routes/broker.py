from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.repositories.broker_settings_repository import BrokerSettingsRepository
from app.schemas.broker import BrokerAccountRead, BrokerSettingsRead, BrokerSettingsUpdate
from app.services.tinvest_broker_service import TinvestBrokerService

router = APIRouter()


@router.get("/accounts", response_model=list[BrokerAccountRead])
def list_broker_accounts(_user: CurrentUser, db: DbSession) -> list[BrokerAccountRead]:
    rows = TinvestBrokerService(db, settings).list_accounts()
    return [BrokerAccountRead.model_validate(r) for r in rows]


@router.get("/settings", response_model=BrokerSettingsRead)
def get_broker_settings(_user: CurrentUser, db: DbSession) -> BrokerSettingsRead:
    repo = BrokerSettingsRepository(db)
    sel = repo.get_selected_account_id()
    env = (settings.TINVEST_DEFAULT_ACCOUNT_ID or "").strip() or None
    return BrokerSettingsRead(selected_account_id=sel, default_account_id_env=env)


@router.put("/settings", response_model=BrokerSettingsRead)
def put_broker_settings(
    _user: CurrentUser,
    db: DbSession,
    payload: BrokerSettingsUpdate,
) -> BrokerSettingsRead:
    repo = BrokerSettingsRepository(db)
    acc = (payload.selected_account_id or "").strip() or None
    repo.set_selected_account_id(acc)
    db.commit()
    env = (settings.TINVEST_DEFAULT_ACCOUNT_ID or "").strip() or None
    return BrokerSettingsRead(selected_account_id=acc, default_account_id_env=env)
