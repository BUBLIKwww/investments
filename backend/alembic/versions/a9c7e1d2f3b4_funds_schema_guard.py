"""funds schema guard for legacy postgres databases

Revision ID: a9c7e1d2f3b4
Revises: f1a2b3c4d5e7
Create Date: 2026-04-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a9c7e1d2f3b4"
down_revision: Union[str, None] = "f1a2b3c4d5e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    statements = [
        "ALTER TABLE IF EXISTS funds ADD COLUMN IF NOT EXISTS figi_or_uid VARCHAR(128) DEFAULT ''",
        "ALTER TABLE IF EXISTS funds ADD COLUMN IF NOT EXISTS instrument_uid VARCHAR(128)",
        "ALTER TABLE IF EXISTS funds ADD COLUMN IF NOT EXISTS figi VARCHAR(64)",
        "ALTER TABLE IF EXISTS funds ADD COLUMN IF NOT EXISTS lot INTEGER DEFAULT 1",
        "ALTER TABLE IF EXISTS funds ADD COLUMN IF NOT EXISTS price NUMERIC(18, 6) DEFAULT 0",
        "ALTER TABLE IF EXISTS funds ADD COLUMN IF NOT EXISTS currency VARCHAR(8) DEFAULT 'RUB'",
        "ALTER TABLE IF EXISTS funds ADD COLUMN IF NOT EXISTS last_price_updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE IF EXISTS funds ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
        "UPDATE funds SET figi_or_uid = COALESCE(NULLIF(figi_or_uid, ''), ticker, '') WHERE figi_or_uid IS NULL OR figi_or_uid = ''",
        "UPDATE funds SET lot = 1 WHERE lot IS NULL",
        "UPDATE funds SET price = 0 WHERE price IS NULL",
        "UPDATE funds SET currency = 'RUB' WHERE currency IS NULL OR currency = ''",
        "UPDATE funds SET last_price_updated_at = CURRENT_TIMESTAMP WHERE last_price_updated_at IS NULL",
        "UPDATE funds SET is_active = TRUE WHERE is_active IS NULL",
    ]
    for sql in statements:
        op.execute(sa.text(sql))


def downgrade() -> None:
    pass
