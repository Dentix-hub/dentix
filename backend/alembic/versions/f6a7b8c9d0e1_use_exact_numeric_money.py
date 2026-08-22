"""use exact numeric types and enforce financial invariants

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-22 18:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MONEY_COLUMNS = (
    ("payments", "amount", 14, 2),
    ("expenses", "cost", 14, 2),
    ("salary_payments", "amount", 14, 2),
    ("lab_payments", "amount", 14, 2),
    ("treatments", "cost", 14, 2),
    ("treatments", "discount", 14, 2),
    ("treatments", "unit_price", 14, 2),
    ("lab_orders", "cost", 14, 2),
    ("lab_orders", "price_to_patient", 14, 2),
    ("procedures", "price", 14, 2),
    ("subscription_plans", "price", 14, 2),
    ("subscription_payments", "amount", 14, 2),
    ("subscription_checkouts", "expected_amount", 14, 2),
    ("tenants", "total_revenue", 14, 2),
    ("users", "fixed_salary", 14, 2),
    ("users", "per_appointment_fee", 14, 2),
    ("price_lists", "copay_fixed", 14, 2),
    ("price_list_items", "price", 14, 2),
    ("daily_system_stats", "total_revenue", 14, 2),
    ("users", "commission_percent", 7, 4),
    ("price_lists", "coverage_percent", 7, 4),
    ("price_lists", "copay_percent", 7, 4),
    ("price_list_items", "discount_percent", 7, 4),
    ("materials", "standard_price", 18, 6),
    ("batches", "cost_per_unit", 18, 6),
    ("treatment_material_usages", "cost_calculated", 18, 6),
    ("ai_logs", "cost", 18, 6),
)


CHECK_CONSTRAINTS = (
    ("payments", "ck_payments_amount_positive", "amount > 0"),
    ("expenses", "ck_expenses_cost_positive", "cost > 0"),
    ("salary_payments", "ck_salary_payments_amount_nonnegative", "amount >= 0"),
    ("lab_payments", "ck_lab_payments_amount_positive", "amount > 0"),
    ("treatments", "ck_treatments_cost_nonnegative", "cost >= 0"),
    ("treatments", "ck_treatments_discount_nonnegative", "discount >= 0"),
    ("treatments", "ck_treatments_discount_not_above_cost", "discount <= cost"),
    ("lab_orders", "ck_lab_orders_cost_nonnegative", "cost >= 0"),
    (
        "lab_orders",
        "ck_lab_orders_patient_price_nonnegative",
        "price_to_patient >= 0",
    ),
    ("procedures", "ck_procedures_price_nonnegative", "price >= 0"),
    (
        "subscription_plans",
        "ck_subscription_plans_price_nonnegative",
        "price >= 0",
    ),
    (
        "subscription_payments",
        "ck_subscription_payments_amount_positive",
        "amount > 0",
    ),
    (
        "subscription_checkouts",
        "ck_subscription_checkouts_amount_nonnegative",
        "expected_amount >= 0",
    ),
    ("tenants", "ck_tenants_revenue_nonnegative", "total_revenue >= 0"),
    (
        "users",
        "ck_users_commission_percent_range",
        "commission_percent >= 0 AND commission_percent <= 100",
    ),
    ("users", "ck_users_fixed_salary_nonnegative", "fixed_salary >= 0"),
    (
        "users",
        "ck_users_appointment_fee_nonnegative",
        "per_appointment_fee >= 0",
    ),
    (
        "price_lists",
        "ck_price_lists_coverage_range",
        "coverage_percent >= 0 AND coverage_percent <= 100",
    ),
    (
        "price_lists",
        "ck_price_lists_copay_range",
        "copay_percent >= 0 AND copay_percent <= 100",
    ),
    ("price_lists", "ck_price_lists_copay_nonnegative", "copay_fixed >= 0"),
    (
        "price_list_items",
        "ck_price_list_items_price_nonnegative",
        "price >= 0",
    ),
    (
        "price_list_items",
        "ck_price_list_items_discount_range",
        "discount_percent >= 0 AND discount_percent <= 100",
    ),
    (
        "materials",
        "ck_materials_standard_price_nonnegative",
        "standard_price IS NULL OR standard_price >= 0",
    ),
    ("batches", "ck_batches_unit_cost_nonnegative", "cost_per_unit >= 0"),
    (
        "treatment_material_usages",
        "ck_treatment_material_usage_cost_nonnegative",
        "cost_calculated IS NULL OR cost_calculated >= 0",
    ),
    ("ai_logs", "ck_ai_logs_cost_nonnegative", "cost >= 0"),
    (
        "daily_system_stats",
        "ck_daily_system_stats_revenue_nonnegative",
        "total_revenue >= 0",
    ),
)


def _preflight_existing_values() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    precision_violations = []
    for table, column, _, scale in MONEY_COLUMNS:
        count = bind.execute(
            sa.text(
                f'SELECT COUNT(*) FROM "{table}" '
                f'WHERE "{column}" IS NOT NULL '
                f'AND "{column}"::numeric <> ROUND("{column}"::numeric, :scale)'
            ),
            {"scale": scale},
        ).scalar_one()
        if count:
            precision_violations.append(f"{table}.{column}={count}")

    invariant_violations = []
    for table, constraint_name, expression in CHECK_CONSTRAINTS:
        count = bind.execute(
            sa.text(f'SELECT COUNT(*) FROM "{table}" WHERE NOT ({expression})')
        ).scalar_one()
        if count:
            invariant_violations.append(f"{constraint_name}={count}")

    if precision_violations or invariant_violations:
        details = "; ".join(precision_violations + invariant_violations)
        raise RuntimeError(
            "Financial Numeric migration requires manual review; no values were "
            f"changed. Violations: {details}"
        )


def upgrade() -> None:
    _preflight_existing_values()

    for table, column, precision, scale in MONEY_COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.Float(),
            type_=sa.Numeric(precision=precision, scale=scale),
            postgresql_using=f'ROUND("{column}"::numeric, {scale})',
        )

    for table, constraint_name, expression in CHECK_CONSTRAINTS:
        op.create_check_constraint(constraint_name, table, expression)


def downgrade() -> None:
    for table, constraint_name, _ in reversed(CHECK_CONSTRAINTS):
        op.drop_constraint(constraint_name, table, type_="check")

    for table, column, precision, scale in reversed(MONEY_COLUMNS):
        op.alter_column(
            table,
            column,
            existing_type=sa.Numeric(precision=precision, scale=scale),
            type_=sa.Float(),
            postgresql_using=f'"{column}"::double precision',
        )
