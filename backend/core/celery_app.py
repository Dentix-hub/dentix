import os
from celery import Celery
from dotenv import load_dotenv

# Load env vars
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(BACKEND_DIR, ".env")
load_dotenv(env_path)

# Redis Credentials
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery
celery_app = Celery(
    "smart_clinic_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["backend.tasks.email_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Resilience
    broker_connection_retry_on_startup=True,
)

if __name__ == "__main__":
    celery_app.start()
