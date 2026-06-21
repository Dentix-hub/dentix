import os
import sys
import time
import shutil
import subprocess
import tarfile
import argparse

# Force UTF-8 encoding for standard output and error on Windows terminals
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
if sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Configuration
STAGING_REPO_URL = "https://huggingface.co/spaces/dentix/dentix-staging"
STAGING_CLONE_DIR = ".hf-deploy-staging"

PRODUCTION_IP = "134.209.206.63"
PRODUCTION_USER = "root"
PRODUCTION_SSH_KEY = os.path.expanduser("~/.ssh/id_ed25519")
PRODUCTION_DEST_DIR = "/root/dentix"

STAGING_IGNORE_PATTERNS = shutil.ignore_patterns(
    "__pycache__", "*.pyc", "venv", ".venv", ".env", "*.db", "*.sqlite", "uploads", "*.log", ".git", ".pytest_cache",
    "node_modules", "dist", ".vite", "coverage", "test-results"
)

def run_local_command(command, cwd=None, print_output=True):
    """Run a local shell command and return status + output."""
    if print_output:
        print(f"📁 Running locally: {command}")
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        if print_output:
            print(f"❌ Command failed: {e.stderr}")
        return False, e.stderr

def run_remote_ssh(command):
    """Execute a command on the DigitalOcean Droplet via SSH."""
    ssh_cmd = f'ssh -i "{PRODUCTION_SSH_KEY}" -o StrictHostKeyChecking=accept-new {PRODUCTION_USER}@{PRODUCTION_IP} "{command}"'
    print(f"🌐 Running on Droplet: {command}")
    return run_local_command(ssh_cmd, print_output=False)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def deploy_staging():
    print("\n==================================================")
    print("🚀 DEPLOYING TO STAGING (Hugging Face)")
    print("==================================================")
    
    source_dir = os.getcwd()
    clone_dir = os.path.join(source_dir, STAGING_CLONE_DIR)
    
    # 1. Clone or pull staging repository
    if os.path.exists(clone_dir):
        print("📥 Updating existing Hugging Face staging clone...")
        run_local_command("git reset --hard HEAD", cwd=clone_dir)
        run_local_command("git pull --rebase", cwd=clone_dir)
    else:
        print("📥 Cloning Hugging Face staging repository...")
        success, err = run_local_command(f"git clone {STAGING_REPO_URL} {clone_dir}")
        if not success:
            print("❌ Clone failed. Make sure you have Hugging Face git credentials set up.")
            return False
            
    if not os.path.exists(clone_dir):
        print("❌ Staging directory not found. Aborting.")
        return False

    # Ensure LFS locking verify is disabled to prevent push aborts on Hugging Face
    run_local_command("git config lfs.https://huggingface.co/spaces/dentix/dentix-staging.git/info/lfs.locksverify false", cwd=clone_dir, print_output=False)

    # 2. Clean destination folders in the clone
    print("🧹 Cleaning destination staging folders...")
    for folder in ["backend", "frontend", "scripts"]:
        dest_path = os.path.join(clone_dir, folder)
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)

    # 3. Copy files to staging folder
    print("📦 Copying backend, frontend, and scripts source files...")
    shutil.copytree(os.path.join(source_dir, "backend"), os.path.join(clone_dir, "backend"), ignore=STAGING_IGNORE_PATTERNS)
    shutil.copytree(os.path.join(source_dir, "frontend"), os.path.join(clone_dir, "frontend"), ignore=STAGING_IGNORE_PATTERNS)
    shutil.copytree(os.path.join(source_dir, "scripts"), os.path.join(clone_dir, "scripts"), ignore=STAGING_IGNORE_PATTERNS)
    
    for file in ["Dockerfile", "requirements.txt", "README.md", ".gitignore"]:
        src = os.path.join(source_dir, file)
        dst = os.path.join(clone_dir, file)
        if os.path.exists(src):
            shutil.copy2(src, dst)

    # 4. Commit and push
    print("📤 Committing changes and pushing to Hugging Face...")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    run_local_command("git add -A", cwd=clone_dir)
    
    # Check if there is anything to commit
    _, status_out = run_local_command("git status --porcelain", cwd=clone_dir, print_output=False)
    if not status_out.strip():
        print("✅ Staging is already up to date. No new changes to push.")
        return True

    commit_ok, _ = run_local_command(f'git commit -m "Staging Deploy: {timestamp}"', cwd=clone_dir)
    if not commit_ok:
        print("❌ Git commit failed.")
        return False

    push_ok, push_err = run_local_command("git push origin main", cwd=clone_dir)
    if push_ok:
        print("\n🎉 SUCCESS! Staging deployment complete.")
        print(f"🌍 Space URL: {STAGING_REPO_URL}")
        print("🌍 App URL: https://dentix-dentix-staging.hf.space")
        return True
    else:
        print(f"❌ Push failed: {push_err}")
        return False

def deploy_production():
    print("\n==================================================")
    print("🚀 DEPLOYING TO PRODUCTION (DigitalOcean Droplet)")
    print("==================================================")
    
    # 1. Build frontend locally
    print("⚡ Building frontend locally...")
    frontend_dir = os.path.join(os.getcwd(), "frontend")
    # Use ExecutionPolicy Bypass on Windows for npm
    cmd = "powershell -ExecutionPolicy Bypass -Command \"npm run build\"" if os.name == 'nt' else "npm run build"
    build_ok, build_out = run_local_command(cmd, cwd=frontend_dir)
    if not build_ok:
        print("❌ Frontend compilation failed!")
        return False
    print("✅ Frontend build completed successfully.")

    # 2. Copy frontend build to backend static folder
    print("🚚 Transferring frontend build to backend/static...")
    static_dir = os.path.join(os.getcwd(), "backend", "static")
    if os.path.exists(static_dir):
        shutil.rmtree(static_dir)
    shutil.copytree(os.path.join(frontend_dir, "dist"), static_dir)
    print("✅ Local assets sync completed.")

    # 3. Create compressed release tar.gz (excluding heavy/temp files)
    print("📦 Packing release archive...")
    archive_name = "release.tar.gz"
    if os.path.exists(archive_name):
        os.remove(archive_name)

    files_to_pack = [
        ("backend", "backend"),
        ("Dockerfile", "Dockerfile"),
        ("Dockerfile.do", "Dockerfile.do"),
        ("requirements.txt", "requirements.txt"),
        ("docker-compose.yml", "docker-compose.yml"),
        ("Caddyfile", "Caddyfile"),
    ]

    with tarfile.open(archive_name, "w:gz") as tar:
        for local_path, arc_name in files_to_pack:
            if os.path.exists(local_path):
                # Filter function to exclude .pyc, logs, db files inside backend
                def tar_filter(tarinfo):
                    exclude_exts = [".pyc", ".db", ".sqlite", ".sqlite3", ".log"]
                    exclude_names = ["__pycache__", ".pytest_cache", "uploads"]
                    
                    # Check file extension
                    _, ext = os.path.splitext(tarinfo.name)
                    if ext in exclude_exts:
                        return None
                    
                    # Check folder names
                    parts = tarinfo.name.split("/")
                    for name in exclude_names:
                        if name in parts:
                            return None
                    return tarinfo

                tar.add(local_path, arcname=arc_name, filter=tar_filter)

    print(f"✅ Release packed into: {archive_name}")

    # 4. Upload archive to DigitalOcean Droplet
    print("📤 Uploading release archive to Droplet via SCP...")
    scp_cmd = f'scp -i "{PRODUCTION_SSH_KEY}" -o StrictHostKeyChecking=accept-new {archive_name} {PRODUCTION_USER}@{PRODUCTION_IP}:{PRODUCTION_DEST_DIR}/'
    upload_ok, upload_err = run_local_command(scp_cmd, print_output=False)
    
    # Cleanup local archive
    if os.path.exists(archive_name):
        os.remove(archive_name)

    if not upload_ok:
        print(f"❌ Archive upload failed: {upload_err}")
        return False
    print("✅ Release archive successfully uploaded.")

    # 5. Extract and restart services on the Droplet via SSH
    print("🔄 Unpacking release and restarting services on the Droplet...")
    remote_commands = (
        f"cd {PRODUCTION_DEST_DIR} && "
        f"rm -rf backend/alembic/versions && "
        f"tar -xzf {archive_name} && "
        f"rm {archive_name} && "
        f"docker compose up -d --build backend worker domain-worker"
    )
    restart_ok, restart_out = run_remote_ssh(remote_commands)
    if not restart_ok:
        print(f"❌ Droplet services deployment/restart failed: {restart_out}")
        return False

    print("\n🎉 SUCCESS! Production deployment to DigitalOcean Droplet completed successfully!")
    print(f"🌍 Server IP: {PRODUCTION_IP}")
    print("🌍 Domain: https://dentixs.app")
    return True

def main():
    parser = argparse.ArgumentParser(description="Dentix Unified Deployment Manager")
    parser.add_argument("--env", choices=["staging", "production"], help="Deployment environment")
    args = parser.parse_args()

    if args.env:
        if args.env == "staging":
            deploy_staging()
        elif args.env == "production":
            deploy_production()
        sys.exit(0)

    # Interactive Mode
    while True:
        clear_screen()
        print("==================================================")
        print("🏥 DENTIX - Unified Deployment Manager")
        print("==================================================")
        print(f"🔒 SSH Key: {PRODUCTION_SSH_KEY}")
        print(f"📍 Staging target: Hugging Face ({STAGING_REPO_URL})")
        print(f"📍 Production target: DigitalOcean Droplet ({PRODUCTION_IP})")
        print("--------------------------------------------------")
        print("Select target environment to deploy:")
        print("  1. Deploy to STAGING (Hugging Face) 🧪")
        print("  2. Deploy to PRODUCTION (DigitalOcean Droplet) 🚀")
        print("  0. Exit")
        print("==================================================")

        choice = input("\n👉 Enter selection (0-2): ").strip()
        if choice == "0":
            print("Deployment exited. Bye!")
            break
        elif choice == "1":
            deploy_staging()
            input("\nPress Enter to continue...")
        elif choice == "2":
            deploy_production()
            input("\nPress Enter to continue...")
        else:
            time.sleep(0.5)

if __name__ == "__main__":
    main()
