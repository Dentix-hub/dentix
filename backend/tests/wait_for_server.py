import time
import requests
import sys

def wait_for_server():
    url = "http://localhost:8000/health"
    print(f"Waiting for server at {url}...")
    for i in range(30):
        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                print(f"[OK] Server is ready! (Attempt {i+1})")
                return
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
        print(".", end="", flush=True)
    
    print("\n[FAIL] Server did not start in time.")
    sys.exit(1)

if __name__ == "__main__":
    wait_for_server()
