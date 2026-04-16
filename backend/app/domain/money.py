from decimal import ROUND_HALF_UP, Decimal

MONEY = Decimal("0.01")
PRICE = Decimal("0.000001")
SHARE = Decimal("1")


def q_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def q_price(value: Decimal) -> Decimal:
    return value.quantize(PRICE, rounding=ROUND_HALF_UP)


def q_share(value: Decimal) -> Decimal:
    return value.quantize(SHARE, rounding=ROUND_HALF_UP)


def to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
