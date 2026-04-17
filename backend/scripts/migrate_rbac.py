import os
import re

ROUTERS_DIR = r"e:\DENTIX\backend\routers"

FILES_TO_MIGRATE = {
    "system_admin.py": "Permission.SYSTEM_CONFIG",
    "price_lists.py": "Permission.SYSTEM_CONFIG", # Assume system config for updating prices
    "patients_async.py": "Permission.PATIENT_READ", # General operations, can be more granular later
    "notifications.py": "Permission.PATIENT_READ", # Everyone needs notifications... actually, let's just make it Permission.PATIENT_READ or AI_CHAT. Assistant has AI_CHAT. No wait, notifications often aren't permissioned. But let's use Permission.CLINICAL_READ
    "users.py": "Permission.SYSTEM_CONFIG",
    "treatments.py": "Permission.CLINICAL_WRITE",
    "insurance.py": "Permission.FINANCIAL_READ",
    "metrics.py": "Permission.FINANCIAL_READ",
    "prescriptions.py": "Permission.CLINICAL_WRITE",
    "analytics_ai_v2.py": "Permission.AI_CHAT",
}

for filename, default_perm in FILES_TO_MIGRATE.items():
    filepath = os.path.join(ROUTERS_DIR, filename)
    if not os.path.exists(filepath):
        print(f"Skipping {filename}, not found.")
        continue
        
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Skip if already fully migrated
    if "Depends(get_current_user)" not in content:
        print(f"Skipping {filename}, already migrated.")
        continue

    # Add imports if missing
    import_stmt = "from backend.core.permissions import Permission, require_permission"
    if "require_permission" not in content and "Permission" not in content:
        # insert after first block of imports
        content = re.sub(
            r"(from fastapi import.*?\n)", 
            f"\\1{import_stmt}\n", 
            content, 
            count=1,
            flags=re.DOTALL
        )
    elif "require_permission" not in content:
        content = content.replace("from backend.core.permissions import", import_stmt) # fallback

    # Replace legacy token usage
    new_content = re.sub(r"Depends\(get_current_user\)", f"Depends(require_permission({default_perm}))", content)

    # Removed the dangerous regex that deletes role checks.

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    print(f"Migrated {filename} with default {default_perm}")

print("Migration script executed.")
