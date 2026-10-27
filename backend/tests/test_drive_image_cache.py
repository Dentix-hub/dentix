import asyncio

import pytest

from backend.services.drive_image_cache import DriveImageCache


def test_lru_size_object_cap_and_invalidation(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr('backend.services.drive_image_cache.time.monotonic', lambda: clock[0])
    cache = DriveImageCache(max_bytes=6, ttl_seconds=5, max_object_bytes=4)
    a, b, c = (1, 'a', 'v', 'original', 1), (1, 'b', 'v', 'original', 1), (2, 'c', 'v', 'original', 1)
    cache.put(a, b'123')
    cache.put(b, b'456')
    assert cache.get(a) == b'123'
    cache.put(c, b'789')
    assert cache.get(b) is None and cache.get(a) == b'123'
    cache.put(b, b'large')
    assert cache.get(b) is None
    cache.invalidate(tenant_id=1)
    assert cache.get(a) is None and cache.get(c) == b'789'
    clock[0] += 6
    assert cache.get(c) is None


@pytest.mark.asyncio
async def test_concurrent_load_is_single_flight_and_invalidation_blocks_repopulation():
    cache = DriveImageCache(max_bytes=100, ttl_seconds=30)
    key = (1, 'a', 'hash', 'thumbnail', 1)
    entered = asyncio.Event()
    release = asyncio.Event()
    calls = 0
    async def loader():
        nonlocal calls
        calls += 1
        entered.set()
        await release.wait()
        return b'content'
    first = asyncio.create_task(cache.get_or_load(key, loader))
    second = asyncio.create_task(cache.get_or_load(key, loader))
    await entered.wait()
    cache.invalidate(tenant_id=1)
    release.set()
    assert await first == await second == b'content'
    assert calls == 1 and cache.get(key) is None
