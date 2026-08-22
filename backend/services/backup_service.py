import os
import datetime
from datetime import timezone
import logging
import traceback
import asyncio
import tempfile
import re
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from sqlalchemy.engine import make_url

from ..google_drive_client import GoogleDriveClient
from ..database import ASYNC_DATABASE_URL, CustomAsyncRlsSession, RlsContext
from .. import models
from .secret_service import GOOGLE_SUPER_ADMIN_TOKEN_KEY

# Configure logger
logger = logging.getLogger("smart_clinic")


def _postgres_connection_args(database_url: str) -> tuple[list[str], dict[str, str], str]:
    """Build PostgreSQL CLI connection arguments without putting secrets in argv."""
    normalized_url = database_url.replace("postgres://", "postgresql://", 1)
    parsed = make_url(normalized_url)
    if not parsed.drivername.startswith("postgresql") or not parsed.database:
        raise ValueError("A valid PostgreSQL database URL is required")

    args = ["--no-password"]
    if parsed.host:
        args.extend(["--host", parsed.host])
    if parsed.port:
        args.extend(["--port", str(parsed.port)])
    if parsed.username:
        args.extend(["--username", parsed.username])

    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password
    ssl_mode = parsed.query.get("sslmode") or parsed.query.get("ssl")
    if ssl_mode:
        env["PGSSLMODE"] = "require" if ssl_mode == "true" else str(ssl_mode)
    return args, env, parsed.database


def build_pg_dump_command(database_url: str, filepath: str) -> tuple[list[str], dict[str, str]]:
    connection_args, env, database_name = _postgres_connection_args(database_url)
    return ["pg_dump", *connection_args, "--file", filepath, database_name], env


def build_psql_command(database_url: str, filepath: str) -> tuple[list[str], dict[str, str]]:
    connection_args, env, database_name = _postgres_connection_args(database_url)
    return ["psql", *connection_args, "--file", filepath, database_name], env


def create_secure_temp_file(*, prefix: str, suffix: str) -> str:
    descriptor, filepath = tempfile.mkstemp(prefix=prefix, suffix=suffix)
    os.close(descriptor)
    try:
        os.chmod(filepath, 0o600)
    except OSError:
        logger.warning("Could not tighten temporary backup file permissions")
    return filepath

# Dedicated async engine for backup with autocommit and separate connection pool
backup_pool_args = {}
connect_args = {}
if "sqlite" in ASYNC_DATABASE_URL:
    connect_args["check_same_thread"] = False
else:
    backup_pool_args = {
        "pool_size": 1,
        "max_overflow": 0,
    }

backup_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    execution_options={"isolation_level": "AUTOCOMMIT"},
    connect_args=connect_args,
    **backup_pool_args
)

BackupSessionLocal = async_sessionmaker(
    bind=backup_engine,
    class_=CustomAsyncRlsSession,
    expire_on_commit=False,
    autoflush=False
)


async def update_backup_status(status: str, message: str, tenant_id: int = None):
    """Helper to update backup status in DB."""
    try:
        context = RlsContext(tenant_id=tenant_id)
        async with BackupSessionLocal(context=context) as db:
            # For tenant-specific backup, update tenant record
            if tenant_id:
                res = await db.execute(
                    select(models.Tenant).filter(models.Tenant.id == tenant_id)
                )
                tenant = res.scalars().first()
                if tenant:
                    if status == "success":
                        tenant.last_backup_at = datetime.datetime.now(timezone.utc)
                    await db.commit()

            # 1. Update Status
            res = await db.execute(
                select(models.SystemSetting).filter(models.SystemSetting.key == "backup_last_status")
            )
            setting_status = res.scalars().first()
            if not setting_status:
                setting_status = models.SystemSetting(
                    key="backup_last_status", value=status
                )
                db.add(setting_status)
            else:
                setting_status.value = status

            # 2. Update Message
            res = await db.execute(
                select(models.SystemSetting).filter(models.SystemSetting.key == "backup_last_message")
            )
            setting_msg = res.scalars().first()
            if not setting_msg:
                setting_msg = models.SystemSetting(key="backup_last_message", value=message)
                db.add(setting_msg)
            else:
                setting_msg.value = message

            # 3. Update Time
            res = await db.execute(
                select(models.SystemSetting).filter(models.SystemSetting.key == "backup_last_run")
            )
            setting_time = res.scalars().first()
            now_str = datetime.datetime.now().isoformat()
            if not setting_time:
                setting_time = models.SystemSetting(key="backup_last_run", value=now_str)
                db.add(setting_time)
            else:
                setting_time.value = now_str

            await db.commit()
    except Exception as e:
        logger.error(f"Failed to update backup status in DB: {e}")


async def run_backup_task(
    refresh_token: str = None, db_url: str = None, tenant_id: int = None, tenant_name: str = None
):
    """
    Executes the database backup and google drive upload in the background.

    For full backup (tenant_id=None): Uses pg_dump.
    For tenants (tenant_id is not None): Creates JSON export of tenant data only.
    """
    if "sqlite" in ASYNC_DATABASE_URL:
        raise RuntimeError("Backup service requires PostgreSQL, not SQLite")

    from .export_service import export_tenant_to_json

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Use appropriate filename extension and logic
    if tenant_id is None:
        filename = f"backup_{timestamp}.sql"
    else:
        safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", tenant_name or "clinic")[:30]
        filename = f"{safe_name}_backup_{timestamp}.json"
    filepath = create_secure_temp_file(
        prefix="dentix_backup_",
        suffix=".sql" if tenant_id is None else ".json",
    )

    logger.info(f"[{timestamp}] Background Backup Task Started: {filename}")
    await update_backup_status("processing", "Starting backup process...", tenant_id)

    try:
        if tenant_id is None:
            # Execute pg_dump as an async subprocess out-of-transaction
            logger.info("Executing pg_dump for full system backup...")
            await update_backup_status("processing", "Running pg_dump...", tenant_id)

            dump_url = db_url or os.getenv("DATABASE_URL") or ASYNC_DATABASE_URL
            command, process_env = build_pg_dump_command(dump_url, filepath)

            process = await asyncio.create_subprocess_exec(
                *command,
                env=process_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                logger.error("pg_dump failed: %s", stderr.decode(errors="replace")[:1000])
                raise RuntimeError("Database backup command failed")
        else:
            # Create JSON export for tenant
            logger.info("Creating JSON export for tenant...")
            await update_backup_status("processing", "Exporting tenant data...", tenant_id)

            context = RlsContext(tenant_id=tenant_id)
            async with BackupSessionLocal(context=context) as db:
                json_content = await export_tenant_to_json(db, tenant_id)

            # Write to file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(json_content)

        # Verify creation
        if not os.path.exists(filepath):
            logger.error("Backup file was not created at expected path.")
            raise Exception("Backup file creation failed")

        file_size = os.path.getsize(filepath)
        size_kb = file_size / 1024
        logger.info(f"Backup successful. Size: {size_kb:.2f} KB")
        await update_backup_status(
            "processing", f"Backup success ({size_kb:.2f} KB). Uploading...", tenant_id
        )

        # Upload to Google Drive
        logger.info("Uploading to Google Drive...")
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, GoogleDriveClient.upload_file, refresh_token, filepath, filename
        )
        file_id = result.get("id")
        link = result.get("link")

        logger.info(f"Upload Successful! File ID: {file_id}")

        await update_backup_status("success", f"{link}", tenant_id)

    except Exception as e:
        # Check for Google API Auth Errors (401/403)
        error_str = str(e)
        if (
            "HttpError 401" in error_str
            or "HttpError 403" in error_str
            or "invalid_grant" in error_str.lower()
        ):
            logger.warning("Authentication failed. Disconnecting Google Drive.")
            try:
                context = RlsContext(tenant_id=tenant_id)
                async with BackupSessionLocal(context=context) as db:
                    # Only auto-disconnect if it was a refresh token based auth
                    if refresh_token:
                        from sqlalchemy import delete
                        await db.execute(
                            delete(models.SystemSetting).filter(
                                models.SystemSetting.key == GOOGLE_SUPER_ADMIN_TOKEN_KEY
                            )
                        )
                    # Reset status
                    await db.execute(
                        delete(models.SystemSetting).filter(
                            models.SystemSetting.key.in_(
                                ["backup_last_status", "backup_last_message", "backup_last_run"]
                            )
                        )
                    )
                    await db.commit()
                await update_backup_status(
                    "failed",
                    "تم فك الربط تلقائياً لانتهاء الصلاحية. يرجى إعادة الربط.",
                    tenant_id,
                )
                return
            except Exception as db_e:
                logger.error(f"Failed to auto-disconnect: {db_e}")

        logger.error("Backup Task Failed: %s", type(e).__name__)
        logger.error(traceback.format_exc())
        await update_backup_status(
            "failed", "Backup failed. Check server logs for details.", tenant_id
        )
    finally:
        # Cleanup
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.info("Local backup file cleaned up.")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp file: {str(cleanup_error)}")
