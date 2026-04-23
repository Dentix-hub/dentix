import requests

endpoints = [
    "/api/v1/inventory/materials",
    "/api/v1/inventory/smart/suggestions/1",
    "/api/v1/inventory/smart/suggestions-categories/1"
]

base_url = "https://dentix-dentix-staging.hf.space"

for ep in endpoints:
    url = base_url + ep
    try:
        response = requests.get(url, timeout=10)
        print(f"Endpoint: {ep}")
        print(f"  Status Code: {response.status_code}")
        print(f"  Response Body: {response.text[:100]}")
    except Exception as e:
        print(f"  Error: {e}")
