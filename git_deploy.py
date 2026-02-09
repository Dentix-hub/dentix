import os
import sys
import time
import shutil
import subprocess

# Configuration
REPOS = {
    "1": {"name": "Staging", "url": "https://huggingface.co/spaces/SmartClinic/smart-clinic-staging", "dir": ".hf-deploy-staging"},
    "2": {"name": "Production", "url": "https://huggingface.co/spaces/SmartClinic/smart-clinic-v2", "dir": ".hf-deploy-production"},
}

IGNORE_PATTERNS = shutil.ignore_patterns(
    "__pycache__", "*.pyc", "venv", ".venv", ".env", "*.db", "*.sqlite", "uploads", "*.log", ".git", ".pytest_cache",
    "node_modules", "dist", ".vite", "coverage", "test-results"
)

def run_command(command, cwd=None):
    """Run shell command and print output."""
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
        print(f"❌ Error: {e.stderr}")
        return False, e.stderr

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def safe_rmtree(path):
    """Safely remove directory with retry for Windows file locking issues."""
    max_retries = 3
    for i in range(max_retries):
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
            return True
        except PermissionError as e:
            if i < max_retries - 1:
                print(f"⚠️  Retry {i+1}/{max_retries} - Files locked, waiting...")
                time.sleep(2)
            else:
                print(f"❌ Cannot delete {path}: {e}")
                return False
        except Exception as e:
            print(f"❌ Error deleting {path}: {e}")
            return False
    return True

def main():
    while True:
        clear_screen()
        print("🤖 DENTIX - Git Deployment Manager")
        print("===================================")
        print("Use this when HF API is failing.\n")
        print("Select Target Environment:")
        print("  1. Deploy to Staging 🚀")
        print("  2. Deploy to Production 🚀")
        print("  3. Clean Deploy to Staging 🧹 (Force)")
        print("  4. Clean Deploy to Production 🧹 (Force)")
        print("  0. Exit")
        
        choice = input("\n👉 Choose (0-4): ").strip()
        
        if choice == '0':
            print("Bye! 👋")
            break
        
        try:
            if choice == '1':
                deploy(REPOS["1"], force=False)
            elif choice == '2':
                deploy(REPOS["2"], force=False)
            elif choice == '3':
                deploy(REPOS["1"], force=True)
            elif choice == '4':
                deploy(REPOS["2"], force=True)
            else:
                print("❌ Invalid choice!")
                time.sleep(1)
                continue
        except Exception as e:
            print(f"\n❌ Unexpected Error: {e}")
            import traceback
            traceback.print_exc()
            
        input("\nPress Enter to return to menu...")

def deploy(target, force=False):
    repo_url = target['url']
    clone_dir = target['dir']
    source_dir = os.getcwd()
    
    mode = "🧹 CLEAN/FORCE" if force else "📦 Normal"
    print(f"\n🚀 Starting {mode} Deployment to [{target['name']}]...")
    print(f"Repo: {repo_url}")
    
    # For Clean Deploy: Delete the entire clone directory first
    if force and os.path.exists(clone_dir):
        print("\n🗑️  Removing old clone for clean deploy...")
        if not safe_rmtree(clone_dir):
            print("⚠️  Continuing with existing directory...")
    
    # 1. Clone or Update
    if os.path.exists(clone_dir):
        print("\n📥 Updating existing clone...")
        run_command("git reset --hard HEAD", cwd=clone_dir)
        run_command("git pull --rebase", cwd=clone_dir)
    else:
        print("\n📥 Cloning repository...")
        success, output = run_command(f"git clone {repo_url} {clone_dir}")
        if not success:
            print("❌ Clone failed. Check internet/credentials.")
            return
        
    if not os.path.exists(clone_dir):
        print("❌ Clone failed. Check internet/credentials.")
        return

    # 2. Clean Destination (Backend/Frontend)
    print("\n🧹 Cleaning destination...")
    for folder in ["backend", "frontend"]:
        dest_path = os.path.join(clone_dir, folder)
        if os.path.exists(dest_path):
            safe_rmtree(dest_path)
            
    # 3. Copy Files
    print("\n📂 Copying files...")
    
    def copy_tree(src, dst):
        shutil.copytree(src, dst, ignore=IGNORE_PATTERNS)

    # Backend
    print("   -> Copying backend...")
    copy_tree(os.path.join(source_dir, "backend"), os.path.join(clone_dir, "backend"))
    
    # Frontend
    print("   -> Copying frontend...")
    copy_tree(os.path.join(source_dir, "frontend"), os.path.join(clone_dir, "frontend"))
    
    # Root Files
    print("   -> Copying root files...")
    for file in ["Dockerfile", "requirements.txt", "README.md"]:
        src = os.path.join(source_dir, file)
        dst = os.path.join(clone_dir, file)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            
    # 4. Commit and Push
    print("\n📤 Committing changes...")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    run_command("git add -A", cwd=clone_dir)
    
    # Check if anything to commit
    status_ok, status_out = run_command("git status --porcelain", cwd=clone_dir)
    
    if not status_out.strip():
        if force:
            # Force mode: create empty commit to trigger rebuild
            print("⚡ Force mode: Creating empty commit to trigger rebuild...")
            commit_ok, _ = run_command(f'git commit --allow-empty -m "Force Deploy: {timestamp}"', cwd=clone_dir)
        else:
            print("⚠️  No changes to deploy (already up to date).")
            print("💡 Tip: Use Clean Deploy (options 3 or 4) to force redeploy.")
            return
    else:
        commit_msg = f"Force Deploy: {timestamp}" if force else f"Deploy: {timestamp}"
        commit_ok, _ = run_command(f'git commit -m "{commit_msg}"', cwd=clone_dir)
    
    if commit_ok:
        print("⬆️  Pushing to Hugging Face...")
        push_ok, push_err = run_command("git push origin main", cwd=clone_dir)
        
        if push_ok:
            print("\n✅ SUCCESS! Deployment complete.")
            print(f"🔗 Monitor: {repo_url}")
        else:
            print("\n❌ Push failed.")
            print("Tip: If it's credential error, run 'git credential-manager configure' or Check HF Token.")
    else:
         print("❌ Commit failed.")

if __name__ == "__main__":
    main()
