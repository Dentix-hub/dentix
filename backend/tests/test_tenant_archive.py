import json
import struct

import pytest

from backend.services.tenant_archive import ArchiveError, MAGIC, decode_archive, encode_archive


@pytest.fixture
def archive_args():
    return dict(tenant_id=7, installation_id='synthetic-installation', schema_revision='head', key_id='current', key=b'a' * 32)


def test_authenticated_archive_round_trip_and_tenant_isolation(archive_args):
    payload = {'data': {'patients': [{'id': 1, 'name': 'synthetic'}]}}
    archive = encode_archive(payload, **archive_args)
    kwargs = dict(tenant_id=7, installation_id='synthetic-installation', keys={'current': b'a' * 32})
    header, restored = decode_archive(archive, **kwargs)
    assert restored == payload
    assert header['counts'] == {'patients': 1}
    with pytest.raises(ArchiveError):
        decode_archive(archive, **{**kwargs, 'tenant_id': 8})
    with pytest.raises(ArchiveError):
        decode_archive(archive, **{**kwargs, 'installation_id': 'other'})
    with pytest.raises(ArchiveError):
        decode_archive(archive, **{**kwargs, 'keys': {'current': b'b' * 32}})


def test_modified_header_with_recomputed_plain_checksum_fails_authentication(archive_args):
    archive = encode_archive({'data': {}}, **archive_args)
    length = struct.unpack('>I', archive[len(MAGIC):len(MAGIC) + 4])[0]
    start = len(MAGIC) + 4
    header = json.loads(archive[start:start + length])
    header['payload_sha256'] = '0' * 64
    encoded = json.dumps(header, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    forged = MAGIC + struct.pack('>I', len(encoded)) + encoded + archive[start + length:]
    with pytest.raises(ArchiveError):
        decode_archive(forged, tenant_id=7, installation_id='synthetic-installation', keys={'current': b'a' * 32})


def test_size_limit_rejects_input_and_output(archive_args):
    with pytest.raises(ArchiveError):
        encode_archive({'data': {}, 'padding': 'x' * 200}, **archive_args, max_bytes=128)
    archive = encode_archive({'data': {}}, **archive_args)
    with pytest.raises(ArchiveError):
        decode_archive(archive, tenant_id=7, installation_id='synthetic-installation', keys={'current': b'a' * 32}, max_bytes=20)
