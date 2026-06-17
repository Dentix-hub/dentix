import logging
from backend.tasks.email_flows import send_connection_email_flow

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    print("[PREFECT] Starting Prefect worker flow server...")
    # Serves the flow locally, creating a deployment and runner
    send_connection_email_flow.serve(name="email-worker-deployment")
