from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
import os
import sys
from dotenv import load_dotenv

# Add project root to python path to allow importing backend modules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(
    os.path.dirname(current_dir)
)  # Go up: alembic -> backend -> root
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv(os.path.join(project_root, ".env"))

# Import Base from your models
from backend.models.base import Base  # noqa: E402
from backend import models # noqa: F401
from rls.register_rls import register_rls
register_rls(Base)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    # Preflight owns its deployment-safety logger. Alembic's default
    # ``disable_existing_loggers=True`` silences the exact health-check reason
    # after a fresh baseline is stamped, making CI failures non-diagnostic.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Set database URL:
# 1. Preserve the database URL if already configured on the Alembic Config object
#    (e.g., set by preflight_migrations using MIGRATION_DATABASE_URL / OWNER_DATABASE_URL).
# 2. Otherwise fall back to environment variables in order:
#    MIGRATION_DATABASE_URL -> OWNER_DATABASE_URL -> DATABASE_URL.
configured_url = config.get_main_option("sqlalchemy.url")
placeholder_urls = {"", "driver://user:pass@localhost/dbname"}
if not configured_url or configured_url in placeholder_urls:
    raw_url = (
        os.getenv("MIGRATION_DATABASE_URL")
        or os.getenv("OWNER_DATABASE_URL")
        or os.getenv("DATABASE_URL")
    )
    if raw_url:
        raw_url = raw_url.strip().strip("'").strip('"')
        if raw_url.startswith("postgres://"):
            raw_url = raw_url.replace("postgres://", "postgresql://", 1)
        if raw_url.startswith("postgresql+asyncpg://"):
            raw_url = raw_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        config.set_main_option("sqlalchemy.url", raw_url.replace("%", "%%"))

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
