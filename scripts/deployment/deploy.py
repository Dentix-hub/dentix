import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import os
import sys
import time
from huggingface_hub import HfApi, login
from pathlib import Path

# Configuration
REPO_ID = "Dentix/smart-clinic-staging"
    
def get_token():
    token = os.getenv("HF_TOKEN")
    if token:
        print("✅ Found HF_TOKEN in environment variables.")
        return token
    
    token = input("🔑 Paste Hugging Face Token (Write): ").strip()
    return token

def upload_folder(api, local_path, repo_path, ignore_patterns):
    print(f"  ⬆️ Syncing '{local_path}' -> '{repo_path}'...", end=" ", flush=True)
    try:
        api.upload_folder(
            folder_path=local_path,
            path_in_repo=repo_path,
            repo_id=REPO_ID,
            repo_type="space",
            commit_message=f"Deploy: {local_path}",
            ignore_patterns=ignore_patterns
        )
        print("✅ Done")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def main():
    print("🚀 Smart Clinic - Production Deployment Tool")
    print("============================================")
    print(f"Target: {REPO_ID}")
    print("This script uploads ALL code (Frontend + Backend) for Docker build.")
    print()
    
    # 1. Login
    token = get_token()
    if not token:
        print("❌ Token required!")
        return

    try:
        login(token=token, add_to_git_credential=False)
        api = HfApi(token=token)
        user = api.whoami()
        print(f"✅ Logged in as: {user['name']}")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return

    # 2. Confirmation
    confirm = input(f"\n❓ Deploy to {REPO_ID}? (y/n): ").lower()
    if confirm != 'y':
        print("ABORTED.")
        return

    print(f"\n📦 Starting Deployment...")
    
    success_count = 0
    
    # 3. Root Files
    root_files = ["Dockerfile", "requirements.txt", "README.md"]
    for file in root_files:
        if os.path.exists(file):
            print(f"  ⬆️ Uploading {file}...", end=" ", flush=True)
            try:
                api.upload_file(
                    path_or_fileobj=file,
                    path_in_repo=file,
                    repo_id=REPO_ID,
                    repo_type="space",
                    commit_message=f"Config: {file}"
                )
                print("✅ Done")
                success_count += 1
            except Exception as e:
                print(f"❌ Failed: {e}")

    # 4. Backend
    if upload_folder(api, "backend", "backend", ["__pycache__", "*.pyc", ".DS_Store", "venv", ".env"]):
        success_count += 1

    # 5. Frontend (Full Upload for Docker Build)
    # Exclude node_modules (heavy) and dist (rebuilt in Docker)
    if upload_folder(api, "frontend", "frontend", ["node_modules", "dist", ".git", ".vscode", ".env*", "test-results"]):
        success_count += 1

    print("\n============================================")
    if success_count >= 3:
        print(f"🚀 SUCCESS! Build triggered on Hugging Face.")
        print(f"🔗 Monitor Build: https://huggingface.co/spaces/{REPO_ID}")
    else:
        print("⚠️ Completed with some errors.")

if __name__ == "__main__":
    main()
