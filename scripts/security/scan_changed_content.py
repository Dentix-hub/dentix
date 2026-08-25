#!/usr/bin/env python3
"""
DENTIX Safe Changed Content Scanner
Scans files or git diffs for potential secrets, unredacted credentials, and prohibited PHI patterns.
Guarantees that matched sensitive values are NEVER printed to stdout or stored in evidence logs.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

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

TEST_FIXTURE_DIRS = {"tests", "ci_tests"}
ALLOW_PATTERN_MARKER = "scan: allow-pattern-definition"


def scan_text(content: str, filename: str = "buffer") -> List[Dict[str, str]]:
    """Scan text content line by line and return list of violations with REDACTED matched text."""
    findings = []
    lines = content.splitlines()
    for line_idx, line in enumerate(lines, start=1):
        if ALLOW_PATTERN_MARKER in line:
            continue
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


def _is_excluded(relative_path: str) -> bool:
    path = Path(relative_path)
    return path.name in EXCLUDED_FILES or bool(set(path.parts).intersection(EXCLUDED_DIRS))


def _is_test_fixture(relative_path: str) -> bool:
    return bool(set(Path(relative_path).parts).intersection(TEST_FIXTURE_DIRS))


def scan_git_diff(diff_text: str, *, exclude_test_fixtures: bool = False) -> List[Dict[str, str]]:
    """Scan only added lines in a zero-context unified git diff."""
    findings: List[Dict[str, str]] = []
    current_file: str | None = None
    added_line = 0

    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            candidate = line[4:]
            current_file = None if candidate == "/dev/null" else candidate.removeprefix("b/")
            continue
        if line.startswith("@@ "):
            match = re.search(r"\+(\d+)(?:,\d+)?", line)
            added_line = int(match.group(1)) - 1 if match else 0
            continue
        if (
            current_file is None
            or _is_excluded(current_file)
            or (exclude_test_fixtures and _is_test_fixture(current_file))
        ):
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added_line += 1
            content = line[1:]
            if ALLOW_PATTERN_MARKER in content:
                continue
            for rule in RULES:
                if rule["pattern"].search(content):
                    findings.append({
                        "file": current_file,
                        "line": str(added_line),
                        "rule_id": rule["id"],
                        "rule_desc": rule["desc"],
                    })
        elif not line.startswith("-") and not line.startswith("\\"):
            added_line += 1

    return findings


def scan_changed_content(
    repo_root: Path,
    base_ref: str,
    *,
    exclude_test_fixtures: bool = False,
) -> List[Dict[str, str]]:
    """Scan committed/uncommitted additions since base_ref plus untracked files."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/@{}^~:+-]*", base_ref):
        raise ValueError("base ref contains unsupported characters")

    diff = subprocess.run(
        ["git", "diff", "--no-ext-diff", "--unified=0", "--no-color", base_ref, "--"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    findings = scan_git_diff(diff.stdout, exclude_test_fixtures=exclude_test_fixtures)

    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    for raw_path in untracked.stdout.split(b"\0"):
        if not raw_path:
            continue
        relative_path = raw_path.decode("utf-8", errors="replace")
        if _is_excluded(relative_path) or (exclude_test_fixtures and _is_test_fixture(relative_path)):
            continue
        content = (repo_root / relative_path).read_text(encoding="utf-8", errors="ignore")
        findings.extend(scan_text(content, relative_path))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan files or added git content without printing matches.")
    parser.add_argument("target", nargs="?", default=".")
    parser.add_argument("--base-ref", help="Scan only content added since this git revision.")
    parser.add_argument(
        "--exclude-test-fixtures",
        action="store_true",
        help="Exclude tests/ci_tests containing synthetic secret and PHI canaries.",
    )
    args = parser.parse_args()

    target_path = Path(args.target).resolve()
    try:
        if args.base_ref:
            findings = scan_changed_content(
                target_path,
                args.base_ref,
                exclude_test_fixtures=args.exclude_test_fixtures,
            )
        elif target_path.is_file():
            findings = scan_file(target_path)
        else:
            findings = scan_directory(target_path)
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"[ERROR] Scanner could not complete: {type(exc).__name__}")
        return 2

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
