
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from fastapi import FastAPI
from backend.main import app

def verify_router_registration():
    print("Verifying router registration...")
    routes = [route.path for route in app.routes]
    
    expected_routes = [
        "/admin/ai/stats",
        "/admin/ai/intents",
        "/admin/ai/logs"
    ]
    
    missing = []
    for route in expected_routes:
        if route not in routes:
            print(f"❌ Missing route: {route}")
            missing.append(route)
        else:
            print(f"✅ Found route: {route}")
            
    if missing:
        print("Verification FAILED.")
        sys.exit(1)
    else:
        print("Verification PASSED. All AI Analytics routes are active.")
        sys.exit(0)

if __name__ == "__main__":
    verify_router_registration()
