import requests

def test_options(url):
    print(f"Testing OPTIONS {url} ...")
    try:
        headers = {
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type"
        }
        response = requests.options(url, headers=headers, timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Headers: {response.headers}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_options("http://127.0.0.1:8000/api/v1/token")
