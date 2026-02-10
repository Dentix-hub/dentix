import requests


def debug_root_tenants():
    url = "http://127.0.0.1:8000/tenants"
    print(f"Testing {url} content...")
    try:
        response = requests.get(url, timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print(f"Content Snippet: {response.text[:100]}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    debug_root_tenants()
