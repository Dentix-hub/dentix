import os
import sys
import asyncio
import logging

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from backend import database, models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_db():
    """Initialize the database: create all tables and stamp Alembic head."""
    logger.info("Starting Database Initialization on Supabase...")

    try:
        # 1. Create all tables defined in models via the async engine
        async with database.async_engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)
        logger.info("Successfully created all tables via Base.metadata.create_all")

        # 2. Stamp Alembic to head
        import subprocess
        logger.info("Stamping Alembic to head...")
        # Change to backend directory to run alembic
        backend_dir = os.path.join(project_root, "backend")
        result = subprocess.run(
            ["alembic", "stamp", "head"],
            cwd=backend_dir,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info("Successfully stamped Alembic to head.")
        else:
            logger.error(f"Failed to stamp Alembic: {result.stderr}")
            sys.exit(1)

        logger.info("Database Initialization Complete.")

    except Exception as e:
        logger.exception(f"Critical error during database initialization: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(init_db())
