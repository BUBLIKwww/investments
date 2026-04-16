"""investment_transactions ledger and portfolio rebuild source

Revision ID: d4e8b2a1c3f0
Revises: 7a2c1f9b4d10
Create Date: 2026-04-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e8b2a1c3f0"
down_revision: Union[str, None] = "7a2c1f9b4d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "investment_transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("fund_id", sa.Integer(), nullable=False),
        sa.Column("operation_type", sa.String(length=8), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price_per_unit", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["strategy_categories.id"]),
        sa.ForeignKeyConstraint(["fund_id"], ["funds.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_investment_transactions_fund_id"), "investment_transactions", ["fund_id"], unique=False)
    op.create_index(op.f("ix_investment_transactions_category_id"), "investment_transactions", ["category_id"], unique=False)
    op.create_index(op.f("ix_investment_transactions_user_id"), "investment_transactions", ["user_id"], unique=False)

    op.execute(
        sa.text(
            """
            INSERT INTO investment_transactions (
                user_id, category_id, fund_id, operation_type, quantity,
                price_per_unit, total_amount, executed_at, note, created_at, updated_at
            )
            SELECT
                h.user_id,
                i.category_id,
                i.fund_id,
                'buy',
                i.purchased_units,
                i.price_used,
                i.actual_allocated_amount,
                h.created_at,
                'Импорт из пополнения #' || h.id,
                h.created_at,
                h.created_at
            FROM topup_history h
            JOIN topup_items i ON i.topup_history_id = h.id
            WHERE i.purchased_units > 0
            """
        )
    )
    op.execute(sa.text("DELETE FROM portfolio_positions"))


def downgrade() -> None:
    op.drop_index(op.f("ix_investment_transactions_user_id"), table_name="investment_transactions")
    op.drop_index(op.f("ix_investment_transactions_category_id"), table_name="investment_transactions")
    op.drop_index(op.f("ix_investment_transactions_fund_id"), table_name="investment_transactions")
    op.drop_table("investment_transactions")
