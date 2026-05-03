from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel
from unittest.mock import MagicMock


# Mock dependencies
def get_db():
    yield MagicMock()


def get_current_user():
    user = MagicMock()
    user.id = 1
    user.tenant_id = 99
    return user


# Mock Models
class AIQueryRequest(BaseModel):
    query: str
    context: dict = {}


class AIQueryResponse(BaseModel):
    message: str


# Recreate the router logic minimally to verify signature
app = FastAPI()


@app.post("/test-ai")
async def ai_query(
    request: AIQueryRequest,
    raw_request: Request,
):
    # This is the line that was failing
    trace_id = getattr(raw_request.state, "trace_id", "default_trace")
    return {"message": f"Success! Trace ID: {trace_id}"}


client = TestClient(app)


def test_endpoint():
    print("Testing Endpoint with Raw Request Injection...")
    try:
        response = client.post("/test-ai", json={"query": "hello"})
        if response.status_code == 200:
            print(f"   [OK] Response: {response.json()}")
        else:
            print(f"   [FAIL] Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        print(f"   [FAIL] Exception: {e}")


if __name__ == "__main__":
    test_endpoint()
