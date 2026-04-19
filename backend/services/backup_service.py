import os
import datetime
import logging
import traceback
from ..google_drive_client import GoogleDriveClient
from ..database import SessionLocal
from .. import models

# Configure logger
logger = logging.getLogger("smart_clinic")


def update_backup_status(status: str, message: str, tenant_id: int = None):
    """Helper to update backup status in DB."""
    try:
        db = SessionLocal()

        # For tenant-specific backup, update tenant record
        if tenant_id:
            tenant = (
                db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
            )
            if tenant:
                if status == "success":
                    tenant.last_backup_at = datetime.datetime.utcnow()
                db.commit()

        # 1. Update Status
        setting_status = (
            db.query(models.SystemSetting)
            .filter(models.SystemSetting.key == "backup_last_status")
            .first()
        )
        if not setting_status:
            setting_status = models.SystemSetting(
                key="backup_last_status", value=status
            )
            db.add(setting_status)
        else:
            setting_status.value = status

        # 2. Update Message
        setting_msg = (
            db.query(models.SystemSetting)
            .filter(models.SystemSetting.key == "backup_last_message")
            .first()
        )
        if not setting_msg:
            setting_msg = models.SystemSetting(key="backup_last_message", value=message)
            db.add(setting_msg)
        else:
            setting_msg.value = message

        # 3. Update Time
        setting_time = (
            db.query(models.SystemSetting)
            .filter(models.SystemSetting.key == "backup_last_run")
            .first()
        )
        now_str = datetime.datetime.now().isoformat()
        if not setting_time:
            setting_time = models.SystemSetting(key="backup_last_run", value=now_str)
            db.add(setting_time)
        else:
            setting_time.value = now_str

        db.commit()
        db.close()
    except Exception as e:
        logger.error(f"Failed to update backup status in DB: {e}")


def run_backup_task(
    refresh_token: str = None, db_url: str = None, tenant_id: int = None, tenant_name: str = None
):
    """
    Executes the database backup and google drive upload in the background.

    For tenants: Creates JSON export of tenant data only.
    """
    from .export_service import export_tenant_to_json

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Use tenant name in filename if available
    safe_name = (tenant_name or "clinic").replace(" ", "_")[:30]
    filename = f"{safe_name}_backup_{timestamp}.json"
    filepath = os.path.join("/tmp", filename)

    logger.info(f"[{timestamp}] Background Backup Task Started: {filename}")
    update_backup_status("processing", "Starting backup process...", tenant_id)

    try:
        # Create JSON export
        logger.info("Creating JSON export...")
        update_backup_status("processing", "Exporting data...", tenant_id)

        db = SessionLocal()
        try:
            json_content = export_tenant_to_json(db, tenant_id)
        finally:
            db.close()

        # Write to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(json_content)

        # Verify creation
        if not os.path.exists(filepath):
            logger.error("Backup file was not created at expected path.")
            raise Exception("Backup file creation failed")

        file_size = os.path.getsize(filepath)
        size_kb = file_size / 1024
        logger.info(f"JSON export successful. Size: {size_kb:.2f} KB")
        update_backup_status(
            "processing", f"Export success ({size_kb:.2f} KB). Uploading...", tenant_id
        )

        # Upload to Google Drive
        logger.info("Uploading to Google Drive...")
        result = GoogleDriveClient.upload_file(refresh_token, filepath, filename)
        file_id = result.get("id")
        link = result.get("link")

        logger.info(f"Upload Successful! File ID: {file_id}")

        update_backup_status("success", f"{link}", tenant_id)

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
                db = SessionLocal()
                # Only auto-disconnect if it was a refresh token based auth
                if refresh_token:
                    db.query(models.SystemSetting).filter(
                        models.SystemSetting.key == "google_refresh_token_super_admin"
                    ).delete()
                # Reset status
                db.query(models.SystemSetting).filter(
                    models.SystemSetting.key.in_(
                        ["backup_last_status", "backup_last_message", "backup_last_run"]
                    )
                ).delete(synchronize_session=False)
                db.commit()
                db.close()
                update_backup_status(
                    "failed",
                    "تم فك الربط تلقائياً لانتهاء الصلاحية. يرجى إعادة الربط.",
                    tenant_id,
                )
                return
            except Exception as db_e:
                logger.error(f"Failed to auto-disconnect: {db_e}")

        logger.error(f"Backup Task Failed: {str(e)}")
        logger.error(traceback.format_exc())
        update_backup_status("failed", f"Error: {str(e)}", tenant_id)
    finally:
        # Cleanup
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.info("Local backup file cleaned up.")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp file: {str(cleanup_error)}")
