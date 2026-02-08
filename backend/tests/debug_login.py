import requests
import sys

def debug_login():
    url = "http://localhost:8000/token"
    # Try the credentials we expect
    payload = {
        "username": "eslamemara1312@gmail.com",
        "password": "ESLAMomara11##"
    }
    
    try:
        print(f"Attempting login to {url}...")
        resp = requests.post(url, data=payload)
        
        print(f"Status Code: {resp.status_code}")
        print(f"Response Body: {resp.text}")
        
        if resp.status_code == 200:
            print("[SUCCESS] Login worked!")
            token = resp.json().get("access_token")
            print(f"Token: {token[:20]}...")
        else:
            print("[FAIL] Login failed.")
            
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")

if __name__ == "__main__":
    debug_login()
