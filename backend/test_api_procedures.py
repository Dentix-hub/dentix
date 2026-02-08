import requests
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_api():
    try:
        # Login
        print("Logging in...")
        resp = requests.post(f"{BASE_URL}/token", data={"username": "admin", "password": "admin123"})
        if resp.status_code != 200:
            print(f"Login failed: {resp.text}")
            return
        
        token = resp.json()["access_token"]
        print("Login success.")
        
        # Get Procedures
        headers = {"Authorization": f"Bearer {token}"}
        print("Fetching Procedures...")
        resp = requests.get(f"{BASE_URL}/procedures/", headers=headers)
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"Success! Found {len(data)} procedures.")
            if len(data) > 0:
                print(f"First item: {data[0]['name']}")
        else:
            print(f"Failed to get procedures: {resp.status_code} - {resp.text}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()
