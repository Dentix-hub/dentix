import json

file_path = r'd:\DENTIX\frontend\src\locales\ar\translation.json'

# Read raw content
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Strategy: remove the broken command_palette block, parse clean JSON, then re-add properly
# Find where the broken injection starts
# The script removed the last two "}" and inserted content between them
# We need to: remove everything from line containing "command_palette" to end, 
# close the parent objects properly, then add command_palette as a sibling

lines = content.splitlines()

# Find the line where command_palette starts
cp_start = None
for i, line in enumerate(lines):
    if '"command_palette"' in line:
        cp_start = i
        break

if cp_start is None:
    print("ERROR: command_palette block not found")
    exit(1)

print(f"Found command_palette at line {cp_start + 1}")

# We need to check what's above cp_start — the previous line should close the 
# medications.table block, but we need the parent medications block to close too
# Look at line cp_start-1
print(f"Line before cp_start: '{lines[cp_start - 1].strip()}'")

# Build clean version: take everything before cp_start
# Line cp_start-1 is "},", which closes "table" inside "medications"
# But we need to also close "medications" itself with "}"
# Then close the root object with "}"
# So the structure should be:
#   ...
#         }             <- closes table
#     },                <- closes medications (need comma since command_palette follows)
#     "command_palette": { ... }
# }                     <- closes root

# Take lines up to and including the line before cp_start
clean_lines = lines[:cp_start]

# The last clean line should be "}," or "}" closing the "table" object
# We need to add "}" to close the parent "medications" object
# But first check: does the line before already close medications?
# Line cp_start-1 is: "},"  (closing table with trailing comma — WRONG, should be no comma)
# Actually looking at the data: line 1520 is "}," which should just be "}" since table is last child

# Let's just strip trailing content and rebuild properly
# Remove trailing whitespace/commas from last clean line
last_line = clean_lines[-1].rstrip()
if last_line.endswith(','):
    clean_lines[-1] = last_line[:-1]  # remove trailing comma from "table" closing

# Close medications
clean_lines.append('    },')

# Add command_palette properly
command_palette = {
    "placeholder": "ابحث عن أي شيء...",
    "results_label": "نتائج البحث",
    "no_results": "لم يتم العثور على نتائج",
    "no_results_desc": "لم نتمكن من العثور على نتائج لـ \\\"{{query}}\\\"",
    "quick_nav": "انتقال سريع",
    "add_patient": "إضافة مريض",
    "new_appointment": "موعد جديد",
    "inventory_check": "فحص المخزون",
    "settings": "الإعدادات",
    "to_close": "للإغلاق",
    "to_select": "للاختيار",
    "go_to": "انتقال إلى",
    "sections": {
        "patients": "المرضى",
        "appointments": "المواعيد",
        "pages": "الصفحات",
        "actions": "الإجراءات"
    }
}

# Serialize command_palette with proper indentation
cp_json = json.dumps(command_palette, ensure_ascii=False, indent=4)
# Indent each line by 4 spaces to match file structure
cp_lines = cp_json.splitlines()
clean_lines.append('    "command_palette": ' + cp_lines[0])
for cp_line in cp_lines[1:]:
    clean_lines.append('    ' + cp_line)

# Close root object
clean_lines.append('}')

# Write back
final_content = '\n'.join(clean_lines) + '\n'

# Validate before writing
try:
    json.loads(final_content)
    print("Validation PASSED — writing file")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(final_content)
    print("Done!")
except json.JSONDecodeError as e:
    print(f"Validation FAILED: {e}")
    print("NOT writing file. Debug output:")
    # Print last 10 lines for debugging
    for i, line in enumerate(clean_lines[-10:]):
        print(f"  {len(clean_lines) - 10 + i + 1}: {line}")
