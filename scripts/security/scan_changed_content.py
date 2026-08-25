#!/usr/bin/env python3
"""
DENTIX Safe Changed Content Scanner
Scans files or git diffs for potential secrets, unredacted credentials, and prohibited PHI patterns.
Guarantees that matched sensitive values are NEVER printed to stdout or stored in evidence logs.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

RULES = [
    {
        "id": "SEC001_PRIVATE_KEY",
        "desc": "Unencrypted private key",
        "pattern": re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    },
    {
        "id": "SEC002_JWT_TOKEN",
        "desc": "Raw JWT access/refresh token",
        "pattern": re.compile(r"\beyJ[A-Za-z0-9-_=]+\.eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_.+/=]+\b"),
    },
    {
        "id": "SEC003_PASSWORD_IN_URL",
        "desc": "Plaintext password embedded in URL",
        "pattern": re.compile(r"://[^:\s]+:[^@\s/]+@[^@\s]+"),
    },
    {
        "id": "SEC004_SUPABASE_SERVICE_KEY",
        "desc": "Supabase service role key",
        "pattern": re.compile(r"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\.[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+"),
    },
    {
        "id": "PHI001_EGYPTIAN_NATIONAL_ID",
        "desc": "Likely raw 14-digit Egyptian National ID",
        "pattern": re.compile(r"\b[23]\d{13}\b"),
    },
    {
        "id": "PHI002_PHONE_RAW_11DIGIT",
        "desc": "Likely unredacted Egyptian mobile number",
        "pattern": re.compile(r"\b(010|011|012|015)\d{8}\b"),
    },
]

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    ".idea",
    ".vscode",
    "__pycache__",
    "htmlcov",
    ".codex-tmp-dart-3.13.1",
}

EXCLUDED_FILES = {
    "scan_changed_content.py",
    "test_scan_changed_content.py",
    "package-lock.json",
    "uv.lock",
}


def scan_text(content: str, filename: str = "buffer") -> List[Dict[str, str]]:
    """Scan text content line by line and return list of violations with REDACTED matched text."""
    findings = []
    lines = content.splitlines()
    for line_idx, line in enumerate(lines, start=1):
        for rule in RULES:
            if rule["pattern"].search(line):
                # Never include matched line content or secret values
                findings.append({
                    "file": filename,
                    "line": str(line_idx),
                    "rule_id": rule["id"],
                    "rule_desc": rule["desc"],
                })
    return findings


def scan_file(file_path: Path) -> List[Dict[str, str]]:
    """Scan a single file safely."""
    if file_path.name in EXCLUDED_FILES:
        return []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        return scan_text(content, str(file_path))
    except Exception:
        return []


def scan_directory(root_dir: Path) -> List[Dict[str, str]]:
    """Recursively scan a directory, ignoring standard build/virtualenv dirs."""
    all_findings = []
    for path in root_dir.rglob("*"):
        if path.is_file():
            # Check exclusions
            parts = set(path.parts)
            if parts.intersection(EXCLUDED_DIRS):
                continue
            findings = scan_file(path)
            all_findings.extend(findings)
    return all_findings


def main() -> int:
    target_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    if target_path.is_file():
        findings = scan_file(target_path)
    else:
        findings = scan_directory(target_path)

    if not findings:
        print("[OK] Safe scan passed. No secrets or prohibited PHI patterns detected.")
        return 0

    print(f"[VIOLATION] Found {len(findings)} potential security/privacy violations:")
    for f in findings:
        # Strict requirement: Print only path, line number, and rule ID
        print(f"  - {f['file']}:{f['line']} [{f['rule_id']}] {f['rule_desc']}")
    print("\nNote: Matched content is redacted in output to prevent secret/PHI leakage.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
