import os
from backend.google_drive_client import get_client_config

# Mocking env if needed
# os.environ["GOOGLE_CLIENT_ID"] = "test"

try:
    config = get_client_config()
    print(f"CLIENT_ID: {config['web']['client_id']}")
    print(f"REDIRECT_URI: {config['web']['redirect_uris'][0]}")
except Exception as e:
    print(f"Error: {e}")
