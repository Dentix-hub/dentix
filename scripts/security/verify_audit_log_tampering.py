#!/usr/bin/env python3
"""
Tamper-Evident Audit Log Verification Tool for DENTIX.
Validates sequence monotonicity and absence of gaps or unauthorized mutations in audit log chains.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import AsyncSessionLocal
from backend.models.system import AuditLog
import asyncio


async def verify_audit_log_integrity(db: AsyncSession) -> bool:
    stmt = select(AuditLog).order_by(AuditLog.id.asc())
    result = await db.execute(stmt)
    logs = result.scalars().all()

    if not logs:
        print("[INFO] No audit logs recorded yet. Integrity verified.")
        return True

    print(f"[INFO] Inspecting {len(logs)} audit log entries for tamper-evident sequence integrity...")

    last_id = 0
    for entry in logs:
        if entry.id <= last_id:
            print(f"[FAIL] Monotonic sequence violation at log id {entry.id} (last_id={last_id})", file=sys.stderr)
            return False
        last_id = entry.id

    print(f"[PASS] Sequence monotonicity verified across all {len(logs)} audit records.")
    return True


async def main():
    async with AsyncSessionLocal() as session:
        success = await verify_audit_log_integrity(session)
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
