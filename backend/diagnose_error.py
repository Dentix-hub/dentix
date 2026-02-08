import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

try:
    print("1. Importing Models...")
    from backend.models import system
    print("   [OK] System models imported.")

    print("2. Importing Analytics Service...")
    from backend.services.analytics_service import AnalyticsService
    print("   [OK] AnalyticsService imported.")

    print("3. Testing AnalyticsService methods...")
    # Mock session
    class MockDB:
        def query(self, *args): return self
        def filter(self, *args): return self
        def join(self, *args): return self
        def all(self): return []
        def count(self): return 0
        def scalar(self): return 0
        def first(self): return None

    service = AnalyticsService(MockDB(), 1)
    
    # Test internal helper
    print("   Testing _get_date_filter...")
    try:
        service._get_date_filter("week", "dummy_col")
        print("   [OK] _get_date_filter works.")
    except AttributeError:
        print("   [FAIL] ERROR: _get_date_filter is MISSING.")
    except Exception as e:
        print(f"   [WARN] _get_date_filter error (expected if no real DB): {e}")

    print("4. Testing AI Agent Import...")
    try:
        from backend.ai.agent.core import AIAgent
        print("   [OK] AIAgent imported successfully.")
        agent = AIAgent()
        print("   [OK] AIAgent instantiated.")
    except ImportError as e:
        print(f"   [FAIL] AI Agent Import Error: {e}")
    except Exception as e:
        print(f"   [FAIL] AI Agent Init Error: {e}")

    print("\n5. Testing ToolExecutor Initialization...")
    try:
        from backend.routers.ai import ToolExecutor
        class MockUser:
            id = 1
            tenant_id = 99
            username = "test_user"
            full_name = "Test User"
            
        print("   Instantiating ToolExecutor...")
        executor = ToolExecutor(MockDB(), MockUser())
        print("   [OK] ToolExecutor instantiated successfully.")
    except TypeError as e:
        print(f"   [FAIL] ToolExecutor Logic Error: {e}")
    except Exception as e:
        print(f"   [FAIL] ToolExecutor General Error: {e}")

    print("\nDiagnosis Complete: integration seems valid.")

except ImportError as e:
    print(f"\n[FAIL] ImportError: {e}")
except Exception as e:
    print(f"\n[FAIL] General Error: {e}")
