from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.topup_history import TopupHistory
from app.models.topup_item import TopupItem


class TopupRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_history(self, user_id: int) -> list[TopupHistory]:
        stmt = (
            select(TopupHistory)
            .where(TopupHistory.user_id == user_id)
            .options(joinedload(TopupHistory.items))
            .order_by(TopupHistory.created_at.desc(), TopupHistory.id.desc())
        )
        return list(self._db.execute(stmt).unique().scalars().all())

    def create_topup(self, topup: TopupHistory, items: list[TopupItem]) -> TopupHistory:
        self._db.add(topup)
        self._db.flush()
        for item in items:
            item.topup_history_id = topup.id
            self._db.add(item)
        self._db.flush()
        self._db.refresh(topup)
        return topup
