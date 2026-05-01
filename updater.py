import os
import sys
import time
import zipfile
import shutil
import urllib.request
import json
import subprocess

# ==========================================
# DENTIX Auto Updater
# ==========================================

# Settings
UPDATE_API_URL = "https://api.dentix.com/v1/desktop/check-updates"
CURRENT_VERSION = "2.0.7"
APP_EXECUTABLE = "DENTIX_Offline.exe"

def wait_for_app_to_close():
    """Wait until the main application is fully closed to avoid file lock errors."""
    print("Waiting for DENTIX to close...")
    # Give the OS a few seconds to release file locks
    time.sleep(3)

def check_for_updates():
    """Check the server for a newer version."""
    print(f"Checking for updates (Current: v{CURRENT_VERSION})...")
    try:
        req = urllib.request.Request(UPDATE_API_URL, headers={'User-Agent': 'DENTIX-Updater'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data.get("version") > CURRENT_VERSION:
                return data.get("download_url")
    except Exception as e:
        print(f"Could not check for updates: {e}")
    return None

def download_update(url, temp_file="update_patch.zip"):
    """Download the update zip file from the server."""
    print(f"Downloading update from {url}...")
    try:
        urllib.request.urlretrieve(url, temp_file)
        print("Download complete.")
        return temp_file
    except Exception as e:
        print(f"Failed to download update: {e}")
        return None

def apply_patch(zip_path):
    """Extract the zip file, overwriting old files."""
    print(f"Applying patch from {zip_path}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract to the current directory (where the updater is running)
            zip_ref.extractall(".")
        print("Patch applied successfully.")
        return True
    except Exception as e:
        print(f"Failed to apply patch: {e}")
        return False

def restart_app():
    """Restart the main application."""
    print("Restarting DENTIX...")
    if os.path.exists(APP_EXECUTABLE):
        subprocess.Popen([APP_EXECUTABLE])
    else:
        print("Error: Could not find main executable to restart.")

def main():
    # If a manual update file is dragged onto the updater or passed as argument
    if len(sys.argv) > 1 and sys.argv[1].endswith('.zip'):
        manual_patch = sys.argv[1]
        print(f"Manual update detected: {manual_patch}")
        wait_for_app_to_close()
        if apply_patch(manual_patch):
            restart_app()
        sys.exit(0)

    # Otherwise, Auto-Update Mode
    download_url = check_for_updates()
    if download_url:
        ans = input("New update found! Download and install now? (y/n): ")
        if ans.lower() == 'y':
            wait_for_app_to_close()
            patch_file = download_update(download_url)
            if patch_file and apply_patch(patch_file):
                os.remove(patch_file) # Cleanup
                print("Update finished.")
            restart_app()
        else:
            print("Update cancelled by user.")
    else:
        print("You are on the latest version.")
        time.sleep(2)

if __name__ == "__main__":
    main()
