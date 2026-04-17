from decimal import ROUND_HALF_UP, Decimal

MONEY = Decimal("0.01")
PRICE = Decimal("0.000001")
SHARE = Decimal("1")


def _coerce_decimal(value: object) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return Decimal(int(value))
    if isinstance(value, int):
        return Decimal(value)
    return Decimal(str(value))


def q_money(value: object) -> Decimal:
    if not isinstance(value, Decimal):
        value = _coerce_decimal(value)
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def q_price(value: object) -> Decimal:
    if not isinstance(value, Decimal):
        value = _coerce_decimal(value)
    return value.quantize(PRICE, rounding=ROUND_HALF_UP)


def q_share(value: object) -> Decimal:
    if not isinstance(value, Decimal):
        value = _coerce_decimal(value)
    return value.quantize(SHARE, rounding=ROUND_HALF_UP)


def to_decimal(value: object) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
