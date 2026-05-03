import requests

# This script attempts to login with a known bad password to see the error response

URL = "http://localhost:8000/token"


def test_login_error():
    print(f"Target: {URL}")

    # Payload as FORM DATA (standard OAuth2)
    payload = {"username": "admin", "password": "WrongPassword123!"}

    try:
        response = requests.post(URL, data=payload)

        print(f"Status Code: {response.status_code}")
        print("Response Body:")
        print(response.text)

        if response.status_code == 401:
            if "اسم المستخدم أو كلمة الصفحة غير صحيحة" in response.text:
                print(
                    "\n✅ PASS: Backend is returning the correct custom error message."
                )
            else:
                print("\n⚠️ WARN: Backend returns 401 but message is different.")
        elif response.status_code == 422:
            print(
                "\n❌ FAIL: Backend returned 422 Validation Error (Frontend sending JSON?)."
            )
        elif response.status_code == 500:
            print("\n❌ FAIL: Backend returned 500 Internal Server Error.")
        else:
            print(f"\n❓ UNEXPECTED: {response.status_code}")

    except Exception as e:
        print(f"Connection Failed: {e}")


if __name__ == "__main__":
    test_login_error()
