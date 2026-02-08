import requests

def test_login(url, username, password):
    print(f"Testing Login to {url} ...")
    try:
        data = {"username": username, "password": password}
        response = requests.post(url, data=data, timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("Login SUCCESS!")
            print(f"Token: {response.json().get('access_token')[:20]}...")
        else:
            print(f"Login FAILED. Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_login(
        "http://127.0.0.1:8000/api/v1/token",
        "eslamemara1312@gmail.com",
        "ESLAMomara11##"
    )
