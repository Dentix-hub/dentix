"""
Tests for Cache Stampede Protection + Cache Key Fix.

Covers:
    1. StampedeProtection: single computation under concurrent access
    2. Lock safety: release only your own lock
    3. Fallback without Redis
    4. Cache key builder: excludes Session/Request objects
"""

import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from backend.core.cache_stampede import StampedeProtection
from backend.services.cache_service import _build_cache_key, _is_serializable_arg


# ---------------------------------------------------------------------------
# Fake in-memory cache for testing (no Redis needed)
# ---------------------------------------------------------------------------
class FakeCache:
    """Thread-safe in-memory cache that mimics CacheManager API."""

    def __init__(self):
        self._store = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            return self._store.get(key)

    def set(self, key, value, expire=300):
        with self._lock:
            self._store[key] = value

    def delete(self, key):
        with self._lock:
            self._store.pop(key, None)


# ---------------------------------------------------------------------------
# Fake Redis for lock testing
# ---------------------------------------------------------------------------
class FakeRedis:
    """Minimal Redis mock that supports SET NX EX, GET, DELETE, EVAL."""

    def __init__(self):
        self._store = {}
        self._lock = threading.Lock()

    def set(self, key, value, nx=False, ex=None):
        with self._lock:
            if nx and key in self._store:
                return None
            self._store[key] = value
            return True

    def get(self, key):
        with self._lock:
            return self._store.get(key)

    def delete(self, key):
        with self._lock:
            self._store.pop(key, None)

    def eval(self, script, numkeys, *args):
        """Simulate the Lua release-lock script."""
        key = args[0]
        expected_value = args[1]
        with self._lock:
            if self._store.get(key) == expected_value:
                self._store.pop(key, None)
                return 1
            return 0


# ===================================================================
# Test: Single computation under concurrent access
# ===================================================================
class TestStampedeProtectionConcurrency(unittest.TestCase):
    """50 threads request the same key. Compute should run ONCE."""

    def test_single_computation_under_concurrent_access(self):
        redis_client = FakeRedis()
        protection = StampedeProtection(redis_client)
        fake_cache = FakeCache()

        computation_count = 0
        count_lock = threading.Lock()

        def expensive_computation():
            nonlocal computation_count
            with count_lock:
                computation_count += 1
            time.sleep(0.2)  # simulate slow query
            return {"result": "computed"}

        results = []
        errors = []

        def worker():
            try:
                result = protection.get_or_compute(
                    cache_key="test:stampede",
                    compute_func=expensive_computation,
                    cache_instance=fake_cache,
                    expire=60,
                )
                results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        self.assertEqual(len(errors), 0, f"Errors: {errors}")
        self.assertEqual(computation_count, 1, "Compute should run exactly once")
        self.assertEqual(len(results), 50, "All 50 threads should get a result")


# ===================================================================
# Test: Lock safety — release only your own lock
# ===================================================================
class TestLockSafety(unittest.TestCase):

    def test_release_only_own_lock(self):
        redis_client = FakeRedis()
        protection = StampedeProtection(redis_client)

        # Process A acquires lock
        acquired_a, value_a = protection._acquire_lock("mykey")
        self.assertTrue(acquired_a)

        # Process B tries to release A's lock with a different value
        protection._release_lock("mykey", "wrong-value")

        # Lock should still exist (A's lock was NOT released)
        self.assertIsNotNone(redis_client.get("lock:mykey"))

        # Process A releases its own lock
        protection._release_lock("mykey", value_a)
        self.assertIsNone(redis_client.get("lock:mykey"))


# ===================================================================
# Test: Fallback without StampedeProtection (no Redis)
# ===================================================================
class TestFallbackWithoutRedis(unittest.TestCase):

    @patch("backend.core.cache_stampede.get_stampede_protection", return_value=None)
    @patch("backend.services.cache_service.cache")
    def test_decorator_works_without_protection(self, mock_cache, mock_get_prot):
        """When no Redis/protection is available, @cached still works."""
        from backend.services.cache_service import cached

        mock_cache.get.return_value = None  # cache miss

        call_count = 0

        @cached(key_prefix="test_prefix", expire=60)
        def my_func(x, y):
            nonlocal call_count
            call_count += 1
            return {"sum": x + y}

        result = my_func(1, 2)
        self.assertEqual(result, {"sum": 3})
        self.assertEqual(call_count, 1)
        mock_cache.set.assert_called_once()


# ===================================================================
# Test: Cache key excludes non-serializable objects
# ===================================================================
class TestCacheKeyBuilder(unittest.TestCase):

    def test_excludes_session(self):
        mock_session = MagicMock(spec=["__class__"])
        mock_session.__class__ = type("Session", (), {})
        # Simulate SQLAlchemy Session by using the actual type check
        from sqlalchemy.orm import Session
        real_session = MagicMock(spec=Session)

        key = _build_cache_key("prefix", (real_session, 42), {})
        self.assertNotIn("Session", key)
        self.assertIn("42", key)
        self.assertEqual(key, "prefix:42")

    def test_excludes_request_like_objects(self):
        mock_request = MagicMock()
        mock_request.scope = {}
        mock_request.headers = {}
        mock_request.state = MagicMock()

        key = _build_cache_key("stats", (mock_request,), {"tenant_id": 5})
        self.assertNotIn("Mock", key)
        self.assertEqual(key, "stats:tenant_id=5")

    def test_excludes_orm_model(self):
        mock_user = MagicMock()
        mock_user.__tablename__ = "users"

        key = _build_cache_key("data", (mock_user,), {"doctor_id": 3})
        self.assertEqual(key, "data:doctor_id=3")

    def test_includes_simple_values(self):
        key = _build_cache_key("pref", (1, "hello"), {"a": 10, "b": 20})
        self.assertEqual(key, "pref:1:hello:a=10:b=20")

    def test_is_serializable_basic_types(self):
        self.assertTrue(_is_serializable_arg(42))
        self.assertTrue(_is_serializable_arg("text"))
        self.assertTrue(_is_serializable_arg(3.14))
        self.assertTrue(_is_serializable_arg(None))


if __name__ == "__main__":
    unittest.main()
