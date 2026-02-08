import requests
import sys

def test_url(url):
    print(f"Testing {url} ...")
    try:
        # We expect a 422 (Validation Error) or 401 (Unauthorized) if the route exists
        # We expect a 404 Not Found or 405 Method Not Allowed if it doesn't
        response = requests.post(url, data={"username": "test", "password": "test"}, timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("--- DIAGNOSTIC START ---")
    test_url("http://127.0.0.1:8000/api/v1/token")
    test_url("http://127.0.0.1:8000/token")
    print("--- DIAGNOSTIC END ---")
