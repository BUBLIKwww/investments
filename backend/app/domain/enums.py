from enum import Enum


class TopupMode(str, Enum):
    STRICT = "strict"
    MAXIMIZE = "maximize"
    SMART = "smart"
