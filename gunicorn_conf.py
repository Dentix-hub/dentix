import os

workers = 4  # Adjust based on CPU cores
worker_class = "uvicorn.workers.UvicornWorker"
bind = "0.0.0.0:" + os.getenv("PORT", "8000")
timeout = 120  # Increased timeout for AI operations
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
