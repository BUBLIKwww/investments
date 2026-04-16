from decimal import Decimal
from typing import Protocol

from app.models.fund import Fund


class PricingProvider(Protocol):
    def get_unit_price(self, fund: Fund, *, at_moment=None) -> Decimal: ...
