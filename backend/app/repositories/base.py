from typing import Any, Generic, TypeVar

from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    def __init__(self, db: Session, model: type[ModelT]) -> None:
        self._db = db
        self._model = model

    def get(self, id_: int) -> Any:
        return self._db.get(self._model, id_)
