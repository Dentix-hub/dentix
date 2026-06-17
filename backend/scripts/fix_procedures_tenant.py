import sys
import os
import asyncio
from sqlalchemy import select

# Ensure backend structure is visible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.database import AsyncSessionLocal
from backend.models.clinical import Procedure


async def fix_procedures_tenant():
    async with AsyncSessionLocal() as db:
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


if __name__ == "__main__":
    asyncio.run(fix_procedures_tenant())
