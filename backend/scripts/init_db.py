"""Create the current Dentix schema baseline on a brand-new database."""

import argparse
import logging
import os
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from backend import database, models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CORE_TABLES = {"tenants", "users", "patients", "appointments"}


def _stamp_alembic_head():
    """Stamp the schema with the current Alembic head."""
    backend_dir = os.path.join(project_root, "backend")
    config = Config(os.path.join(backend_dir, "alembic.ini"))
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.stamp(config, "head")


def _needs_baseline(engine):
    """Return True only when the database has no Dentix core schema yet."""
    tables = set(inspect(engine).get_table_names())
    existing_core_tables = tables.intersection(CORE_TABLES)
    if existing_core_tables:
        logger.info(
            "Dentix schema already exists (%s); baseline initialization skipped.",
            ", ".join(sorted(existing_core_tables)),
        )
        return False

    logger.info(
        "No Dentix core tables found; creating the current schema baseline. "
        "Existing auxiliary tables: %s",
        ", ".join(sorted(tables)) or "none",
    )
    return True


def init_db(*, only_if_empty=False):
    """Create all current tables and stamp the result at Alembic head."""
    logger.info("Starting database baseline initialization...")

    try:
        if only_if_empty and not _needs_baseline(database.engine):
            return False

        models.Base.metadata.create_all(bind=database.engine)
        logger.info("Successfully created all tables via Base.metadata.create_all")

        logger.info("Stamping Alembic to head...")
        _stamp_alembic_head()
        logger.info("Successfully stamped Alembic to head.")
        logger.info("Database Initialization Complete.")
        return True
    except Exception as exc:
        logger.exception("Critical error during database initialization: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize the Dentix database schema.")
    parser.add_argument(
        "--if-empty",
        action="store_true",
        help="Create a baseline only when no Dentix core tables exist.",
    )
    init_db(only_if_empty=parser.parse_args().if_empty)
