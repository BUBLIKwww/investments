"""mvp invest schema

Revision ID: 7a2c1f9b4d10
Revises: c0824d97343f
Create Date: 2026-04-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "7a2c1f9b4d10"
down_revision: Union[str, None] = "c0824d97343f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_if_exists(bind: sa.engine.Connection, table: str) -> None:
    if table in inspect(bind).get_table_names():
        op.drop_table(table)


def upgrade() -> None:
    bind = op.get_bind()

    _drop_if_exists(bind, "topup_items")
    _drop_if_exists(bind, "topup_history")
    _drop_if_exists(bind, "portfolio_positions")
    _drop_if_exists(bind, "strategies")
    _drop_if_exists(bind, "strategy_categories")
    _drop_if_exists(bind, "funds")

    op.create_table(
        "funds",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("figi_or_uid", sa.String(length=64), nullable=False),
        sa.Column("lot", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("currency", sa.String(length=8), server_default="RUB", nullable=False),
        sa.Column("last_price_updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_funds_figi_or_uid"), "funds", ["figi_or_uid"], unique=False)
    op.create_index(op.f("ix_funds_ticker"), "funds", ["ticker"], unique=True)

    op.create_table(
        "strategy_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("fund_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("target_percent", sa.Numeric(precision=9, scale=4), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.ForeignKeyConstraint(["fund_id"], ["funds.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "sort_order", name="uq_strategy_category_user_sort"),
    )
    op.create_index(op.f("ix_strategy_categories_fund_id"), "strategy_categories", ["fund_id"], unique=False)
    op.create_index(op.f("ix_strategy_categories_user_id"), "strategy_categories", ["user_id"], unique=False)

    op.create_table(
        "portfolio_positions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("fund_id", sa.Integer(), nullable=False),
        sa.Column("total_lots", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_units", sa.Integer(), server_default="0", nullable=False),
        sa.Column("invested_amount", sa.Numeric(precision=18, scale=2), server_default="0", nullable=False),
        sa.Column("average_buy_price", sa.Numeric(precision=18, scale=6), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["strategy_categories.id"]),
        sa.ForeignKeyConstraint(["fund_id"], ["funds.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "category_id", "fund_id", name="uq_portfolio_user_category_fund"),
    )
    op.create_index(op.f("ix_portfolio_positions_category_id"), "portfolio_positions", ["category_id"], unique=False)
    op.create_index(op.f("ix_portfolio_positions_fund_id"), "portfolio_positions", ["fund_id"], unique=False)
    op.create_index(op.f("ix_portfolio_positions_user_id"), "portfolio_positions", ["user_id"], unique=False)

    op.create_table(
        "topup_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("total_allocated_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("total_cash_remainder", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_topup_history_user_id"), "topup_history", ["user_id"], unique=False)

    op.create_table(
        "topup_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("topup_history_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("fund_id", sa.Integer(), nullable=False),
        sa.Column("target_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("actual_allocated_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("cash_remainder", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("price_used", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("lot_size", sa.Integer(), nullable=False),
        sa.Column("purchased_lots", sa.Integer(), nullable=False),
        sa.Column("purchased_units", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["strategy_categories.id"]),
        sa.ForeignKeyConstraint(["fund_id"], ["funds.id"]),
        sa.ForeignKeyConstraint(["topup_history_id"], ["topup_history.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_topup_items_category_id"), "topup_items", ["category_id"], unique=False)
    op.create_index(op.f("ix_topup_items_fund_id"), "topup_items", ["fund_id"], unique=False)
    op.create_index(op.f("ix_topup_items_topup_history_id"), "topup_items", ["topup_history_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    _drop_if_exists(bind, "topup_items")
    _drop_if_exists(bind, "topup_history")
    _drop_if_exists(bind, "portfolio_positions")
    _drop_if_exists(bind, "strategy_categories")
    _drop_if_exists(bind, "funds")

    op.create_table(
        "funds",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_funds_ticker"), "funds", ["ticker"], unique=True)

    op.create_table(
        "strategy_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_strategy_categories_slug"), "strategy_categories", ["slug"], unique=True)

    op.create_table(
        "portfolio_positions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("fund_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["fund_id"], ["funds.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_portfolio_positions_fund_id"), "portfolio_positions", ["fund_id"], unique=False)
    op.create_index(op.f("ix_portfolio_positions_user_id"), "portfolio_positions", ["user_id"], unique=False)

    op.create_table(
        "strategies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["strategy_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_strategies_category_id"), "strategies", ["category_id"], unique=False)

    op.create_table(
        "topup_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_topup_history_user_id"), "topup_history", ["user_id"], unique=False)
