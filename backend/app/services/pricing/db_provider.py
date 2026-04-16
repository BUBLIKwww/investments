from datetime import datetime
from decimal import Decimal

from app.domain.money import q_price, to_decimal
from app.models.fund import Fund


class DbPricingProvider:
    """Uses `Fund.price` from DB. Replace with a real market provider later."""

    def get_unit_price(self, fund: Fund, *, at_moment: datetime | None = None) -> Decimal:
        _ = at_moment
        return q_price(to_decimal(fund.price))
