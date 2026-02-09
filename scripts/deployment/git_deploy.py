import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
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
        # print(result.stdout)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e.stderr}")
        return False, e.stderr

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    while True:
        clear_screen()
        print("🤖 Smart Clinic - Git Deployment Manager")
        print("========================================")
        print("Use this when HF API (Standard/Clean Deploy) is failing.")
        print("\nSelect Target Environment:")
        print("  1. Deploy to Staging 🚀")
        print("  2. Deploy to Production 🚀")
        print("  0. Exit")
        
        choice = input("\n👉 Choose (1-2): ").strip()
        
        if choice == '0':
            print("Bye! 👋")
            break
            
        if choice in REPOS:
            target = REPOS[choice]
            deploy(target)
            input("\nPress Enter to return to menu...")
        else:
            time.sleep(0.5)

def deploy(target):
    repo_url = target['url']
    clone_dir = target['dir']
    source_dir = os.getcwd()
    
    print(f"\n🚀 Starting Git Deployment to [{target['name']}]...")
    print(f"Repo: {repo_url}")
    
    # 1. Clone or Update
    if os.path.exists(clone_dir):
        print("\n📥 Updating existing clone...")
        # Reset any local changes in clone just in case
        run_command("git reset --hard HEAD", cwd=clone_dir)
        run_command("git pull --rebase", cwd=clone_dir)
    else:
        print("\n📥 Cloning repository...")
        run_command(f"git clone {repo_url} {clone_dir}")
        
    if not os.path.exists(clone_dir):
        print("❌ Clone failed. Check internet/credentials.")
        return

    # 2. Clean Destination (Backend/Frontend)
    print("\n🧹 Cleaning destination...")
    for folder in ["backend", "frontend"]:
        dest_path = os.path.join(clone_dir, folder)
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)
            
    # 3. Copy Files
    print("\n📂 Copying files...")
    
    # Helper to copy with ignore
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
        print("⚠️  No changes to deploy (already up to date).")
        return

    commit_ok, _ = run_command(f'git commit -m "Deploy: {timestamp}"', cwd=clone_dir)
    
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
