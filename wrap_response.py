import os
import re

FILES = [
    r"d:\DENTIX\backend\routers\insurance.py",
    r"d:\DENTIX\backend\routers\laboratories.py",
    r"d:\DENTIX\backend\routers\procedures.py"
]

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add the import if not there
    if "from backend.core.response import success_response" not in content:
        content = re.sub(
            r'(from fastapi import APIRouter.*?\n)',
            r'\1from backend.core.response import success_response\n',
            content, count=1
        )

    # Remove response_model=... 
    content = re.sub(r',\s*response_model=[^)]*', '', content)

    # Now for each endpoint def, we need to wrap the return statements.
    # A simple regex for top-level returns in functions is dangerous.
    # Instead let's just do it dynamically or using simple string replacement:
    # "return result" -> "return success_response(result)"
    content = re.sub(r'\breturn (result|providers|provider|price_lists|\{.*?\})\b(?!\))', 
                     lambda m: f"return success_response({m.group(1)})", content)
    
    # labs
    content = re.sub(r'\breturn _get_cached_laboratories\(.*?\)', 
                     lambda m: f"return success_response({m.group(0)[7:]})", content)
    content = re.sub(r'\breturn db_lab\b', r'return success_response(db_lab)', content)
    content = re.sub(r'\breturn lab\b', r'return success_response(lab)', content)
    content = re.sub(r'\breturn db_order\b', r'return success_response(db_order)', content)
    content = re.sub(r'\breturn db_procedure\b', r'return success_response(db_procedure)', content)
    content = re.sub(r'\breturn procedure\b', r'return success_response(procedure)', content)
    content = re.sub(r'\breturn db_payment\b', r'return success_response(db_payment)', content)
    content = re.sub(r'\breturn payments\b', r'return success_response(payments)', content)
    content = re.sub(r'return \{"message"', r'return success_response(message', content) # not ideal but okay
    content = re.sub(r'return success_response\(message: (.*?)\}', r'return success_response(message=\1)', content)

    # procedure specific returns
    content = re.sub(r'\breturn procedures\b', r'return success_response(procedures)', content)
    content = re.sub(r'\breturn \{"id": provider\.id, "message": "Updated"\}', 'return success_response({"id": provider.id}, message="Updated")', content)
    content = re.sub(r'\breturn \{"message": "Deactivated".*?\}', 'return success_response(deactivated_lists, message="Deactivated")', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for f in FILES:
    process_file(f)
