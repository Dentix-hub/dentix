import os
import re

api_dir = r"d:\DENTIX\frontend\src\api"
exports = {}

for filename in os.listdir(api_dir):
    if filename.endswith(".js") and filename != "index.js" and filename != "apiClient.js":
        with open(os.path.join(api_dir, filename), "r", encoding="utf-8") as f:
            content = f.read()
            # Match export const name = ... or export function name(...)
            matches = re.findall(r"export const (\w+)|export function (\w+)", content)
            for m in matches:
                name = m[0] or m[1]
                if name in exports:
                    exports[name].append(filename)
                else:
                    exports[name] = [filename]

duplicates = {name: files for name, files in exports.items() if len(files) > 1}
if duplicates:
    print("Duplicate exports found:")
    for name, files in duplicates.items():
        print(f"  {name}: {', '.join(files)}")
else:
    print("No duplicate exports found.")
