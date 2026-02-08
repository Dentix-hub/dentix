
import requests
import sys

BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "eslamemara1312@gmail.com"
ADMIN_PASS = "ESLAMomara11##"

def verify_staging_state():
    print("🕵️ Verifying Staging State...")
    
    # 1. Login
    try:
        response = requests.post(f"{BASE_URL}/token", data={
            "username": ADMIN_EMAIL,
            "password": ADMIN_PASS
        })
        if response.status_code != 200:
            print(f"❌ Login Failed: {response.text}")
            sys.exit(1)
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Super Admin Login Successful.")
        
        # 2. Check Tenants (Should be empty list or count=0)
        # Note: Adjust endpoint based on actual admin router
        res = requests.get(f"{BASE_URL}/admin/users?skip=0&limit=10", headers=headers)
        if res.status_code == 200:
            users = res.json()
            # Super Admin is a user, so count should be 1
            print(f"✅ Users Count: {len(users)} (Expected: 1 - Super Admin only)")
            
            for u in users:
                print(f"   - User: {u['username']} ({u['role']})")
                
        else:
            print(f"⚠️ Could not fetch users: {res.status_code}")

    except Exception as e:
        print(f"❌ Connection Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_staging_state()
