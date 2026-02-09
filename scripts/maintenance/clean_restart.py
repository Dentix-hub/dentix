import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import os
import shutil
import psutil
import time

def kill_uvicorn():
    print("Killing uvicorn processes...")
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'uvicorn' in proc.info['name'] or 'uvicorn' in (proc.info['cmdline'] or []):
                print(f"Killing PID {proc.info['pid']}")
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

def clean_pycache(start_dir):
    print(f"Cleaning __pycache__ in {start_dir}...")
    for root, dirs, files in os.walk(start_dir):
        for d in dirs:
            if d == "__pycache__":
                path = os.path.join(root, d)
                print(f"Removing {path}")
                try:
                    shutil.rmtree(path)
                except Exception as e:
                    print(f"Failed to remove {path}: {e}")
        
        for f in files:
            if f.endswith(".pyc"):
                path = os.path.join(root, f)
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"Failed to remove {path}: {e}")

if __name__ == "__main__":
    kill_uvicorn()
    time.sleep(1)
    clean_pycache("backend")
    print("Deep clean completed.")
