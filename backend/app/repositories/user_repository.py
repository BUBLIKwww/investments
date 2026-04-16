from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User

MOCK_TELEGRAM_ID = 1_000_000_001


class UserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self._db.get(User, user_id)

    def get_mock_user(self) -> User | None:
        stmt = select(User).where(User.telegram_id == MOCK_TELEGRAM_ID).limit(1)
        return self._db.execute(stmt).scalar_one_or_none()

    def create_mock_user(self) -> User:
        user = User(telegram_id=MOCK_TELEGRAM_ID, username="mock_user")
        self._db.add(user)
        self._db.flush()
        return user
