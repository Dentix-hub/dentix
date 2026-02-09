import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
"""
Direct test: Import get_detailed_analytics from the RENAMED file (analytics_ai_v2.py)
and run it to confirm it works without User.full_name errors.
"""
import sys
import os
sys.path.insert(0, os.getcwd())

# Force import from the renamed file
from backend.routers.analytics_ai_v2 import get_detailed_analytics
from backend.database import SessionLocal

def test():
    db = SessionLocal()
    try:
        # Use a valid tenant_id (1 is usually default)
        result = get_detailed_analytics(db, tenant_id=1, days=30)
        print("SUCCESS! get_detailed_analytics returned:")
        print(result[:500] if len(result) > 500 else result)
    except Exception as e:
        print(f"FAILED with error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test()
