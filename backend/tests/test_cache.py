from backend.core.cache import CacheManager


def test_cache_manager():
    # 1. Initialize Cache Manager (Will default to Local Memory if no Redis)
    cm = CacheManager()
    print(f"Using Redis: {cm.use_redis}")

    # 2. Test SET
    test_key = "test_key_123"
    test_val = {"foo": "bar", "num": 100}
    cm.set(test_key, test_val, expire=5)

    # 3. Test GET
    retrieved = cm.get(test_key)
    print(f"Retrieved: {retrieved}")
    assert retrieved == test_val
    assert retrieved["foo"] == "bar"

    # 4. Test DELETE
    cm.delete(test_key)
    deleted = cm.get(test_key)
    assert deleted is None
    print("Delete Verification Successful")


if __name__ == "__main__":
    test_cache_manager()
