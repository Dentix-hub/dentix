"""Known archive-version adapters for additive attachment storage metadata."""
from copy import deepcopy

from backend.services.tenant_archive import ArchiveError

PRE_DRIVE_IMAGE_REVISIONS = {'d42a71e9bc83', 'e82c19f5a406', 'f17a93c60e24', 'ab52d9c807a1'}
NEW_ATTACHMENT_DEFAULTS = {
    'storage_provider': 'legacy', 'storage_uuid': None, 'drive_original_id': None,
    'drive_thumbnail_id': None, 'original_size': None, 'original_sha256': None,
    'thumbnail_sha256': None, 'google_account_sub': None, 'connection_generation': None,
    'storage_status': 'ready',
}


def adapt_archive_version(payload, revision):
    if revision not in PRE_DRIVE_IMAGE_REVISIONS:
        return payload
    adapted = deepcopy(payload)
    for row in adapted.get('data', {}).get('attachments', []):
        if not isinstance(row, dict) or set(row) & NEW_ATTACHMENT_DEFAULTS.keys():
            raise ArchiveError('تنسيق المرفقات القديم غير صالح')
        row.update(NEW_ATTACHMENT_DEFAULTS)
    return adapted
