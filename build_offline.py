import os
import shutil
import subprocess
import sys

# ==========================================
# Build Pipeline for DENTIX Offline (Desktop)
# ==========================================

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
DIST_OBF_DIR = os.path.join(PROJECT_ROOT, "dist_obf")

def run_command(cmd, cwd=PROJECT_ROOT):
    print(f"\n[EXEC] {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"\n[ERROR] Command failed with exit code {result.returncode}")
        sys.exit(1)

def build_frontend():
    print("\n=== 1. Building React Frontend ===")
    
    # Create .env.desktop to point to localhost
    env_desktop = os.path.join(FRONTEND_DIR, ".env.production")
    with open(env_desktop, 'w') as f:
        # For offline, we point to localhost. Notice that desktop_app.py assigns a random port if 8000 is taken,
        # but typically frontend relative paths (/) work best if served from the same origin!
        # So we leave API URL empty or '/' to let it use the current host.
        f.write("VITE_API_BASE_URL=\n")
        f.write("VITE_APP_ENV=offline\n")

    run_command("npm install", cwd=FRONTEND_DIR)
    run_command("npm run build", cwd=FRONTEND_DIR)
    
    source_dist = os.path.join(FRONTEND_DIR, "dist")
    target_static = os.path.join(BACKEND_DIR, "static")
    
    if os.path.exists(target_static):
        shutil.rmtree(target_static)
        
    print(f"Copying {source_dist} to {target_static}")
    shutil.copytree(source_dist, target_static)

def obfuscate_backend():
    print("\n=== 2. Obfuscating Python Code (PyArmor) ===")
    run_command("pip install pyarmor pyinstaller pywebview")
    
    if os.path.exists(DIST_OBF_DIR):
        shutil.rmtree(DIST_OBF_DIR)
        
    # Pyarmor 8 command to obfuscate the backend directory recursively
    run_command(f"pyarmor gen -O {DIST_OBF_DIR} backend")
    
    # We also need to copy the static files into the obfuscated directory
    # so that Pyinstaller bundles them correctly
    source_static = os.path.join(BACKEND_DIR, "static")
    target_static = os.path.join(DIST_OBF_DIR, "backend", "static")
    if os.path.exists(source_static):
        shutil.copytree(source_static, target_static)

def build_executable():
    print("\n=== 3. Packaging Desktop Application (PyInstaller) ===")
    
    # Separator for PyInstaller add-data varies by OS (Windows uses ';', Linux/Mac uses ':')
    sep = ';' if os.name == 'nt' else ':'
    
    # PyInstaller options
    # Hidden imports needed for SQLite offline mode (not auto-detected from dynamic URLs)
    hidden_imports = [
        'aiosqlite',
        'sqlite3',
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.dialects.sqlite.aiosqlite',
    ]
    hidden_str = ' '.join(f'--hidden-import {m}' for m in hidden_imports)
    
    cmd = (
        'pyinstaller --noconfirm --onedir --windowed '
        '--name "DENTIX_Offline" '
        f'{hidden_str} '
        f'--add-data "{DIST_OBF_DIR}/backend{sep}backend" '
        'desktop_app.py'
    )
    
    run_command(cmd)

if __name__ == "__main__":
    print(" Starting DENTIX Offline Build Pipeline...")
    build_frontend()
    obfuscate_backend()
    build_executable()
    print("\n === BUILD COMPLETE ===")
    print("Your desktop application is ready in the 'dist/DENTIX_Offline' folder.")
