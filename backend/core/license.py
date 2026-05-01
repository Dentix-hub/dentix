import os
import hashlib
import platform
import subprocess
import socket
import uuid

APP_DATA_DIR = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "DentixOffline")
LICENSE_FILE = os.path.join(APP_DATA_DIR, "license.key")

def get_machine_id():
    """Get a unique hardware ID for the machine with multiple fallbacks."""
    methods = []
    
    # Method 1: Windows UUID (Best)
    if platform.system() == "Windows":
        try:
            output = subprocess.check_output("wmic csproduct get uuid", shell=True, text=True, creationflags=0x08000000)
            uid = output.split('\n')[1].strip()
            if uid and len(uid) > 5 and uid != "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF":
                return uid
        except Exception:
            pass

    # Method 2: Disk Serial (Stable)
    if platform.system() == "Windows":
        try:
            output = subprocess.check_output("wmic diskdrive get serialnumber", shell=True, text=True, creationflags=0x08000000)
            serial = output.split('\n')[1].strip()
            if serial:
                return f"DISK-{serial}"
        except Exception:
            pass

    # Method 3: MAC Address (Fallback)
    try:
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0, 8*6, 8)][::-1])
        if mac and mac != '00:00:00:00:00:00':
            return f"MAC-{mac.upper()}"
    except Exception:
        pass

    # Method 4: CPU ID
    if platform.system() == "Windows":
        try:
            output = subprocess.check_output("wmic cpu get processorid", shell=True, text=True, creationflags=0x08000000)
            cpuid = output.split('\n')[1].strip()
            if cpuid:
                return f"CPU-{cpuid}"
        except Exception:
            pass

    return "OFFLINE-GENERIC-ID-001"

def generate_license_key(machine_id):
    """Generate a license key based on the machine ID."""
    hash_obj = hashlib.sha256((machine_id.strip() + "DENTIX_SECRET_KEY").encode())
    hash_hex = hash_obj.hexdigest().upper()
    return f"{hash_hex[:4]}-{hash_hex[4:8]}-{hash_hex[8:12]}-{hash_hex[12:16]}-{hash_hex[16:20]}"

def save_license(key):
    """Save the license key to disk if it's valid."""
    key = key.strip()
    expected_key = generate_license_key(get_machine_id())
    if key == expected_key:
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        with open(LICENSE_FILE, "w") as f:
            f.write(key)
        return True
    return False

def load_license():
    """Load the license key from disk."""
    if os.path.exists(LICENSE_FILE):
        with open(LICENSE_FILE, "r") as f:
            return f.read().strip()
    return None

def is_license_valid():
    """Check if the current license is valid for this machine."""
    current_key = load_license()
    if not current_key:
        return False
    
    expected_key = generate_license_key(get_machine_id())
    return current_key == expected_key
