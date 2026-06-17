import os
import sys
import logging
import asyncio

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from backend import database, models
from backend.core import seeding
from backend.utils.firebase_manager import firebase_manager
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_final_setup():
    """Final setup: seeding and verification."""
    # Ensure env is loaded
    load_dotenv(os.path.join(project_root, ".env"))

    logger.info("Starting Final Seeding & Verification...")

    try:
        # 1. Seed Default Data (Plans & Admin)
        logger.info("Running Database Seeding...")
        async with database.AsyncSessionLocal() as db:
            async with db.begin():
                await seeding.seed_default_data(db)

        # 3. Test Firebase Initialization
        logger.info("Testing Firebase Initialization...")
        firebase_manager.initialize()
        if firebase_manager._initialized:
            logger.info("Firebase Integration: SUCCESS")
        else:
            logger.error("Firebase Integration: FAILED (Check credentials)")

        logger.info("Final Setup Complete.")

    except Exception as e:
        logger.exception(f"Error during final setup: {e}")

if __name__ == "__main__":
    asyncio.run(run_final_setup())
