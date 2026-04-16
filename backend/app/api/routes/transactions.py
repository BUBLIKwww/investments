from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.transaction import (
    InvestmentTransactionCreate,
    InvestmentTransactionRead,
    InvestmentTransactionUpdate,
)
from app.services.transaction_service import TransactionService

router = APIRouter()


@router.get("", response_model=list[InvestmentTransactionRead])
def list_transactions(user: CurrentUser, db: DbSession) -> list[InvestmentTransactionRead]:
    return TransactionService(db).list(int(user.id))


@router.post("", response_model=InvestmentTransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(user: CurrentUser, db: DbSession, payload: InvestmentTransactionCreate) -> InvestmentTransactionRead:
    return TransactionService(db).create(int(user.id), payload)


@router.get("/{transaction_id}", response_model=InvestmentTransactionRead)
def get_transaction(user: CurrentUser, db: DbSession, transaction_id: int) -> InvestmentTransactionRead:
    return TransactionService(db).get(int(user.id), transaction_id)


@router.put("/{transaction_id}", response_model=InvestmentTransactionRead)
def update_transaction(
    user: CurrentUser,
    db: DbSession,
    transaction_id: int,
    payload: InvestmentTransactionUpdate,
) -> InvestmentTransactionRead:
    return TransactionService(db).update(int(user.id), transaction_id, payload)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(user: CurrentUser, db: DbSession, transaction_id: int) -> None:
    TransactionService(db).delete(int(user.id), transaction_id)
