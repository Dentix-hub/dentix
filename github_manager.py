
import os
import time
import subprocess
import sys

# Configuration
BRANCHES = {
    "1": "staging",
    "2": "main"
}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def run_command(cmd, desc):
    print(f"  ⏳ {desc}...", end=" ", flush=True)
    try:
        # Run command and capture output
        result = subprocess.run(cmd, shell=True, check=True, text=True, capture_output=True)
        print("✅")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print("❌")
        print(f"\n[ERROR] Command failed: {cmd}")
        print(f"Error details:\n{e.stderr}")
        return False, e.stderr

def git_deploy(branch):
    print(f"\n🐙 Starting GitHub Push to branch [{branch}]...")
    print("==================================================")
    
    # 1. Commit Message
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    default_msg = f"Auto-Update {timestamp}"
    
    custom_msg = input(f"📝 Commit Message (Press Enter for '{default_msg}'): ").strip()
    commit_msg = custom_msg if custom_msg else default_msg
    
    # 2. Add Files
    success, _ = run_command("git add .", "Staging all files")
    if not success: return

    # 3. Check Status (Avoid empty commits)
    status_proc = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    if not status_proc.stdout.strip():
        # Check if we are ahead
        pass
        # Actually if status is clean, commit will fail.
        # But we might have unpushed commits.
    
    # 4. Commit
    # We use || true in bash, or check status first. 
    # Attempt commit, if empty it's fine.
    print(f"  💾 Committing: '{commit_msg}'...", end=" ", flush=True)
    try:
        subprocess.run(f'git commit -m "{commit_msg}"', shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        print("✅")
    except subprocess.CalledProcessError:
        print("ℹ️ (Nothing to commit)")

    # 5. Pull (Rebase structure usually better, but simple pull is safer for beginners)
    success, _ = run_command(f"git pull origin {branch}", "Pulling latest changes")
    if not success: 
       if input("  ⚠️  Pull failed. Continue Push? (y/n): ").lower() != 'y': return

    # 6. Push
    # Push HEAD (current branch) to the target remote branch
    success, _ = run_command(f"git push origin HEAD:{branch}", f"Pushing current code to {branch}")
    
    if success:
        print(f"\n🎉 Successfully pushed to GitHub [{branch}]!")
    
    input("\nPress Enter to return...")

def main():
    while True:
        clear_screen()
        print("🐙 Smart Clinic - GitHub Manager")
        print("================================")
        
        print("\nSelect Target Branch:")
        for k, v in BRANCHES.items():
            print(f"  {k}. Push to {v}")
            
        print("\nOptions:")
        print("  0. Exit")
        
        choice = input("\n👉 Choose (1-2): ").strip()
        
        if choice == '0':
            print("Bye! 👋")
            break
            
        if choice in BRANCHES:
            branch = BRANCHES[choice]
            if input(f"❓ Confirm push to '{branch}'? (y/n): ").lower() == 'y':
                git_deploy(branch)
        else:
            time.sleep(0.5)

if __name__ == "__main__":
    main()
