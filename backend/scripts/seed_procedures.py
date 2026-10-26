import sys
import os
import asyncio
from sqlalchemy import select

# Ensure backend structure is visible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.database import system_session_scope
from backend.models.clinical import Procedure
from backend.data.default_procedures import DEFAULT_PROCEDURE_CATALOG


async def seed_procedures():
    async with system_session_scope() as db:
        try:
            tenant_id = None  # Global procedures
            added_count = 0
            existing_count = 0

            print("Checking procedures...")
            for entry in DEFAULT_PROCEDURE_CATALOG:
                # Only a GLOBAL procedure satisfies this seed. A tenant-owned row
                # with the same name is an override and must remain tenant-owned.
                res = await db.execute(
                    select(Procedure).filter(
                        Procedure.name == entry.name,
                        Procedure.tenant_id.is_(None),
                    )
                )
                exists = res.scalars().first()
                if exists:
                    # Update code/category if missing
                    if exists.code != entry.code or exists.category != entry.category:
                        exists.code = entry.code
                        exists.category = entry.category
                    existing_count += 1
                    continue

                # Create new global catalog entry
                new_proc = Procedure(
                    name=entry.name,
                    code=entry.code,
                    category=entry.category,
                    price=entry.default_price,
                    tenant_id=tenant_id,
                )
                db.add(new_proc)
                added_count += 1

            await db.commit()
            print(
                f"Done! Added {added_count} new procedures. Skipped {existing_count} existing."
            )

        except Exception as e:
            print(f"Error seeding procedures: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(seed_procedures())
