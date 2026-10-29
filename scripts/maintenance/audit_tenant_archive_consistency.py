#!/usr/bin/env python3
"""Run read-only consistency audit for a tenant's archive references."""
import argparse
import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import AsyncSessionLocal, RlsContext
from backend.services.tenant_archive_consistency import (
    audit_tenant_consistency, format_consistency_report,
)


async def main():
    parser = argparse.ArgumentParser(description="Audit tenant archive consistency (read-only).")
    parser.add_argument("--tenant-id", type=int, required=True, help="Tenant ID to audit")
    args = parser.parse_args()

    async with AsyncSessionLocal(context=RlsContext(tenant_id=args.tenant_id)) as session:
        result = await audit_tenant_consistency(session, args.tenant_id)
        report = format_consistency_report(result)
        print(report)
        if not result["consistent"]:
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
