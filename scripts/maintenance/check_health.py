import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import requests
try:
    r = requests.get("http://127.0.0.1:8000/", timeout=3)
    print(f"Root Status: {r.status_code}")
    print(r.json())
except Exception as e:
    print(f"Error: {e}")
