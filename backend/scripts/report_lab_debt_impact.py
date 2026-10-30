"""Lab Debt Impact Report (Slice L6).

Read-only script to analyze existing lab orders, lab payments, resulting lab debt,
historical manual Laboratory expenses, and heuristic double-count pairs per tenant.

NO WRITES: Strictly read-only analysis. No backfill, no data modifications.

Usage:
    uv run python backend/scripts/report_lab_debt_impact.py
    uv run python backend/scripts/report_lab_debt_impact.py --tenant-id 1
    uv run python backend/scripts/report_lab_debt_impact.py --format markdown
    uv run python backend/scripts/report_lab_debt_impact.py --format json
"""

import argparse
import asyncio
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure project root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# If DATABASE_URL is not set, attempt loading .env or fallback to local test DB
if not os.getenv("DATABASE_URL"):
    from dotenv import load_dotenv
    for env_candidate in [
        os.path.join(PROJECT_ROOT, ".env"),
        os.path.join(PROJECT_ROOT, "backend", ".env"),
    ]:
        if os.path.exists(env_candidate):
            load_dotenv(env_candidate)
            break
    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = (
            os.getenv("SYSTEM_DATABASE_URL")
            or "postgresql://dentix_ci_system:dentix_ci_system_pass@localhost:5432/dentix_test"
        )

from backend import models  # noqa: E402
from backend.core.money import as_decimal, quantize_money  # noqa: E402

logger = logging.getLogger("report_lab_debt_impact")

LAB_CATEGORY_VARIANTS: Set[str] = {
    "laboratory",
    "lab",
    "معمل",
    "معامل",
    "معامل وتركيبات",
    "معامل وتركيبات خارجية",
}


@dataclass
class DoubleCountCandidate:
    expense_id: int
    expense_date: str
    expense_cost: float
    expense_item_name: str
    expense_notes: Optional[str]
    order_id: int
    order_date: str
    order_cost: float
    order_work_type: str
    laboratory_id: Optional[int]
    patient_id: Optional[int]
    days_difference: int


@dataclass
class TenantImpactReport:
    tenant_id: Optional[int]
    tenant_name: str
    active_orders_count: int
    active_orders_sum: float
    payments_count: int
    payments_sum: float
    resulting_debt: float
    lab_expenses_count: int
    lab_expenses_sum: float
    double_count_pairs_count: int
    double_count_estimated_amount: float
    double_count_pairs: List[DoubleCountCandidate] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _to_date(val: Any) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        return datetime.fromisoformat(str(val)).date()
    except Exception:
        return None


def is_laboratory_category(category: Optional[str]) -> bool:
    if not category:
        return False
    normalized = category.strip().lower()
    return normalized in LAB_CATEGORY_VARIANTS or "laborator" in normalized or "معمل" in normalized


def find_double_count_pairs(
    expenses: List[models.Expense],
    orders: List[models.LabOrder],
    max_days: int = 3,
) -> Tuple[List[DoubleCountCandidate], float]:
    """Find candidate double-count pairs between historical Lab expenses and LabOrders.

    Heuristic rule per brief:
    expense.cost == order.cost within +-3 days of order_date.
    """
    candidates: List[DoubleCountCandidate] = []
    matched_expense_ids: Set[int] = set()
    matched_order_ids: Set[int] = set()
    greedy_sum = Decimal("0.00")

    # Sort pairs by smallest date delta first for deterministic greedy matching
    potential_matches: List[Tuple[int, models.Expense, models.LabOrder]] = []

    for exp in expenses:
        exp_date = _to_date(exp.date)
        if not exp_date or exp.cost is None:
            continue
        exp_cost = quantize_money(as_decimal(exp.cost))

        for ord_ in orders:
            ord_date = _to_date(ord_.order_date)
            if not ord_date or ord_.cost is None:
                continue
            ord_cost = quantize_money(as_decimal(ord_.cost))

            if exp_cost == ord_cost:
                diff = abs((exp_date - ord_date).days)
                if diff <= max_days:
                    potential_matches.append((diff, exp, ord_))

    # Sort candidate matches by absolute days diff ascending
    potential_matches.sort(key=lambda item: (item[0], item[1].id, item[2].id))

    for diff, exp, ord_ in potential_matches:
        candidate = DoubleCountCandidate(
            expense_id=exp.id,
            expense_date=str(_to_date(exp.date)),
            expense_cost=float(quantize_money(as_decimal(exp.cost))),
            expense_item_name=exp.item_name or "",
            expense_notes=exp.notes,
            order_id=ord_.id,
            order_date=str(_to_date(ord_.order_date)),
            order_cost=float(quantize_money(as_decimal(ord_.cost))),
            order_work_type=ord_.work_type or "",
            laboratory_id=ord_.laboratory_id,
            patient_id=ord_.patient_id,
            days_difference=diff,
        )
        candidates.append(candidate)

        if exp.id not in matched_expense_ids and ord_.id not in matched_order_ids:
            matched_expense_ids.add(exp.id)
            matched_order_ids.add(ord_.id)
            greedy_sum += quantize_money(as_decimal(exp.cost))

    return candidates, float(greedy_sum)


async def collect_tenant_impact(
    session: AsyncSession,
    tenant_id: Optional[int],
    tenant_name: str,
) -> TenantImpactReport:
    """Read-only analysis of lab orders, payments, debt, expenses, and heuristic pairing for one tenant."""
    # 1. Non-cancelled orders with cost > 0
    orders_query = select(models.LabOrder).where(
        models.LabOrder.cost > 0,
        func.lower(func.coalesce(models.LabOrder.status, "")) != "cancelled",
    )
    if tenant_id is not None:
        orders_query = orders_query.where(models.LabOrder.tenant_id == tenant_id)
    else:
        orders_query = orders_query.where(models.LabOrder.tenant_id.is_(None))
    orders_query = orders_query.order_by(models.LabOrder.order_date.asc(), models.LabOrder.id.asc())

    orders_res = await session.execute(orders_query)
    orders = list(orders_res.scalars().all())

    orders_count = len(orders)
    orders_sum = quantize_money(sum((as_decimal(o.cost) for o in orders), Decimal("0.00")))

    # 2. Lab payments
    payments_query = select(models.LabPayment)
    if tenant_id is not None:
        payments_query = payments_query.where(models.LabPayment.tenant_id == tenant_id)
    else:
        payments_query = payments_query.where(models.LabPayment.tenant_id.is_(None))
    payments_query = payments_query.order_by(models.LabPayment.date.asc(), models.LabPayment.id.asc())

    payments_res = await session.execute(payments_query)
    payments = list(payments_res.scalars().all())

    payments_count = len(payments)
    payments_sum = quantize_money(sum((as_decimal(p.amount) for p in payments), Decimal("0.00")))

    # 3. Resulting debt
    resulting_debt = quantize_money(orders_sum - payments_sum)

    # 4. Expense rows with category Laboratory
    expenses_query = select(models.Expense)
    if tenant_id is not None:
        expenses_query = expenses_query.where(models.Expense.tenant_id == tenant_id)
    else:
        expenses_query = expenses_query.where(models.Expense.tenant_id.is_(None))
    expenses_query = expenses_query.order_by(models.Expense.date.asc(), models.Expense.id.asc())

    expenses_res = await session.execute(expenses_query)
    all_expenses = list(expenses_res.scalars().all())
    lab_expenses = [e for e in all_expenses if is_laboratory_category(e.category)]

    lab_expenses_count = len(lab_expenses)
    lab_expenses_sum = quantize_money(sum((as_decimal(e.cost) for e in lab_expenses), Decimal("0.00")))

    # 5. Heuristic double-count pairs (expense cost == order cost within +-3 days)
    double_count_pairs, double_count_amount = find_double_count_pairs(lab_expenses, orders, max_days=3)

    return TenantImpactReport(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        active_orders_count=orders_count,
        active_orders_sum=float(orders_sum),
        payments_count=payments_count,
        payments_sum=float(payments_sum),
        resulting_debt=float(resulting_debt),
        lab_expenses_count=lab_expenses_count,
        lab_expenses_sum=float(lab_expenses_sum),
        double_count_pairs_count=len(double_count_pairs),
        double_count_estimated_amount=double_count_amount,
        double_count_pairs=double_count_pairs,
    )


async def generate_impact_reports(
    session: AsyncSession,
    target_tenant_id: Optional[int] = None,
) -> List[TenantImpactReport]:
    """Execute read-only queries across tenants."""
    reports: List[TenantImpactReport] = []

    if target_tenant_id is not None:
        tenant_res = await session.execute(
            select(models.Tenant.id, models.Tenant.name).where(models.Tenant.id == target_tenant_id)
        )
        row = tenant_res.first()
        t_name = row[1] if row else f"Tenant #{target_tenant_id}"
        report = await collect_tenant_impact(session, target_tenant_id, t_name)
        reports.append(report)
        return reports

    # Query all tenants
    tenants_res = await session.execute(
        select(models.Tenant.id, models.Tenant.name).order_by(models.Tenant.id.asc())
    )
    tenants = tenants_res.all()

    for tid, tname in tenants:
        report = await collect_tenant_impact(session, tid, tname or f"Tenant #{tid}")
        reports.append(report)

    # Check for legacy rows with tenant_id IS NULL
    null_tenant_res = await session.execute(
        select(
            func.count(models.LabOrder.id)
        ).where(models.LabOrder.tenant_id.is_(None))
    )
    null_orders = null_tenant_res.scalar() or 0

    null_payments_res = await session.execute(
        select(func.count(models.LabPayment.id)).where(models.LabPayment.tenant_id.is_(None))
    )
    null_payments = null_payments_res.scalar() or 0

    null_exp_res = await session.execute(
        select(func.count(models.Expense.id)).where(models.Expense.tenant_id.is_(None))
    )
    null_expenses = null_exp_res.scalar() or 0

    if null_orders > 0 or null_payments > 0 or null_expenses > 0:
        legacy_report = await collect_tenant_impact(session, None, "Legacy (NULL Tenant)")
        reports.append(legacy_report)

    return reports


def format_text_report(reports: List[TenantImpactReport]) -> str:
    lines: List[str] = []
    lines.append("=" * 88)
    lines.append(" DENTIX LAB DEBT IMPACT REPORT (SLICE L6 — READ ONLY)")
    lines.append("=" * 88)

    for r in reports:
        lines.append(f"\n--- Tenant: {r.tenant_name} (ID: {r.tenant_id if r.tenant_id is not None else 'NULL'}) ---")
        lines.append(f"  • Non-Cancelled Orders (cost > 0) : {r.active_orders_count:4d} orders | Sum: {r.active_orders_sum:12.2f} EGP")
        lines.append(f"  • Recorded Lab Payments          : {r.payments_count:4d} pmts   | Sum: {r.payments_sum:12.2f} EGP")
        lines.append(f"  • Resulting Lab Debt (Accrual)   : {r.resulting_debt:12.2f} EGP (Orders Sum - Payments Sum)")
        lines.append(f"  • Category 'Laboratory' Expenses : {r.lab_expenses_count:4d} rows   | Sum: {r.lab_expenses_sum:12.2f} EGP")
        lines.append(f"  • Heuristic Double-Count Pairs   : {r.double_count_pairs_count:4d} pairs  | Est. Amount: {r.double_count_estimated_amount:10.2f} EGP")

        if r.double_count_pairs:
            lines.append("    Candidate Pairs (cost equal within ±3 days):")
            for p in r.double_count_pairs[:10]:
                lines.append(
                    f"      - Expense #{p.expense_id} ({p.expense_date}, {p.expense_cost:.2f} EGP, '{p.expense_item_name}') <-> "
                    f"Order #{p.order_id} ({p.order_date}, {p.order_cost:.2f} EGP, '{p.order_work_type}') [diff: {p.days_difference}d]"
                )
            if len(r.double_count_pairs) > 10:
                lines.append(f"      ... and {len(r.double_count_pairs) - 10} more pairs")

    lines.append("\n" + "=" * 88)
    total_orders = sum(r.active_orders_count for r in reports)
    total_orders_sum = sum(r.active_orders_sum for r in reports)
    total_payments = sum(r.payments_count for r in reports)
    total_payments_sum = sum(r.payments_sum for r in reports)
    total_debt = sum(r.resulting_debt for r in reports)
    total_expenses = sum(r.lab_expenses_count for r in reports)
    total_expenses_sum = sum(r.lab_expenses_sum for r in reports)
    total_double_pairs = sum(r.double_count_pairs_count for r in reports)
    total_double_amount = sum(r.double_count_estimated_amount for r in reports)

    lines.append(" TOTALS ACROSS ALL ANALYZED TENANTS:")
    lines.append(f"  • Total Active Lab Orders : {total_orders} ({total_orders_sum:.2f} EGP)")
    lines.append(f"  • Total Lab Payments      : {total_payments} ({total_payments_sum:.2f} EGP)")
    lines.append(f"  • Net Resulting Lab Debt  : {total_debt:.2f} EGP")
    lines.append(f"  • Total Lab Expenses      : {total_expenses} ({total_expenses_sum:.2f} EGP)")
    lines.append(f"  • Possible Double-Counts  : {total_double_pairs} pairs ({total_double_amount:.2f} EGP)")
    lines.append("=" * 88)
    return "\n".join(lines)


def format_markdown_report(reports: List[TenantImpactReport]) -> str:
    lines: List[str] = []
    lines.append("### Lab Debt Impact Report (Slice L6 — Read-Only)")
    lines.append("")
    lines.append("| Tenant ID | Tenant Name | Active Orders (Cost > 0) | Lab Payments | Resulting Lab Debt | Category 'Laboratory' Expenses | Possible Double-Count Pairs |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

    for r in reports:
        t_id = str(r.tenant_id) if r.tenant_id is not None else "NULL"
        orders_cell = f"{r.active_orders_count} ({r.active_orders_sum:,.2f} EGP)"
        pmts_cell = f"{r.payments_count} ({r.payments_sum:,.2f} EGP)"
        debt_cell = f"**{r.resulting_debt:,.2f} EGP**"
        exp_cell = f"{r.lab_expenses_count} ({r.lab_expenses_sum:,.2f} EGP)"
        dc_cell = f"{r.double_count_pairs_count} pairs ({r.double_count_estimated_amount:,.2f} EGP)"
        lines.append(f"| {t_id} | {r.tenant_name} | {orders_cell} | {pmts_cell} | {debt_cell} | {exp_cell} | {dc_cell} |")

    lines.append("")
    lines.append("> [!NOTE]")
    lines.append("> **Strictly read-only report.** No automatic backfill has been applied per brief section 4 (Slice L6).")
    lines.append("> Historical orders remain debt owed to labs unless owner approves a backfill strategy prior to `staging` -> `main` promotion.")

    return "\n".join(lines)


def resolve_database_url(cli_url: Optional[str] = None) -> str:
    """Resolve database URL following application precedence."""
    url = cli_url or os.getenv("SYSTEM_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        # Check default test postgres if available
        url = "postgresql://dentix_ci_system:dentix_ci_system_pass@localhost:5432/dentix_test"

    url = url.strip().strip("'").strip('"')
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


async def main_async(args: argparse.Namespace) -> int:
    db_url = resolve_database_url(args.db_url)
    # Mask password for logging
    masked = db_url.split("@")[-1] if "@" in db_url else db_url
    print(f"Connecting to database: {masked}", file=sys.stderr)

    engine = create_async_engine(db_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with session_factory() as session:
            reports = await generate_impact_reports(session, target_tenant_id=args.tenant_id)
            await session.rollback()  # Guaranteed read-only
    finally:
        await engine.dispose()

    if args.format == "json":
        print(json.dumps([r.to_dict() for r in reports], indent=2))
    elif args.format == "markdown":
        print(format_markdown_report(reports))
    else:
        print(format_text_report(reports))

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only Lab Debt Impact Report (Slice L6)")
    parser.add_argument("--tenant-id", type=int, default=None, help="Filter to specific tenant ID")
    parser.add_argument("--format", choices=["text", "markdown", "json"], default="text", help="Output format")
    parser.add_argument("--db-url", type=str, default=None, help="Database connection URL override")
    args = parser.parse_args()

    sys.exit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
