from pydantic import BaseModel, Field


class BrokerAccountRead(BaseModel):
    id: str
    name: str
    type: str = Field(description="tinkoff | iis | invest_box | unknown")
    status: str = Field(description="open | closed | new | unknown")
    access_level: str = Field(description="full | read_only | none | unknown")


class BrokerSettingsRead(BaseModel):
    selected_account_id: str | None
    default_account_id_env: str | None = Field(
        default=None,
        description="TINVEST_DEFAULT_ACCOUNT_ID из окружения (подсказка, не секрет)",
    )


class BrokerSettingsUpdate(BaseModel):
    selected_account_id: str | None = Field(description="ID счёта из GET /broker/accounts; null — сбросить")
