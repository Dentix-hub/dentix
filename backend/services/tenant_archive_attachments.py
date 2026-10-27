"""Validate restored attachment ownership metadata without opening remote files."""
import re
import uuid
from pathlib import PurePosixPath
from urllib.parse import urlparse

from backend.services.tenant_archive import ArchiveError


def validate_attachment_metadata(data, tenant_id):
    seen = set()
    for row in data['attachments']:
        provider, path = row.get('storage_provider'), row.get('file_path')
        if not isinstance(path, str) or not path:
            raise ArchiveError('مرجع المرفق في النسخة الاحتياطية غير صالح')
        if provider == 'legacy':
            if any(row.get(key) is not None for key in ('storage_uuid', 'drive_original_id', 'drive_thumbnail_id', 'google_account_sub')):
                raise ArchiveError('مرجع المرفق القديم غير صالح')
            if path.startswith('https://'):
                url = urlparse(path)
                if url.hostname != 'res.cloudinary.com' or f'/tenant_{tenant_id}/' not in url.path or url.username or url.password:
                    raise ArchiveError('مرجع المرفق القديم غير صالح')
            else:
                parts = PurePosixPath(path).parts
                if not parts or parts[0] != f'tenant_{tenant_id}' or '..' in parts or '\\' in path or path.startswith('/'):
                    raise ArchiveError('مرجع المرفق القديم غير صالح')
        elif provider == 'google_drive':
            storage_uuid = row.get('storage_uuid')
            try:
                if not isinstance(storage_uuid, str) or str(uuid.UUID(storage_uuid)) != storage_uuid:
                    raise ValueError
            except ValueError as exc:
                raise ArchiveError('معرّف الصورة غير صالح') from exc
            if storage_uuid in seen or path != f'/api/v1/upload/drive/{storage_uuid}/content':
                raise ArchiveError('مرجع الصورة غير صالح')
            seen.add(storage_uuid)
            if row.get('storage_status') not in {'ready', 'failed'}:
                raise ArchiveError('الصورة لم تكتمل قبل إنشاء النسخة')
            if not isinstance(row.get('google_account_sub'), str) or not row['google_account_sub']:
                raise ArchiveError('حساب الصورة غير صالح')
            if row.get('storage_status') == 'ready':
                if any(not isinstance(row.get(key), str) or not row[key] for key in ('drive_original_id', 'drive_thumbnail_id')):
                    raise ArchiveError('مرجع ملف الصورة غير صالح')
                if any(not re.fullmatch(r'[0-9a-f]{64}', row.get(key) or '') for key in ('original_sha256', 'thumbnail_sha256')):
                    raise ArchiveError('بصمة الصورة غير صالحة')
                if not isinstance(row.get('original_size'), int) or isinstance(row['original_size'], bool) or row['original_size'] <= 0:
                    raise ArchiveError('حجم الصورة غير صالح')
        else:
            raise ArchiveError('نوع تخزين المرفق غير مدعوم')
