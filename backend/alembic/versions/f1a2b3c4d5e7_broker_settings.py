"""broker_settings: выбранный счёт T‑Invest

Revision ID: f1a2b3c4d5e7
Revises: e3f4a5b6c7d8
Create Date: 2026-04-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f1a2b3c4d5e7"
down_revision: Union[str, None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "broker_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("selected_account_id", sa.String(length=64), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(sa.text("INSERT INTO broker_settings (id, selected_account_id) VALUES (1, NULL)"))


def downgrade() -> None:
    op.drop_table("broker_settings")
