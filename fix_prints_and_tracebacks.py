import os
import re

BACKEND_DIR = r"d:\DENTIX\backend"

IGNORE_DIRS = ["tests", "scripts", "__pycache__"]

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    modified = False

    # 1. Add import logging and logger = logging.getLogger(__name__) if not present
    # but only if we end up changing something, or we can just ensure it anyway.
    
    # regex for print(...) -> logger.info(...)
    # We want to match print( something )
    # This is rudimentary, but covers 99% of debugging prints
    if "print(" in content:
        content = re.sub(r'\bprint\((.*?)\)', r'logger.info(\1)', content)
        modified = True

    # 2. Traceback cleanup
    if "import traceback" in content and "traceback.print_exc()" in content:
        content = re.sub(r'^[ \t]*import traceback\s*\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'^[ \t]*traceback\.print_exc\(\)\s*\n', '        logger.exception("An exception occurred", exc_info=True)\n', content, flags=re.MULTILINE)
        modified = True

    if modified:
        # Check if logging is already imported
        if "import logging" not in content:
            # insert after the first import or at the top
            lines = content.split('\n')
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    insert_idx = i
                    break
            
            lines.insert(insert_idx, "import logging")
            lines.insert(insert_idx+1, "logger = logging.getLogger(__name__)")
            content = '\n'.join(lines)
            
        elif "logging.getLogger" not in content:
            # logging imported, but no logger initialized
            content = re.sub(r'(import logging\s*\n)', r'\1logger = logging.getLogger(__name__)\n', content)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    fixed = 0
    for root, dirs, files in os.walk(BACKEND_DIR):
        # Exclude directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                if process_file(path):
                    fixed += 1
    
    print(f"Fixed {fixed} files.")

if __name__ == "__main__":
    main()
