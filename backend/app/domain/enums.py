from enum import Enum


class TopupMode(str, Enum):
    STRICT = "strict"
    MAXIMIZE = "maximize"
    SMART = "smart"


class TransactionOperationType(str, Enum):
    BUY = "buy"
    SELL = "sell"
