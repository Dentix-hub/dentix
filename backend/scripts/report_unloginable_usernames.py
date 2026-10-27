"""Read-only diagnostic script for previously unloginable stored usernames.

Finds user rows where Python ``normalize_username(stored) != stored.strip().lower()``
(e.g., Arabic Alef variants أ/إ/آ, Teh Marbuta ة, or Alef Maksura ى) as well as rows
with leading/trailing whitespace (``stored != stored.strip()``).

Strictly read-only: performs no writes and outputs aggregate counts only by default
(no PHI is queried or printed).
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend import models  # noqa: E402
from backend.crud.auth import normalize_username  # noqa: E402
from backend.database import system_session_scope  # noqa: E402


async def find_unloginable_usernames(db: AsyncSession) -> dict[str, Any]:
    """Scan users table read-only and collect rows where normalization differs.

    Collects `(tenant_id, user_id, repr(stored_username))` tuples for rows where
    `normalize_username(stored) != stored.strip().lower()` and aggregate counts
    per tenant. No PHI columns (`full_name`, `email`, patient records) are read.
    """
    stmt = select(
        models.User.tenant_id,
        models.User.id,
        models.User.username,
    ).order_by(models.User.tenant_id.asc(), models.User.id.asc())

    result = await db.execute(stmt)
    user_rows = result.all()

    matched_rows: list[tuple[int | None, int, str]] = []
    whitespace_rows: list[tuple[int | None, int, str]] = []
    tenant_counts: dict[int | None, dict[str, int]] = defaultdict(
        lambda: {
            "examined": 0,
            "arabic_normalization_mismatch": 0,
            "outer_whitespace": 0,
        }
    )

    total_examined = 0
    for tenant_id, user_id, stored_username in user_rows:
        total_examined += 1
        stats = tenant_counts[tenant_id]
        stats["examined"] += 1

        stored = stored_username or ""
        if normalize_username(stored) != stored.strip().lower():
            matched_rows.append((tenant_id, user_id, repr(stored)))
            stats["arabic_normalization_mismatch"] += 1

        if stored != stored.strip():
            whitespace_rows.append((tenant_id, user_id, repr(stored)))
            stats["outer_whitespace"] += 1

    # Explicitly rollback to guarantee read-only execution.
    await db.rollback()

    return {
        "total_examined": total_examined,
        "matched_count": len(matched_rows),
        "outer_whitespace_count": len(whitespace_rows),
        "rows": matched_rows,
        "whitespace_rows": whitespace_rows,
        "tenant_counts": dict(tenant_counts),
    }


def format_report(summary: dict[str, Any]) -> str:
    """Format report output with counts only by default (no PHI)."""
    lines = [
        "=" * 64,
        "UNLOGINABLE USERNAMES DIAGNOSTIC REPORT (READ-ONLY)",
        "=" * 64,
        f"Total users examined: {summary['total_examined']}",
        f"Rows where normalize_username(stored) != stored.strip().lower(): {summary['matched_count']}",
        f"Rows with leading/trailing whitespace: {summary['outer_whitespace_count']}",
        "-" * 64,
        "Counts per tenant:",
    ]

    for tenant_id, stats in sorted(
        summary["tenant_counts"].items(),
        key=lambda item: (item[0] is not None, item[0] or 0),
    ):
        label = f"tenant_id={tenant_id}" if tenant_id is not None else "tenant_id=None"
        lines.append(
            f"  - {label}: examined={stats['examined']}, "
            f"arabic_normalization_mismatch={stats['arabic_normalization_mismatch']}, "
            f"outer_whitespace={stats['outer_whitespace']}"
        )

    lines.append("=" * 64)
    return "\n".join(lines)


async def _main_async() -> int:
    async with system_session_scope() as db:
        summary = await find_unloginable_usernames(db)
    print(format_report(summary))
    return 0


def main() -> int:
    return asyncio.run(_main_async())


if __name__ == "__main__":
    raise SystemExit(main())
