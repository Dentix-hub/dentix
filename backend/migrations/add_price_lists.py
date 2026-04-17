"""
Migration: Add Price List Tables

Creates:
- insurance_providers
- price_lists
- price_list_items

Adds columns:
- patients.default_price_list_id
- appointments.price_list_id
- treatments.price_list_id, unit_price, price_snapshot

Run with: python backend/migrations/add_price_lists.py
"""

from sqlalchemy import text
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Table creation SQL
CREATE_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS insurance_providers (
        id SERIAL PRIMARY KEY,
        tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
        name VARCHAR NOT NULL,
        code VARCHAR,
        contact_email VARCHAR,
        contact_phone VARCHAR,
        address TEXT,
        notes TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS price_lists (
        id SERIAL PRIMARY KEY,
        tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
        name VARCHAR NOT NULL,
        type VARCHAR DEFAULT 'cash',
        description TEXT,
        is_default BOOLEAN DEFAULT FALSE,
        is_active BOOLEAN DEFAULT TRUE,
        insurance_provider_id INTEGER REFERENCES insurance_providers(id),
        coverage_percent FLOAT DEFAULT 100.0,
        copay_percent FLOAT DEFAULT 0.0,
        copay_fixed FLOAT DEFAULT 0.0,
        effective_from DATE,
        effective_to DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS price_list_items (
        id SERIAL PRIMARY KEY,
        price_list_id INTEGER REFERENCES price_lists(id) NOT NULL,
        procedure_id INTEGER REFERENCES procedures(id) NOT NULL,
        price FLOAT NOT NULL,
        discount_percent FLOAT DEFAULT 0.0,
        insurance_code VARCHAR,
        max_units INTEGER,
        requires_approval BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
]

# Column additions
ADD_COLUMNS = [
    {
        "table": "patients",
        "column": "default_price_list_id",
        "sql": "ALTER TABLE patients ADD COLUMN IF NOT EXISTS default_price_list_id INTEGER REFERENCES price_lists(id)",
    },
    {
        "table": "appointments",
        "column": "price_list_id",
        "sql": "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS price_list_id INTEGER REFERENCES price_lists(id)",
    },
    {
        "table": "treatments",
        "column": "price_list_id",
        "sql": "ALTER TABLE treatments ADD COLUMN IF NOT EXISTS price_list_id INTEGER REFERENCES price_lists(id)",
    },
    {
        "table": "treatments",
        "column": "unit_price",
        "sql": "ALTER TABLE treatments ADD COLUMN IF NOT EXISTS unit_price FLOAT",
    },
    {
        "table": "treatments",
        "column": "price_snapshot",
        "sql": "ALTER TABLE treatments ADD COLUMN IF NOT EXISTS price_snapshot TEXT",
    },
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_insurance_tenant ON insurance_providers(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_pricelist_tenant ON price_lists(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_pricelist_type ON price_lists(tenant_id, type)",
    "CREATE INDEX IF NOT EXISTS idx_pricelistitem_list ON price_list_items(price_list_id)",
    "CREATE INDEX IF NOT EXISTS idx_pricelistitem_proc ON price_list_items(procedure_id)",
    "CREATE INDEX IF NOT EXISTS idx_appointment_pricelist ON appointments(price_list_id)",
    "CREATE INDEX IF NOT EXISTS idx_treatment_pricelist ON treatments(price_list_id)",
]


def run_migration():
    """Run all migrations."""
    logger.info("Starting Price Lists Migration...")

    with engine.connect() as conn:
        # Create tables
        for sql in CREATE_TABLES:
            try:
                conn.execute(text(sql))
                conn.commit()
                table_name = sql.split("CREATE TABLE IF NOT EXISTS ")[1].split(" ")[0]
                logger.info(f"Created table: {table_name}")
            except Exception as e:
                logger.warning(f"Table creation: {e}")

        # Add columns
        for col_def in ADD_COLUMNS:
            try:
                # SQLite doesn't support IF NOT EXISTS in ALTER TABLE
                # We attempt to add, and catch duplicate column error
                sql_command = col_def["sql"].replace("IF NOT EXISTS ", "")
                conn.execute(text(sql_command))
                conn.commit()
                logger.info(f"Added column: {col_def['table']}.{col_def['column']}")
            except Exception as e:
                if (
                    "duplicate column" in str(e).lower()
                    or "no such column" in str(e).lower()
                ):
                    # "no such column" might be misleading but usually sqlite says "duplicate column name: ..."
                    logger.info(
                        f"Column already exists or error: {col_def['table']}.{col_def['column']}"
                    )
                else:
                    logger.warning(f"Column addition failed: {e}")

        # Create indexes
        for idx_sql in INDEXES:
            try:
                conn.execute(text(idx_sql))
                conn.commit()
                logger.info("Created index")
            except Exception as e:
                logger.warning(f"Index creation: {e}")

    logger.info("Migration complete!")


def create_default_price_lists():
    """Create default CASH price list for each tenant."""
    logger.info("Creating default price lists...")

    with engine.connect() as conn:
        # Get all tenants
        tenants = conn.execute(text("SELECT id FROM tenants")).fetchall()

        for tenant in tenants:
            tenant_id = tenant[0]

            # Check if default exists
            existing = conn.execute(
                text("""
                SELECT id FROM price_lists
                WHERE tenant_id = :tid AND is_default = TRUE
            """),
                {"tid": tenant_id},
            ).fetchone()

            if not existing:
                conn.execute(
                    text("""
                    INSERT INTO price_lists (tenant_id, name, type, is_default, is_active)
                    VALUES (:tid, 'كاش', 'cash', TRUE, TRUE)
                """),
                    {"tid": tenant_id},
                )
                conn.commit()
                logger.info(f"Created default price list for tenant {tenant_id}")


def migrate_procedure_prices():
    """Copy Procedure.price to default PriceListItem."""
    logger.info("Migrating procedure prices to default price lists...")

    with engine.connect() as conn:
        # Get procedures with prices
        procedures = conn.execute(
            text("""
            SELECT p.id, p.price, p.tenant_id
            FROM procedures p
            WHERE p.price IS NOT NULL AND p.price > 0
        """)
        ).fetchall()

        for proc in procedures:
            proc_id, price, tenant_id = proc

            # Get default price list for tenant
            price_list = conn.execute(
                text("""
                SELECT id FROM price_lists
                WHERE tenant_id = :tid AND is_default = TRUE
            """),
                {"tid": tenant_id},
            ).fetchone()

            if price_list:
                # Check if item exists
                existing = conn.execute(
                    text("""
                    SELECT id FROM price_list_items
                    WHERE price_list_id = :plid AND procedure_id = :pid
                """),
                    {"plid": price_list[0], "pid": proc_id},
                ).fetchone()

                if not existing:
                    conn.execute(
                        text("""
                        INSERT INTO price_list_items (price_list_id, procedure_id, price)
                        VALUES (:plid, :pid, :price)
                    """),
                        {"plid": price_list[0], "pid": proc_id, "price": price},
                    )
                    conn.commit()

        logger.info("Procedure prices migrated!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        run_migration()
        create_default_price_lists()
        migrate_procedure_prices()
    elif len(sys.argv) > 1 and sys.argv[1] == "--migrate-prices":
        migrate_procedure_prices()
    else:
        run_migration()
        logger.info("\nTo create default price lists: python add_price_lists.py --full")
