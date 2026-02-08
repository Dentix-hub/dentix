import requests

def test_url(url):
    print(f"Testing {url} ...")
    try:
        response = requests.get(url, timeout=5)
        print(f"[{response.status_code}] {url}")
        if response.status_code != 404:
            print(f"MATCH FOUND! Status: {response.status_code}")
            return True
    except Exception as e:
        print(f"Error testing {url}: {e}")
    return False

if __name__ == "__main__":
    base = "http://127.0.0.1:8000"
    paths = [
        "/api/v1/admin/tenants",
        "/api/v1/admin/admin/tenants",
        "/admin/tenants",
        "/api/v1/tenants",
        "/tenants",
        "/api/v1/admin/system",
        "/api/v1/system/logs"
    ]
    
    found = False
    for p in paths:
        if test_url(base + p):
            found = True
            
    if not found:
        print("NO MATCHING ROUTE FOUND.")
