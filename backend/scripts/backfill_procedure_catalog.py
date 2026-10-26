"""Idempotent backfill script for procedure code and category.

Sets code and category on existing procedure rows whose name exactly matches
a catalog name. Never touches price, never creates rows.
Dry-run by default; run with --apply to commit changes.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure backend structure is visible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.data.default_procedures import PROCEDURES_BY_NAME
from backend.database import system_session_scope
from backend.models.clinical import Procedure


async def run_backfill(
    db: AsyncSession,
    apply: bool = False,
) -> dict[str, Any]:
    """Execute catalog backfill over all existing procedures.

    Args:
        db: Active AsyncSession (typically system/admin scope).
        apply: If True, commits changes; if False, executes a dry-run without persisting.

    Returns:
        Summary dict containing counts per tenant and total updates.
    """
    stmt = select(Procedure).order_by(Procedure.tenant_id.asc(), Procedure.id.asc())
    result = await db.execute(stmt)
    procedures = result.scalars().all()

    tenant_counts: dict[Any, dict[str, int]] = defaultdict(lambda: {"examined": 0, "updated": 0, "unchanged": 0, "unmatched": 0})
    total_examined = 0
    total_updated = 0

    for proc in procedures:
        t_key = proc.tenant_id
        stats = tenant_counts[t_key]
        stats["examined"] += 1
        total_examined += 1

        catalog_entry = PROCEDURES_BY_NAME.get(proc.name)
        if not catalog_entry:
            stats["unmatched"] += 1
            continue

        needs_code = proc.code != catalog_entry.code
        needs_category = proc.category != catalog_entry.category

        if needs_code or needs_category:
            if apply:
                proc.code = catalog_entry.code
                proc.category = catalog_entry.category
            stats["updated"] += 1
            total_updated += 1
        else:
            stats["unchanged"] += 1

    if apply:
        await db.commit()
    else:
        await db.rollback()

    return {
        "dry_run": not apply,
        "total_examined": total_examined,
        "total_updated": total_updated,
        "tenant_counts": dict(tenant_counts),
    }


def format_backfill_report(summary: dict[str, Any]) -> str:
    lines = [
        "=" * 60,
        f"PROCEDURE CATALOG BACKFILL REPORT ({'DRY-RUN' if summary['dry_run'] else 'APPLIED'})",
        "=" * 60,
        f"Total rows examined: {summary['total_examined']}",
        f"Total rows to update / updated: {summary['total_updated']}",
        "-" * 60,
        "Counts per tenant:",
    ]
    for tenant_id, stats in sorted(
        summary["tenant_counts"].items(),
        key=lambda x: (x[0] is not None, x[0] or 0),
    ):
        label = f"Tenant {tenant_id}" if tenant_id is not None else "Global (tenant_id=None)"
        lines.append(
            f"  {label:<25}: {stats['examined']} examined, {stats['updated']} updated, {stats['unchanged']} unchanged, {stats['unmatched']} unmatched"
        )
    lines.append("=" * 60)
    if summary["dry_run"]:
        lines.append("[DRY-RUN] No changes were persisted. Use --apply to execute.")
    else:
        lines.append("[SUCCESS] All changes successfully applied and committed.")
    lines.append("=" * 60)
    return "\n".join(lines)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill procedure code and category.")
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Apply changes to database. Default is dry-run.",
    )
    args = parser.parse_args()

    async with system_session_scope() as db:
        summary = await run_backfill(db, apply=args.apply)
        print(format_backfill_report(summary))


if __name__ == "__main__":
    asyncio.run(main())
