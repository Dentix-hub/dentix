"""Authenticated envelope for clinic-scoped archives.

Archive decoding only authenticates and decodes bytes; callers must still
validate the business registry and references before performing any writes.
"""
import base64
import binascii
import hashlib
import json
import os
import struct
import uuid
from datetime import datetime, timezone

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b'DENTIX-CLINIC\x00'
VERSION = 1
DEFAULT_MAX_BYTES = 100 * 1024 * 1024
MAX_HEADER_BYTES = 16 * 1024


class ArchiveError(ValueError):
    """An archive is invalid, unsupported, or cannot be authenticated."""

    def __init__(self, message, *, section=None, field=None, category=None, counts=None, referenced_section=None):
        super().__init__(message)
        self.message = message
        self.section = section
        self.field = field
        self.category = category
        self.counts = counts
        self.referenced_section = referenced_section


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _key(value):
    try:
        decoded = base64.b64decode(value.encode('ascii'), altchars=b'-_', validate=True)
    except (ValueError, UnicodeError, binascii.Error, AttributeError) as exc:
        raise ArchiveError('مفتاح النسخ الاحتياطي غير صالح') from exc
    if len(decoded) != 32:
        raise ArchiveError('مفتاح النسخ الاحتياطي غير صالح')
    return decoded


def configured_keys():
    current_id = os.getenv('TENANT_BACKUP_KEY_ID')
    current_key = os.getenv('TENANT_BACKUP_ENCRYPTION_KEY')
    installation = os.getenv('DENTIX_INSTALLATION_ID')
    if not current_id or not current_key or not installation:
        raise ArchiveError('إعدادات النسخ الاحتياطي غير مكتملة')
    try:
        previous = json.loads(os.getenv('TENANT_BACKUP_PREVIOUS_KEYS_JSON', '{}'))
        if not isinstance(previous, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in previous.items()):
            raise ValueError
        if current_id in previous:
            raise ValueError
        keys = {key_id: _key(value) for key_id, value in previous.items()}
        keys[current_id] = _key(current_key)
    except (ValueError, json.JSONDecodeError) as exc:
        raise ArchiveError('إعدادات مفاتيح النسخ الاحتياطي غير صالحة') from exc
    return current_id, keys, installation


def encode_archive(payload, *, tenant_id, installation_id, schema_revision, key_id, key, max_bytes=DEFAULT_MAX_BYTES):
    raw = _canonical(payload)
    if len(raw) > max_bytes:
        raise ArchiveError('حجم النسخة الاحتياطية أكبر من الحد المسموح')
    header = {
        'version': VERSION, 'schema_revision': schema_revision, 'backup_id': str(uuid.uuid4()),
        'created_at': datetime.now(timezone.utc).isoformat(), 'tenant_id': tenant_id,
        'installation_id': installation_id, 'key_id': key_id,
        'counts': {name: len(rows) for name, rows in payload.get('data', {}).items() if isinstance(rows, list)},
        'payload_sha256': hashlib.sha256(raw).hexdigest(),
    }
    header_bytes = _canonical(header)
    if len(header_bytes) > MAX_HEADER_BYTES:
        raise ArchiveError('ترويسة النسخة الاحتياطية غير صالحة')
    prefix = MAGIC + struct.pack('>I', len(header_bytes)) + header_bytes
    nonce = os.urandom(12)
    archive = prefix + nonce + AESGCM(key).encrypt(nonce, raw, prefix)
    if len(archive) > max_bytes:
        raise ArchiveError('حجم النسخة الاحتياطية أكبر من الحد المسموح')
    return archive


def decode_archive(archive, *, tenant_id, installation_id, keys, max_bytes=DEFAULT_MAX_BYTES):
    if len(archive) > max_bytes or not archive.startswith(MAGIC) or len(archive) < len(MAGIC) + 4:
        raise ArchiveError('ملف النسخة الاحتياطية غير صالح أو أكبر من الحد المسموح')
    header_size = struct.unpack('>I', archive[len(MAGIC):len(MAGIC) + 4])[0]
    header_end = len(MAGIC) + 4 + header_size
    if not 0 < header_size <= MAX_HEADER_BYTES or len(archive) < header_end + 28:
        raise ArchiveError('ترويسة النسخة الاحتياطية غير صالحة')
    prefix = archive[:header_end]
    try:
        header = json.loads(archive[len(MAGIC) + 4:header_end])
        if not isinstance(header, dict) or header.get('version') != VERSION:
            raise ArchiveError('إصدار النسخة الاحتياطية غير مدعوم')
        key = keys[header['key_id']]
        raw = AESGCM(key).decrypt(archive[header_end:header_end + 12], archive[header_end + 12:], prefix)
        if len(raw) > max_bytes or header.get('tenant_id') != tenant_id or header.get('installation_id') != installation_id:
            raise ArchiveError('النسخة الاحتياطية لا تخص هذه العيادة أو البيئة')
        if hashlib.sha256(raw).hexdigest() != header.get('payload_sha256'):
            raise ArchiveError('محتوى النسخة الاحتياطية غير صالح')
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ArchiveError('محتوى النسخة الاحتياطية غير صالح')
        return header, payload
    except (InvalidTag, KeyError, TypeError, ValueError, UnicodeError) as exc:
        if isinstance(exc, ArchiveError):
            raise
        raise ArchiveError('تعذر التحقق من النسخة الاحتياطية') from exc
