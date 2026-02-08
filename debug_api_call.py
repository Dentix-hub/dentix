import requests
import json
import os

BASE_URL = "http://localhost:8000/api/v1"

# 1. Login to get token
def login():
    print("Logging in...")
    try:
        resp = requests.post(f"{BASE_URL}/token", data={
            "username": "eslam",
            "password": "password123"
        })
        if resp.status_code != 200:
            print(f"Login Failed: {resp.text}")
            return None
        return resp.json()["access_token"]
    except Exception as e:
        print(f"Connection Error: {e}")
        return None

def test_analyze_clinic(token):
    print("\nTesting /admin/ai/analyze-clinic...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Payload matching Frontend
    payload = {
        "revenue": 10000.0,
        "breakdown": {
            "expenses": 2000.0,
            "lab_costs": 500.0,
            "material_costs": 1000.0
        },
        "total_costs": 3500.0,
        "net_profit": 6500.0,
        "margin_percent": 65.0
    }
    
    try:
        resp = requests.post(
            f"{BASE_URL}/admin/ai/analyze-clinic", 
            json=payload, 
            headers=headers
        )
        print(f"Status: {resp.status_code}")
        print("Response:")
        print(resp.text)
    except Exception as e:
        print(f"Request Failed: {e}")

if __name__ == "__main__":
    token = login()
    if token:
        test_analyze_clinic(token)
