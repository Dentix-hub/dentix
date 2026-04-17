import os
import re

import glob

routers = [
    "admin_audit.py", "admin_doctors.py", "admin_features.py", "admin_security.py",
    "admin_stats.py", "admin_subscriptions.py", "admin_system.py", "admin_tenants.py",
    "ai.py", "ai_admin.py", "ai_assist.py",
    "analytics_ai_v2.py",
    "financials.py",
    "health.py",
    "support.py",
    "attachments.py",
    "upload.py",
    "repair.py"
]

ROUTERS_DIR = r"d:\DENTIX\backend\routers"

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Track if we need to add the import
    needs_import = False
    
    # We want to find patterns like: return {"something": value}
    # and replace with: return success_response(data={"something": value})
    
    # A simple regex for top-level returns (be careful with multiline dicts)
    # We can match `return { ... }` that is on a single line or starts/ends simply
    
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        if line.strip().startswith("return {") and line.strip().endswith("}"):
            inner = line[line.find("{"):line.rfind("}")+1]
            # Replace it
            indent = line[:len(line) - len(line.lstrip())]
            new_lines.append(f"{indent}return success_response(data={inner})")
            needs_import = True
        elif line.strip().startswith("return JSONResponse(content={") and line.strip().endswith("})"):
            inner = line[line.find("content={")+8:line.rfind("})")]
            indent = line[:len(line) - len(line.lstrip())]
            new_lines.append(f"{indent}return success_response(data={inner})")
            needs_import = True
        elif line.strip().startswith("return JSONResponse(") and line.strip().endswith(")"):
            # Skip multiline JSONResponse for simple regex, handle them manually if needed
            new_lines.append(line)
        else:
            new_lines.append(line)

    content_new = "\n".join(new_lines)
    
    # Ensure import is present if needed
    if needs_import and "from ..core.response import success_response" not in content_new and "from backend.core.response import success_response" not in content_new:
        # Find where to put the import
        import_stmt = "from ..core.response import success_response, error_response"
        
        # simple placement after the first batch of from/import
        lines_new = content_new.split('\n')
        insert_idx = 0
        for i, l in enumerate(lines_new):
            if l.startswith("from fastapi "):
                insert_idx = i + 1
                break
        lines_new.insert(insert_idx, import_stmt)
        content_new = "\n".join(lines_new)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content_new)
        
    print(f"Processed {os.path.basename(filepath)} - Modified: {needs_import}")

for r in routers:
    fp = os.path.join(ROUTERS_DIR, r)
    if os.path.exists(fp):
        process_file(fp)
    else:
        print(f"File not found: {r}")
