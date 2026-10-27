"""Bounded per-process cache for already-authorized Drive image bytes."""
import asyncio
import os
import logging
import threading
import time
from collections import OrderedDict

logger = logging.getLogger(__name__)

MAX_OBJECT_BYTES = 8 * 1024 * 1024
DEFAULT_CACHE_BYTES = 64 * 1024 * 1024
DEFAULT_TTL_SECONDS = 300


def _setting(name, default, maximum):
    try:
        return max(0, min(int(os.getenv(name, str(default))), maximum))
    except ValueError:
        return default


class DriveImageCache:
    def __init__(self, max_bytes=None, ttl_seconds=None, max_object_bytes=MAX_OBJECT_BYTES):
        self.max_bytes = max_bytes if max_bytes is not None else _setting('DRIVE_IMAGE_CACHE_MAX_BYTES', DEFAULT_CACHE_BYTES, DEFAULT_CACHE_BYTES)
        self.ttl_seconds = ttl_seconds if ttl_seconds is not None else _setting('DRIVE_IMAGE_CACHE_TTL_SECONDS', DEFAULT_TTL_SECONDS, DEFAULT_TTL_SECONDS)
        self.max_object_bytes = max_object_bytes
        self._entries = OrderedDict()
        self._bytes = 0
        self._lock = threading.RLock()
        self._inflight = {}
        self._epochs = {}
        self._limit = asyncio.Semaphore(4)
        self.hits = 0
        self.misses = 0
        self.outbound_bytes = 0
        self.load_seconds = 0.0

    def get(self, key):
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self.misses += 1
                return None
            expires, content = entry
            if expires <= time.monotonic():
                self._entries.pop(key)
                self._bytes -= len(content)
                self.misses += 1
                return None
            self._entries.move_to_end(key)
            self.hits += 1
            return content

    def put(self, key, content):
        if not isinstance(content, bytes) or not self.ttl_seconds or len(content) > self.max_object_bytes or len(content) > self.max_bytes:
            return
        with self._lock:
            old = self._entries.pop(key, None)
            if old:
                self._bytes -= len(old[1])
            self._entries[key] = (time.monotonic() + self.ttl_seconds, content)
            self._bytes += len(content)
            while self._bytes > self.max_bytes:
                _, (_, evicted) = self._entries.popitem(last=False)
                self._bytes -= len(evicted)

    def invalidate(self, *, tenant_id, storage_uuid=None):
        with self._lock:
            self._epochs[tenant_id] = self._epochs.get(tenant_id, 0) + 1
            for key in list(self._entries):
                if key[0] == tenant_id and (storage_uuid is None or key[1] == storage_uuid):
                    _, value = self._entries.pop(key)
                    self._bytes -= len(value)

    async def get_or_load(self, key, loader):
        cached = self.get(key)
        if cached is not None:
            return cached
        with self._lock:
            task = self._inflight.get(key)
            if task is None:
                epoch = self._epochs.get(key[0], 0)
                async def load():
                    started = time.monotonic()
                    async with self._limit:
                        value = await loader()
                    with self._lock:
                        if self._epochs.get(key[0], 0) == epoch:
                            self.put(key, value)
                        self.load_seconds += time.monotonic() - started
                    return value
                task = asyncio.create_task(load())
                self._inflight[key] = task
                def done(completed):
                    with self._lock:
                        if self._inflight.get(key) is completed:
                            self._inflight.pop(key, None)
                task.add_done_callback(done)
        return await asyncio.shield(task)

    def record_outbound(self, size):
        with self._lock:
            self.outbound_bytes += size
            requests = self.hits + self.misses
            if requests and requests % 100 == 0:
                logger.info("drive_image_metrics outbound_bytes=%d requests=%d cache_hit_ratio=%.4f load_seconds=%.3f",
                            self.outbound_bytes, requests, self.hits / requests, self.load_seconds)


image_cache = DriveImageCache()
