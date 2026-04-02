import requests
import os

BASE_URL = "http://127.0.0.1:8000/api/v1"
USERNAME = "eslamemara1312@gmail.com"
PASSWORD = os.environ.get("SUPER_ADMIN_PASSWORD", "ESLAMomara11##")

def verify():
    # 1. Login
    print("Logging in...")
    try:
        resp = requests.post(f"{BASE_URL}/token", data={"username": USERNAME, "password": PASSWORD})
        if resp.status_code != 200:
            print(f"Login failed: {resp.status_code} {resp.text}")
            return
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Login success.")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    # 2. Check Dashboard Stats
    print("\nChecking Dashboard Stats...")
    resp = requests.get(f"{BASE_URL}/stats/dashboard", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        print("Dashboard Stats OK:")
        print(f"  Total Patients: {data.get('total_patients')}")
        print(f"  Total Appointments: {data.get('today_appointments')}")
        print(f"  Today Revenue: {data.get('today_revenue')}")
    else:
        print(f"Dashboard Stats Failed: {resp.status_code} {resp.text}")

    # 3. Check Appointments (with slash)
    print("\nChecking Appointments (with slash)...")
    resp = requests.get(f"{BASE_URL}/appointments/", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        print(f"Appointments OK. Count: {len(data)}")
    else:
        print(f"Appointments Failed: {resp.status_code} {resp.text}")

    # 4. Check Patients (with slash)
    print("\nChecking Patients (with slash)...")
    resp = requests.get(f"{BASE_URL}/patients/", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        print(f"Patients OK. Count: {len(data)}")
    else:
        print(f"Patients Failed: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    verify()
