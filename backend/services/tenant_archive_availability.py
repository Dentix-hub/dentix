"""Report whether backed-up attachment references are currently reachable."""
import os
from pathlib import Path

from sqlalchemy import select

from backend import models
from backend.services.clinic_drive_provider import ClinicDriveProvider, DriveFailure
from backend.services.clinic_google_connection import drive_io
from backend.services.file_service import _get_upload_root


async def attachment_availability(db, *, tenant_id, rows):
    tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == tenant_id))).scalar_one()
    refresh, folder, sub = tenant.google_refresh_token, tenant.google_image_folder_id, tenant.google_account_sub
    connected = tenant.google_connection_status == 'connected' and bool(refresh and folder)
    await db.commit()
    missing = 0
    unverified = 0
    drive_rows = []
    root = _get_upload_root().resolve()
    for row in rows:
        if row.get('storage_provider') == 'google_drive':
            if row.get('storage_status') != 'ready' or not connected or row.get('google_account_sub') != sub:
                missing += 1
            else:
                drive_rows.append(row)
        elif row.get('file_path', '').startswith('https://'):
            unverified += 1
        else:
            path = (root / row['file_path']).resolve()
            if not path.is_relative_to(root / f'tenant_{tenant_id}') or not path.is_file():
                missing += 1
    if not drive_rows:
        return {'missing': missing, 'unverified': unverified}
    installation = os.getenv('DENTIX_INSTALLATION_ID', '').strip()
    try:
        provider = await drive_io(ClinicDriveProvider, refresh)
        metadata = {}
        page = None
        while True:
            items, page = await drive_io(provider.list_images, folder_id=folder, tenant_id=tenant_id, installation_id=installation, page_token=page)
            metadata.update({item['id']: item for item in items})
            if not page:
                break
        for row in drive_rows:
            original = metadata.get(row.get('drive_original_id'))
            thumbnail = metadata.get(row.get('drive_thumbnail_id'))
            def matches(item, variant, digest):
                props = item.get('appProperties', {}) if item else {}
                return bool(item and props.get('dentix_storage') == row.get('storage_uuid')
                            and props.get('dentix_variant') == variant
                            and props.get('dentix_sha256') == digest and item.get('sha256Checksum') == digest)
            if not matches(original, 'original', row.get('original_sha256')) or not matches(thumbnail, 'thumbnail', row.get('thumbnail_sha256')):
                missing += 1
    except (DriveFailure, OSError, ValueError):
        unverified += len(drive_rows)
    return {'missing': missing, 'unverified': unverified}
