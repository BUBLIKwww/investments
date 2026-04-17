"""funds: instrument_uid + figi for T-Invest API

Revision ID: e3f4a5b6c7d8
Revises: d4e8b2a1c3f0
Create Date: 2026-04-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, None] = "d4e8b2a1c3f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("funds") as batch:
        batch.add_column(sa.Column("instrument_uid", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("figi", sa.String(length=64), nullable=True))
        batch.alter_column(
            "figi_or_uid",
            existing_type=sa.String(length=64),
            type_=sa.String(length=128),
            existing_nullable=False,
        )
    op.create_index(op.f("ix_funds_instrument_uid"), "funds", ["instrument_uid"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_funds_instrument_uid"), table_name="funds")
    with op.batch_alter_table("funds") as batch:
        batch.alter_column(
            "figi_or_uid",
            existing_type=sa.String(length=128),
            type_=sa.String(length=64),
            existing_nullable=False,
        )
        batch.drop_column("figi")
        batch.drop_column("instrument_uid")
