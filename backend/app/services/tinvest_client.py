"""Минимальный REST‑клиент T‑Invest API."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from decimal import Decimal

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings


_REST_API = "https://invest-public-api.tbank.ru/rest"
_REST_API_SANDBOX = "https://sandbox-invest-public-api.tbank.ru/rest"


def _decimal_from_parts(units: object, nano: object) -> Decimal:
    try:
        whole = Decimal(str(units or 0))
    except Exception:
        whole = Decimal("0")
    try:
        frac = Decimal(str(nano or 0)) / Decimal("1000000000")
    except Exception:
        frac = Decimal("0")
    return whole + frac


def quotation_to_decimal(value: dict | None) -> Decimal:
    if not value:
        return Decimal("0")
    return _decimal_from_parts(value.get("units"), value.get("nano"))


def money_value_to_decimal(value: dict | None) -> Decimal:
    if not value:
        return Decimal("0")
    return _decimal_from_parts(value.get("units"), value.get("nano"))


class TinvestRestClient:
    def __init__(self, settings: Settings) -> None:
        token = (settings.TINVEST_TOKEN or "").strip()
        if not token:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="TINVEST_TOKEN не задан.",
            )
        base_url = _REST_API_SANDBOX if settings.TINVEST_USE_SANDBOX else _REST_API
        self._http = httpx.Client(
            base_url=base_url,
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

    def close(self) -> None:
        self._http.close()

    def _post(self, method: str, payload: dict) -> dict:
        try:
            resp = self._http.post(method, json=payload)
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"T-Invest REST недоступен: {str(e)[:300]}",
            ) from e

        if resp.status_code >= 400:
            snippet = (resp.text or "")[:300]
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY if resp.status_code >= 500 else resp.status_code,
                detail=f"T-Invest REST HTTP {resp.status_code}: {snippet or 'empty response'}",
            )
        try:
            data = resp.json()
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="T-Invest REST вернул некорректный JSON",
            ) from e
        return data if isinstance(data, dict) else {}

    def get_accounts(self, *, status_name: str = "ACCOUNT_STATUS_ALL") -> list[dict]:
        data = self._post(
            "/tinkoff.public.invest.api.contract.v1.UsersService/GetAccounts",
            {"status": status_name},
        )
        rows = data.get("accounts")
        return rows if isinstance(rows, list) else []

    def get_portfolio(self, account_id: str, *, currency: str = "RUB") -> dict:
        return self._post(
            "/tinkoff.public.invest.api.contract.v1.OperationsService/GetPortfolio",
            {"accountId": account_id, "currency": currency},
        )

    def get_withdraw_limits(self, account_id: str) -> dict:
        return self._post(
            "/tinkoff.public.invest.api.contract.v1.OperationsService/GetWithdrawLimits",
            {"accountId": account_id},
        )

    def get_operations_by_cursor(self, account_id: str, *, limit: int = 100) -> dict:
        return self._post(
            "/tinkoff.public.invest.api.contract.v1.OperationsService/GetOperationsByCursor",
            {"accountId": account_id, "limit": int(limit)},
        )

    def post_order(
        self,
        *,
        instrument_id: str,
        quantity: int,
        account_id: str,
        order_id: str,
        direction: str,
        order_type: str = "ORDER_TYPE_MARKET",
    ) -> dict:
        payload = {
            "instrumentId": instrument_id,
            "quantity": str(int(quantity)),
            "accountId": account_id,
            "orderId": order_id,
            "direction": direction,
            "orderType": order_type,
        }
        return self._post(
            "/tinkoff.public.invest.api.contract.v1.OrdersService/PostOrder",
            payload,
        )

    def find_instrument(self, query: str) -> list[dict]:
        data = self._post(
            "/tinkoff.public.invest.api.contract.v1.InstrumentsService/FindInstrument",
            {"query": query, "apiTradeAvailableFlag": True},
        )
        rows = data.get("instruments")
        return rows if isinstance(rows, list) else []

    def get_last_prices(self, instrument_ids: list[str]) -> list[dict]:
        data = self._post(
            "/tinkoff.public.invest.api.contract.v1.MarketDataService/GetLastPrices",
            {"instrumentId": instrument_ids},
        )
        rows = data.get("lastPrices")
        return rows if isinstance(rows, list) else []

    def get_instrument_by(self, *, id_type: str, instrument_id: str) -> dict | None:
        data = self._post(
            "/tinkoff.public.invest.api.contract.v1.InstrumentsService/GetInstrumentBy",
            {"idType": id_type, "id": instrument_id},
        )
        row = data.get("instrument")
        return row if isinstance(row, dict) else None


@contextmanager
def tinvest_client(settings: Settings) -> Generator[object, None, None]:
    client = TinvestRestClient(settings)
    try:
        yield client
    finally:
        client.close()
