import os
import sys
import logging
from sqlalchemy import create_engine, inspect, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("fix_alembic_version")

def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL environment variable is not set.")
        sys.exit(0)

    # Normalize postgres:// -> postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    try:
        logger.info("[REPAIR] Connecting to database to check Alembic version...")
        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"[REPAIR] Existing tables in database: {tables}")

        if "alembic_version" in tables:
            with engine.connect() as conn:
                res = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
                versions = [r[0] for r in res]
                logger.info(f"[REPAIR] Current Alembic versions in database: {versions}")

                # Check if 'r2s3t4u5v6w7' is in the versions
                if "r2s3t4u5v6w7" in versions:
                    logger.warning("[REPAIR] Detected phantom version 'r2s3t4u5v6w7' in alembic_version table.")

                    # Determine appropriate version to replace it with
                    if "feature_flags" in tables:
                        logger.info("[REPAIR] Tables indicate database is at phase 3. Setting version to 'b7c8d9e0f1a2'.")
                        conn.execute(text("UPDATE alembic_version SET version_num = 'b7c8d9e0f1a2' WHERE version_num = 'r2s3t4u5v6w7'"))
                        conn.commit()
                        logger.info("[REPAIR] Alembic version successfully updated to 'b7c8d9e0f1a2'.")
                    else:
                        logger.info("[REPAIR] Tables indicate database is not at phase 3. Deleting 'r2s3t4u5v6w7' version so migrations can run.")
                        conn.execute(text("DELETE FROM alembic_version WHERE version_num = 'r2s3t4u5v6w7'"))
                        conn.commit()
                        logger.info("[REPAIR] Alembic version 'r2s3t4u5v6w7' successfully deleted.")
                else:
                    logger.info("[REPAIR] Phantom version 'r2s3t4u5v6w7' not found. No repair needed.")
        else:
            logger.info("[REPAIR] alembic_version table does not exist.")

    except Exception as e:
        logger.error(f"[REPAIR ERROR] Error during alembic version repair: {e}", exc_info=True)

if __name__ == "__main__":
    main()
