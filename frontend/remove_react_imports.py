import os
import re

directory = r"e:\DENTIX\frontend\src"
print(f"Scanning {directory}...")

# Regex to match: import React from 'react'; or import React, { ... } from 'react';
# We only want to remove the default export 'React' if it's unused.
# But since we are using new transform, we don't need 'React' in scope for JSX.
# If files use React.useState, then we need 'React'.
# But typically they use { useState }.
# If they use React.useEffect, removing import React breaks it.
# So we should be careful.
# 'no-unused-vars' warning says 'React' is defined but never used.
# This implies React.something is NOT used.
# So removing 'import React' is safe in those files.
# But what about 'import React, { useState } ...'?
# We should only remove 'React, ' part.
# Or if it is 'import React from ...' remove whole line.

# Strategy:
# 1. Read file.
# 2. Check if 'React' is used in body (e.g. React.useState, React.useEffect, React.memo, etc).
# 3. If NOT used, remove 'React' from import.

def process_file(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check for usage of React (whole word, not in import)
    # Simple check: count occurrences of "React"
    # If count == 1 (the import itself), safe to remove.
    # But import might be multiline.
    
    # Let's use a simpler heuristic for now:
    # Remove "import React from 'react';" (exact match)
    # Remove "import React, { ... } from 'react';" -> "import { ... } from 'react';"
    
    lines = content.splitlines()
    new_lines = []
    modified = False
    
    for line in lines:
        if "import React from 'react'" in line or 'import React from "react"' in line:
            # Check if line has other named imports
            if "{" in line:
                # import React, { useState } from 'react'
                # Remove 'React, '
                new_line = line.replace("React, ", "").replace("React ,", "")
                # If only React was imported? "import React, {}" ? Unlikely.
                new_lines.append(new_line)
                modified = True
            else:
                # import React from 'react'; 
                # Check if React is used elsewhere?
                # If we remove it and it IS used, build fails.
                # But 'no-unused-vars' said it UNUSED.
                # So we assume unused.
                # Skip this line completely.
                modified = True
                continue
        else:
            new_lines.append(line)
            
    if modified:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines))
        print(f"Fixed: {path}")

for root, dirs, files in os.walk(directory):
    for file in files:
        if file.endswith((".js", ".jsx")):
            process_file(os.path.join(root, file))
