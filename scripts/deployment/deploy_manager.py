import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import os
import time
import shutil
from huggingface_hub import HfApi, login

TOKEN_FILE = ".hf_token_custom"

# Configuration
REPOS = {
    "1": {"name": "Staging", "id": "SmartClinic/smart-clinic-staging"},
    "2": {"name": "Production", "id": "SmartClinic/smart-clinic-v2"},
    # Add more if needed
}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def clean_local_temp():
    """Removes __pycache__ and .pyc files locally."""
    print("\n🧹 Cleaning local temporary files...")
    count = 0
    for root, dirs, files in os.walk(".", topdown=False):
        for name in dirs:
            if name == "__pycache__":
                try:
                    shutil.rmtree(os.path.join(root, name))
                    count += 1
                except: pass
    print(f"   ✅ Removed {count} '__pycache__' directories.")

def load_token():
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                return f.read().strip()
        except:
            return None
    return None

def save_token(token):
    with open(TOKEN_FILE, "w") as f:
        f.write(token.strip())
    print("✅ Token saved successfully!")

def get_api_client():
    token = load_token()
    if not token:
        print("🔑 No token found.")
        token = input("👉 Paste your Hugging Face Token (Write): ").strip()
        if token:
            save_token(token)
        else:
            return None, None
            
    try:
        login(token=token, add_to_git_credential=False)
        api = HfApi(token=token)
        user = api.whoami()
        return api, user
    except Exception as e:
        print(f"❌ Login Error: {e}")
        # Maybe token expired?
        if input("🔄 Reset token? (y/n): ").lower() == 'y':
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
            return get_api_client() # Retry
        return None, None

def deploy(api, repo_id, env_name, clean_remote=False):
    print(f"\n🚀 Starting Deployment to [{env_name}] ({repo_id})...")
    if clean_remote:
        print("🧹 MODE: CLEAN DEPLOY (Wiping remote folders first)")
    print("==================================================")
    
    # Automatic Commit Message
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    custom_msg = f"Auto-Deploy {timestamp}"
    if clean_remote:
        custom_msg += " [Clean]"
    print(f"📝 Commit Message: {custom_msg}")
    
    # Clean Local first
    clean_local_temp()

    # Clean Remote if requested
    if clean_remote:
        print("  🔥 Wiping remote 'backend' & 'frontend'...", end=" ", flush=True)
        try:
            api.delete_folder(path_in_repo="backend", repo_id=repo_id, repo_type="space", commit_message=f"Clean Backend {timestamp}")
            api.delete_folder(path_in_repo="frontend", repo_id=repo_id, repo_type="space", commit_message=f"Clean Frontend {timestamp}")
            print("✅")
        except Exception as e:
            print(f"⚠️  (Might not exist): {e}")

    # Critical Files
    root_files = ["README.md", "Dockerfile", "requirements.txt"]
    hooks_file = "frontend/src/hooks/useVoiceInput.js"
    
    success_count = 0
    fail_count = 0
    
    # 1. Root Files
    for file in root_files:
        if not os.path.exists(file):
            print(f"⚠️  Missing: {file}")
            continue
        print(f"  ⬆️ Uploading {file}...", end=" ", flush=True)
        try:
            api.upload_file(
                path_or_fileobj=file,
                path_in_repo=file,
                repo_id=repo_id,
                repo_type="space",
                commit_message=f"{custom_msg}: {file}"
            )
            print("✅")
            success_count += 1
        except Exception as e:
            print(f"❌ {e}")
            fail_count += 1

    # 2. Backend (Full Sync)
    print("  ⬆️ Syncing 'backend' folder...", end=" ", flush=True)
    try:
        api.upload_folder(
            folder_path="backend",
            path_in_repo="backend",
            repo_id=repo_id,
            repo_type="space",
            commit_message=f"{custom_msg}: Backend Sync",
            ignore_patterns=[
                "__pycache__", "*.pyc", ".DS_Store",
                "uploads/*", "static/*", "*.db", "*.sqlite", "*.log",
                ".venv", "venv", ".env", ".git", ".pytest_cache"
            ]
        )
        print("✅")
        success_count += 1
    except Exception as e:
        print(f"❌ {e}")
        fail_count += 1

    # 3. Frontend (Full Sync)
    print("  ⬆️ Syncing 'frontend' folder...", end=" ", flush=True)
    try:
        api.upload_folder(
            folder_path="frontend",
            path_in_repo="frontend",
            repo_id=repo_id,
            repo_type="space",
            commit_message=f"{custom_msg}: Frontend Sync",
            ignore_patterns=[
                "node_modules/*", "dist/*", ".git", ".env",
                ".vite", "coverage", ".DS_Store", "*.log", "*.zip"
            ]
        )
        print("✅")
        success_count += 1
    except Exception as e:
        print(f"❌ {e}")
        fail_count += 1
            
    print("\n--------------------------------------------------")
    print(f"📊 Result: {success_count} Success, {fail_count} Failed")
    if success_count > 0:
        print(f"🌍 Live URL: https://huggingface.co/spaces/{repo_id}")
    input("\nPress Enter to return to menu...")

def main():
    while True:
        clear_screen()
        print("🤖 Smart Clinic - Deployment Manager")
        print("====================================")
        
        # Check login status subtly
        token = load_token()
        if token:
            print("✅ Token: Loaded (Saved)")
        else:
            print("⚠️  Token: Not configured")
            
        print("\nSelect Target Environment:")
        for k, v in REPOS.items():
            print(f"  {k}. Deploy to {v['name']} 🚀")
            
        print("\nOptions:")
        print("  9. Settings (Change Repos/Token)")
        print("  0. Exit")
        
        choice = input("\n👉 Choose (1-2): ").strip()
        
        if choice == '0':
            print("Bye! 👋")
            break
            
        if choice in REPOS:
            api, user = get_api_client()
            if api:
                print(f"👤 Authenticated as: {user['name']}")
                env = REPOS[choice]
                
                # Clean Deploy Option
                clean_opt = False
                print(f"\n❓  Deploy Mode:")
                print("   1. Standard Deploy (Fast) ⚡")
                print("   2. Clean Deploy (Wipe Remote + Local Clean) 🧹")
                if input("   👉 Choice (1/2): ").strip() == '2':
                    clean_opt = True
                
                if input(f"\n❓ Confirm deploy to {env['name']}? (y/n): ").lower() == 'y':
                    deploy(api, env['id'], env['name'], clean_remote=clean_opt)
        
        elif choice == '9':
            print("\nSettings:")
            if input("  Trash saved token? (y/n): ").lower() == 'y':
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                    print("  Deleted.")
            input("Press Enter...")
        else:
            time.sleep(0.5)

if __name__ == "__main__":
    main()
