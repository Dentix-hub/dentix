import sys
import os
import asyncio
from sqlalchemy import select

# Ensure backend structure is visible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.database import system_session_scope
from backend.models.clinical import Procedure


async def fix_procedures_tenant():
    """Optionally migrate the historical tenant-1 seed catalog to globals.

    This operation changes data ownership and therefore must never run merely
    because an application container started. Existing deployments may have a
    real clinic with tenant_id=1. Require an explicit one-off opt-in instead.
    """
    if os.getenv("MIGRATE_TENANT1_PROCEDURES_TO_GLOBAL", "false").lower() != "true":
        print(
            "Skipping tenant-1 procedure ownership migration. "
            "Set MIGRATE_TENANT1_PROCEDURES_TO_GLOBAL=true for an explicit one-off run."
        )
        return

    async with system_session_scope() as db:
        try:
            # Fetch all procedures with tenant_id=1
            stmt = select(Procedure).filter(Procedure.tenant_id == 1)
            res = await db.execute(stmt)
            procs = res.scalars().all()
            print(f"Found {len(procs)} procedures with tenant_id=1.")

            for p in procs:
                p.tenant_id = None  # Make them global

            await db.commit()
            print(f"Updated {len(procs)} procedures to be Global (tenant_id=NULL).")

        except Exception as e:
            print(f"Error: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(fix_procedures_tenant())
