"""
Script: Propagate Global Procedures to All Tenants
--------------------------------------------------
Problem: Global procedures (tenant_id=None) exist but represent base treatments.
         Tenants cannot use them because valid PriceListItems are required,
         and PriceLists are tenant-specific.

Solution: This script iterates over all tenants, finds their default price list,
          and adds all Global Procedures to it as PriceListItems.
"""

import sys
import os
import asyncio
from sqlalchemy import text

# Ensure backend structure is visible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.database import system_session_scope


async def fix_global_procedures():
    print("Starting Global Procedure Propagation...")

    async with system_session_scope() as conn:
        # 1. Get all Global Procedures
        res_procs = await conn.execute(
            text("""
            SELECT id, price, name FROM procedures WHERE tenant_id IS NULL
        """)
        )
        global_procs = res_procs.fetchall()

        if not global_procs:
            print("No global procedures found. Run seed_procedures.py first.")
            return

        print(f"Found {len(global_procs)} global procedures.")

        # 2. Get all Tenants
        res_tenants = await conn.execute(text("SELECT id, name FROM tenants"))
        tenants = res_tenants.fetchall()
        print(f"Found {len(tenants)} tenants.")

        total_inserted = 0

        for tenant in tenants:
            tenant_id, tenant_name = tenant
            safe_tenant_name = str(tenant_name).encode('ascii', errors='backslashreplace').decode('ascii')
            print(f"Processing Tenant: {safe_tenant_name} ({tenant_id})")

            # 3. Get Default Price List
            res_pl = await conn.execute(
                text("""
                SELECT id FROM price_lists
                WHERE tenant_id = :tid AND is_default = TRUE
            """),
                {"tid": tenant_id},
            )
            price_list = res_pl.fetchone()

            if not price_list:
                print(f"  [WARN] No default price list for {safe_tenant_name}. Skipping.")
                continue

            pl_id = price_list[0]

            # 4. Insert Items
            for proc in global_procs:
                proc_id, price, name = proc

                # Check if exists
                res_exists = await conn.execute(
                    text("""
                    SELECT id FROM price_list_items
                    WHERE price_list_id = :plid AND procedure_id = :pid
                """),
                    {"plid": pl_id, "pid": proc_id},
                )
                exists = res_exists.fetchone()

                if not exists:
                    # Use provided price or 0.0
                    final_price = price if price is not None else 0.0

                    await conn.execute(
                        text("""
                        INSERT INTO price_list_items (price_list_id, procedure_id, price, created_at, updated_at)
                        VALUES (:plid, :pid, :price, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """),
                        {"plid": pl_id, "pid": proc_id, "price": final_price},
                    )
                    total_inserted += 1

            await conn.commit()

    print(
        f"\nSuccess! Inserted {total_inserted} new price list items across all tenants."
    )


if __name__ == "__main__":
    try:
        asyncio.run(fix_global_procedures())
    except Exception as e:
        print(f"Error: {e}")
