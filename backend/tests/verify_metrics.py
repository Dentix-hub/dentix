import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi.testclient import TestClient
from backend.main import app

def test_metrics_endpoint():
    client = TestClient(app)
    
    # We trigger the startup event manually if TestClient doesn't automatically
    # But TestClient manages context usually.
    # Note: Instrumentator().expose(app) adds the route immediately usually, 
    # but inside startup_event it happens on startup.
    # TestClient calls startup handlers inside a context manager.
    
    with TestClient(app) as client:
        response = client.get("/metrics")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("[OK] Metrics endpoint is active.")
            print(f"Content Preview: {response.text[:100]}")
        else:
            print("[FAIL] Metrics endpoint not accessible.")
            # Verify routes
            print("Routes:", [route.path for route in app.routes])

if __name__ == "__main__":
    test_metrics_endpoint()
