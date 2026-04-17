from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.broker_setting import BrokerSetting


class BrokerSettingsRepository:
    """Одна строка id=1 хранит выбранный счёт."""

    _ROW_ID = 1

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_row(self) -> BrokerSetting | None:
        return self._db.get(BrokerSetting, self._ROW_ID)

    def get_selected_account_id(self) -> str | None:
        row = self.get_row()
        if row is None:
            return None
        v = (row.selected_account_id or "").strip()
        return v or None

    def set_selected_account_id(self, account_id: str | None) -> BrokerSetting:
        row = self.get_row()
        if row is None:
            row = BrokerSetting(id=self._ROW_ID, selected_account_id=account_id)
            self._db.add(row)
        else:
            row.selected_account_id = account_id
        self._db.flush()
        return row
