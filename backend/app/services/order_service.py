"""Live‑ордера через T‑Invest Invest API: buy/sell + история."""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.config import settings as app_settings
from app.domain.enums import TransactionOperationType
from app.domain.money import q_money, q_price
from app.models.investment_transaction import InvestmentTransaction
from app.repositories.fund_repository import FundRepository
from app.repositories.strategy_repository import StrategyRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.order import OrderHistoryItem, OrderResult
from app.services.pricing.db_provider import DbPricingProvider
from app.services.portfolio_recalculation_service import PortfolioRecalculationService
from app.services.tinvest_broker_service import TinvestBrokerService
from app.services.tinvest_client import money_value_to_decimal, quotation_to_decimal, tinvest_client

logger = logging.getLogger(__name__)

_NOTE_PREFIX = "Live T-Invest"
_RE_ORDER_ID = re.compile(r"order_id=([^;]+)")
_RE_STATUS = re.compile(r"status=([^;]+)")


def _stable_int_id(value: str) -> int:
    raw = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return int(raw, 16)


class OrderService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self._db = db
        self._settings = settings or app_settings
        self._funds = FundRepository(db)
        self._strategy = StrategyRepository(db)
        self._tx_repo = TransactionRepository(db)
        self._pricing = DbPricingProvider()
        self._recalc = PortfolioRecalculationService(db)

    def _category_for_fund(self, user_id: int, fund_id: int) -> int:
        for c in self._strategy.list_for_user(user_id):
            if int(c.fund_id) == int(fund_id) and bool(c.is_active):
                return int(c.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Фонд не привязан к активной категории стратегии",
        )

    def place_market_order(
        self, user_id: int, *, fund_id: int, quantity: int, action: Literal["buy", "sell"],
    ) -> OrderResult:
        fund = self._funds.get_by_id(int(fund_id))
        if fund is None or not fund.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Фонд не найден в каталоге",
            )

        lot = max(1, int(fund.lot or 1))
        if int(quantity) < lot or (int(quantity) % lot) != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"quantity должен быть кратен lot={lot}",
            )
        lots_n = int(quantity) // lot

        instrument_id = (fund.instrument_uid or "").strip() or (fund.figi or "").strip()
        if not instrument_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="У фонда нет instrument_uid/figi — добавьте через POST /api/v1/funds/add",
            )

        category_id = self._category_for_fund(user_id, int(fund_id))

        broker = TinvestBrokerService(self._db, self._settings)
        account_id = broker.resolve_account_id()

        direction = "ORDER_DIRECTION_BUY" if action == "buy" else "ORDER_DIRECTION_SELL"
        client_order_id = str(uuid.uuid4())

        logger.info(
            "live_order_submit user=%s account=%s instrument=%s lots=%s action=%s client_oid=%s",
            user_id, account_id, instrument_id, lots_n, action, client_order_id,
        )

        with tinvest_client(self._settings) as client:
            try:
                r = client.post_order(
                    instrument_id=instrument_id,
                    quantity=lots_n,
                    account_id=account_id,
                    order_id=client_order_id,
                    direction=direction,
                    order_type="ORDER_TYPE_MARKET",
                )
            except Exception as e:
                logger.exception("live_order_failed user=%s fund_id=%s", user_id, fund_id)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"T-Invest: {str(e)[:300]}",
                ) from e

        status_name = str(r.get("executionReportStatus") or "").strip() or None
        ok = status_name not in (
            "EXECUTION_REPORT_STATUS_REJECTED",
            "EXECUTION_REPORT_STATUS_CANCELLED",
            "EXECUTION_REPORT_STATUS_UNSPECIFIED",
            "",
        )
        broker_oid = (str(r.get("orderId") or "").strip() or client_order_id) or None
        msg = (str(r.get("message") or "").strip() or None)

        tx_id: int | None = None
        if ok:
            now = datetime.now(timezone.utc)
            unit_price = quotation_to_decimal(r.get("executedOrderPrice")) or q_price(self._pricing.get_unit_price(fund))
            if unit_price <= 0:
                unit_price = q_price(Decimal("0.01"))
            total_amt = abs(money_value_to_decimal(r.get("totalOrderAmount"))) or q_money(Decimal(int(quantity)) * unit_price)
            op = (
                TransactionOperationType.BUY.value
                if action == "buy"
                else TransactionOperationType.SELL.value
            )
            note = (
                f"{_NOTE_PREFIX} {action}; order_id={broker_oid}; status={status_name or 'N/A'}"
            )
            entity = InvestmentTransaction(
                user_id=user_id,
                category_id=int(category_id),
                fund_id=int(fund_id),
                operation_type=op,
                quantity=int(quantity),
                price_per_unit=unit_price,
                total_amount=total_amt,
                executed_at=now,
                note=note,
                created_at=now,
                updated_at=now,
            )
            try:
                self._tx_repo.add(entity)
                self._recalc.rebuild_positions_for_user(user_id)
                self._db.commit()
                self._db.refresh(entity)
                tx_id = int(entity.id)
            except Exception:
                logger.exception("live_order_persist_failed user=%s broker_oid=%s", user_id, broker_oid)
                self._db.rollback()

        return OrderResult(
            success=bool(ok),
            broker_order_id=broker_oid,
            execution_status=status_name,
            message=msg,
            transaction_id=tx_id,
            account_id=account_id,
            fund_id=int(fund_id),
            quantity=int(quantity),
            lots=lots_n,
            action=action,
        )

    def history(self, user_id: int) -> list[OrderHistoryItem]:
        broker = TinvestBrokerService(self._db, self._settings)
        try:
            account_id = broker.resolve_account_id()
        except HTTPException:
            account_id = ""

        out: list[OrderHistoryItem] = []
        if account_id:
            with tinvest_client(self._settings) as client:
                data = client.get_operations_by_cursor(account_id, limit=100)
            remote_rows = data.get("items") if isinstance(data.get("items"), list) else data.get("operations")
            if isinstance(remote_rows, list):
                for item in remote_rows:
                    operation_type = str(item.get("type") or item.get("operationType") or "").strip()
                    if operation_type not in ("OPERATION_TYPE_BUY", "OPERATION_TYPE_SELL"):
                        continue
                    instrument_id = (
                        str(item.get("instrumentUid") or "").strip()
                        or str(item.get("figi") or "").strip()
                    )
                    fund = None
                    if instrument_id:
                        fund = self._funds.get_by_instrument_uid(instrument_id) or self._funds.get_by_figi(instrument_id)
                    fund_id = int(fund.id) if fund is not None else 0
                    try:
                        category_id = self._category_for_fund(user_id, fund_id) if fund_id else 0
                    except HTTPException:
                        category_id = 0
                    price_per_unit = money_value_to_decimal(item.get("price"))
                    if price_per_unit <= 0:
                        price_per_unit = Decimal("0.01")
                    total_amount = abs(money_value_to_decimal(item.get("payment")))
                    quantity = int(quotation_to_decimal(item.get("quantity")) or Decimal("0"))
                    op_id = str(item.get("id") or item.get("parentOperationId") or f"{instrument_id}:{operation_type}:{item.get('date')}")
                    dt_raw = str(item.get("date") or datetime.now(timezone.utc).isoformat())
                    out.append(
                        OrderHistoryItem(
                            id=_stable_int_id(op_id),
                            fund_id=fund_id,
                            category_id=category_id,
                            operation_type=str(item.get("type") or item.get("operationType") or ""),
                            quantity=quantity,
                            price_per_unit=price_per_unit,
                            total_amount=total_amount,
                            executed_at=datetime.fromisoformat(dt_raw.replace("Z", "+00:00")),
                            note="Live T-Invest REST",
                            broker_order_id=(str(item.get("id") or "").strip() or None),
                            execution_status=str(item.get("state") or "").strip() or None,
                        )
                    )
                if out:
                    return out

        rows = self._tx_repo.list_for_user(user_id)
        out = []
        for t in rows:
            note = (t.note or "").strip()
            if not note.startswith(_NOTE_PREFIX):
                continue
            m_oid = _RE_ORDER_ID.search(note)
            m_st = _RE_STATUS.search(note)
            out.append(
                OrderHistoryItem(
                    id=int(t.id),
                    fund_id=int(t.fund_id),
                    category_id=int(t.category_id),
                    operation_type=str(t.operation_type),
                    quantity=int(t.quantity),
                    price_per_unit=Decimal(t.price_per_unit),
                    total_amount=Decimal(t.total_amount),
                    executed_at=t.executed_at,
                    note=note,
                    broker_order_id=(m_oid.group(1).strip() if m_oid else None),
                    execution_status=(m_st.group(1).strip() if m_st else None),
                )
            )
        return out
