import json
import os
import re

def fix_lint(report_path):
    with open(report_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for file_data in data:
        file_path = file_data['filePath']
        messages = file_data['messages']
        
        # Sort messages by line/column in reverse order to avoid shifting indices
        # But we are doing text manipulation, so line-based is easier if we process line by line?
        # Or we can read the file, splitting into lines, and then apply changes.
        
        if not messages:
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # We need to track changes to lines.
        # Let's map line_index -> new_content (or None if deleted)
        
        modified = False
        
        # Filter for no-unused-vars
        unused_vars = [m for m in messages if m['ruleId'] == 'no-unused-vars']
        
        # Group by line
        vars_by_line = {}
        for m in unused_vars:
            line_idx = m['line'] - 1 # 0-indexed
            if line_idx not in vars_by_line:
                vars_by_line[line_idx] = []
            
            # Extract variable name from message
            # Message format: "'VarName' is defined but never used"
            # or "'VarName' is assigned a value but never used"
            match = re.search(r"'([^']+)' is", m['message'])
            if match:
                vars_by_line[line_idx].append(match.group(1))
        
        for line_idx, vars_on_line in vars_by_line.items():
            if line_idx >= len(lines): continue
            
            line = lines[line_idx]
            
            # Strategy:
            # 1. Check if it is an import line
            if line.strip().startswith('import '):
                # Handle default import: import X from '...'
                # Handle path import: import { X, Y } from '...'
                # Handle mixed: import X, { Y } from '...'
                
                original_line = line
                
                for var in vars_on_line:
                    # Case 1: Import default "import Var from"
                    # We need to be careful not to match "Var" inside "Variable"
                    # Regex word boundary
                    
                    # If regex matches "import\s+Var\s+from", then remove the whole line?
                    # But what if import Var, { Other } from ...?
                    
                    # Remove from brace structure { Var, Other } -> { Other }
                    # Remove from defaults Var, { ... } -> { ... }
                    
                    # Pattern 1: ", Var," -> "," (middle of list)
                    line = re.sub(r',\s*\b' + re.escape(var) + r'\b\s*,', ',', line)
                    
                    # Pattern 2: "{ Var," -> "{" (start of list)
                    line = re.sub(r'\{\s*\b' + re.escape(var) + r'\b\s*,', '{', line)
                    
                    # Pattern 3: ", Var }" -> "}" (end of list)
                    line = re.sub(r',\s*\b' + re.escape(var) + r'\b\s*\}', ' }', line)
                    
                    # Pattern 4: "{ Var }" -> "{}" (only item in list)
                    line = re.sub(r'\{\s*\b' + re.escape(var) + r'\b\s*\}', '{}', line)
                    
                    # Pattern 5: "import Var from" (default import alone)
                    # "import Var," (default with named)
                    if re.search(r'import\s+\b' + re.escape(var) + r'\b\s+from', line):
                         # It is the only thing? 
                         # If checking "import Var from '...'", then remove line.
                         # But we can just replace Var with nothing and clean up later.
                         pass

                    # Re-construct:
                    # It's hard to robustly regex replace everything.
                    # Simple heuristic:
                    
                    # If var is in braces:
                    # Remove it.
                    
                    # If var is default:
                    # Remove it.
                    
                    # Use a specialized remover for imports.
                    pass
                
                # If we have "{}" left, or "import from ...", or empty?
                # Let's perform a simpler removal:
                
                current_line = original_line
                for var in vars_on_line:
                    # Try to remove "Var, "
                    current_line = re.sub(r'\b' + re.escape(var) + r'\b\s*,\s*', '', current_line)
                    # Try to remove ", Var"
                    current_line = re.sub(r',\s*\b' + re.escape(var) + r'\b', '', current_line)
                    # Try to remove "Var" (last one or only one)
                    current_line = re.sub(r'\b' + re.escape(var) + r'\b', '', current_line)
                
                # Cleanup empty braces or empty imports
                if re.search(r'import\s*\{\s*\}\s*from', current_line):
                    current_line = "" # Delete line
                elif re.search(r'import\s+from', current_line):
                     current_line = "" # Delete line (broken import)
                elif re.search(r'import\s*[\'"][^\'"]+[\'"]\s*;?\s*$', current_line):
                    # import 'css'; -> Keep
                    pass
                elif re.match(r'^\s*import\s*;?\s*$', current_line):
                    current_line = "" # Empty
                elif re.match(r'^\s*$', current_line):
                    current_line = "" # Empty
                
                lines[line_idx] = current_line
                modified = True
            
            else:
                # Not an import line (variable assignment, destructuring, etc.)
                # "const { Var } = props;" -> "const {} = props;"
                # "const Var = 1;" -> "const Var = 1;" (If we remove it, we break code?)
                # Actually if "const Var = 1", removing it breaks syntax "const = 1"?
                # Safe to remove WHOLE line if definition?
                
                # Only safe to remove if it is "const Var = ..." or "let Var ..."
                # If "const { A, Var } = ...", remove Var from destructuring.
                pass
        
        if modified:
             # Filter out empty lines that were deleted (set to "")
             new_lines = [l for l in lines if l.strip() != ""]
             with open(file_path, 'w', encoding='utf-8') as f:
                 f.writelines(new_lines)
             print(f"Fixed: {file_path}")

fix_lint('lint_report.json')
