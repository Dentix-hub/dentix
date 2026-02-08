import pytest
import logging
from httpx import AsyncClient
from backend.main import app

# We need async client for full middleware stack testing usually, 
# or TestClient which handles it synchronously.
from fastapi.testclient import TestClient

client = TestClient(app)

def test_security_headers_presence():
    response = client.get("/")  # Assuming / exists or 404 is fine, headers should still be there
    # Note: Middlewares run even on 404s usually
    
    # If / doesn't exist, try /docs or /health if mapped
    if response.status_code == 404:
        print("Note: Root path returned 404, but checking headers anyway.")

    headers = response.headers
    print("Response Headers:", headers)

    assert "Strict-Transport-Security" in headers
    assert "max-age=31536000" in headers["Strict-Transport-Security"]
    
    assert "X-Content-Type-Options" in headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    
    assert "X-Frame-Options" in headers
    assert headers["X-Frame-Options"] == "SAMEORIGIN"
    
    assert "Content-Security-Policy" in headers
    assert "default-src 'self'" in headers["Content-Security-Policy"]

if __name__ == "__main__":
    test_security_headers_presence()
