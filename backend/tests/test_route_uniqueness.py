from collections import defaultdict

from backend.main import app


def test_fastapi_has_no_duplicate_method_path_pairs():
    routes_by_key = defaultdict(list)
    for route in app.routes:
        for method in getattr(route, "methods", set()):
            if method not in {"HEAD", "OPTIONS"}:
                routes_by_key[(method, route.path)].append(route.name)

    duplicates = {
        key: names for key, names in routes_by_key.items() if len(names) > 1
    }
    assert duplicates == {}
