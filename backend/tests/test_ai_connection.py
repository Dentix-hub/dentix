import os
import sys
from dotenv import load_dotenv

# Add project root to sys.path to allow 'backend' imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print(f"Current Working Directory: {os.getcwd()}")

# Load .env
if os.path.exists(".env"):
    print("Found .env in current directory.")
    load_dotenv()
elif os.path.exists("../.env"):
    print("Found .env in parent directory.")
    load_dotenv("../.env")
else:
    print("WARNING: No .env file found!")

key = os.getenv("GROQ_API_KEY")
print(f"GROQ_API_KEY present: {bool(key)}")
if key:
    print(f"Key preview: {key[:4]}...{key[-4:]}")

try:
    # Attempt import using full package path
    from backend.ai.agent.core import get_agent

    print("Attempting to initialize Agent...")
    agent = get_agent()
    print("Agent initialized successfully.")

except Exception as e:
    print(f"ERROR: Agent initialization failed: {e}")
    import traceback

    traceback.print_exc()
