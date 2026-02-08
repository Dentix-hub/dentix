
import sys
import os

# Add root to sys.path
sys.path.append(os.getcwd())

try:
    print("Testing imports...")
    from backend.ai.analytics.service import AIAnalyticsService
    print("Import Successful!")
    
    # Mock DB Session
    class MockQuery:
        def filter(self, *args, **kwargs): return self
        def count(self): return 10
        def group_by(self, *args): return self
        def order_by(self, *args): return self
        def limit(self, *args): return self
        def all(self): return []

    class MockDB:
        def query(self, *args): return MockQuery()

    print("Testing get_stats...")
    stats = AIAnalyticsService.get_stats(MockDB(), "month", 1)
    print("Execution Successful!")
    print(stats)

except Exception as e:
    print("CRASHED!")
    import traceback
    traceback.print_exc()
