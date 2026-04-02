import requests
import os
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"
USERNAME = "eslamemara1312@gmail.com"
PASSWORD = os.environ.get("SUPER_ADMIN_PASSWORD", "ESLAMomara11##")

def verify():
    # 1. Login
    try:
        resp = requests.post(f"{BASE_URL}/token", data={"username": USERNAME, "password": PASSWORD})
        if resp.status_code != 200:
            print(f"Login failed: {resp.status_code} {resp.text}")
            return
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    # 2. Check Dashboard Stats Keys
    print("\nChecking Dashboard Stats Keys...")
    resp = requests.get(f"{BASE_URL}/stats/dashboard", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        print("Keys found: " + ", ".join(data.keys()))
        print(json.dumps(data, indent=2))
    else:
        print(f"Dashboard Stats Failed: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    verify()
