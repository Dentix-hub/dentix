import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.core.celery_app import celery_app
from backend.tasks.email_tasks import send_connection_email
import time

def test_celery_config():
    print("1. Inspecting Config...")
    print(f"Broker: {celery_app.conf.broker_url}")
    print(f"Tasks: {celery_app.tasks.keys()}")
    
    assert "send_connection_email" in celery_app.tasks
    print("[OK] Celery App Configured.")

    print("\n2. Testing Task Logic (Synchronous execution)...")
    # We use .apply() to run locally in this process, bypassing the broker/worker
    result = send_connection_email.apply(kwargs={
        "email": "test@example.com", 
        "subject": "Test Subject", 
        "message": "Hello World"
    })
    
    print(f"Task Result: {result.result}")
    assert result.status == 'SUCCESS'
    print("[OK] Task Logic Verified.")

if __name__ == "__main__":
    test_celery_config()
