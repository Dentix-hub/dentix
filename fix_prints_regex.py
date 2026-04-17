import os
import re

BACKEND_DIR = r"d:\DENTIX\backend"
IGNORE_DIRS = ["tests", "scripts", "__pycache__"]

def fix_prints(content):
    # This will match print( ... ) even across newlines if we use dotall, 
    # but balancing parentheses with regex is tricky.
    # We will just replace "print(" with "logger.info(" and hope the parentheses balance.
    # Since print(...) is syntactically identical to logger.info(...)
    # Note: we need to ensure we only replace the keyword print when it's a function call.
    
    # We find word boundaries: \bprint(
    new_content = re.sub(r'\bprint\(', 'logger.info(', content)
    return new_content

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    content = fix_prints(content)

    if content != original:
        has_logging = "import logging" in content
        has_logger = "logger = logging.getLogger" in content
        lines = content.split('\n')
        
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                insert_idx = i
                break
                
        if not has_logging:
            lines.insert(insert_idx, "import logging")
        if not has_logger:
            lines.insert(insert_idx + (0 if has_logging else 1), "logger = logging.getLogger(__name__)")
            
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        return True
    return False

if __name__ == "__main__":
    fixed = 0
    for root, dirs, files in os.walk(BACKEND_DIR):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                if process_file(path):
                    fixed += 1
    print(f"Fixed {fixed} files with regex.")
