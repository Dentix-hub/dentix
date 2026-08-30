#!/usr/bin/env python3
"""
DENTIX CI Scope Classifier
Deterministic change classifier for selective PR CI execution.

Inputs:
  - Event type (github.event_name)
  - Target branch / ref
  - Git commit range / diff against base
  - Optional PR labels (CLI or JSON)

Outputs JSON with boolean classification flags.

Safety model:
  1. Protected pushes (staging/main) and workflow_dispatch: always force_full.
  2. HIGH_RISK labels: always force_full.
  3. Closed-list structural surfaces (models/schema lineage, shared API/session,
     core security, migrations, governance) always force full.
  4. Token-aware keyword scanning catches high-risk source paths without unsafe
     substring matches (for example, ``AuthorCard`` is not authentication).
  5. Clinical UI remains STANDARD unless a clinical-semantics token is present.
  6. Unrecognized paths and an empty/unavailable diff force full.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Union


# ---------------------------------------------------------------------------
# Token-aware high-risk scanning. Keywords are matched on normalized path-token
# boundaries, not arbitrary substrings.
# ---------------------------------------------------------------------------
HIGH_RISK_KEYWORDS_AUTH = [
    "auth", "login", "logout", "password", "credential", "jwt", "token",
    "session", "cookie", "oauth", "rbac", "permission", "role",
    "super_admin", "superadmin", "impersonate", "impersonation",
]
HIGH_RISK_KEYWORDS_TENANCY = [
    "tenant", "rls", "idor", "bola", "row_level", "row-level",
    "cross_tenant", "cross-tenant", "child_tenant", "child-tenant",
    "tenant_scope", "tenant-scope", "tenant_context", "tenant-context",
]
HIGH_RISK_KEYWORDS_FINANCE = [
    "finance", "expense", "expenses", "invoice", "invoices", "payment",
    "payments", "billing", "pricing", "commission", "commissions", "ledger",
    "transaction", "transactions", "cost_engine",
]
HIGH_RISK_KEYWORDS_MIGRATION = [
    "alembic", "migration", "migrations",
]
HIGH_RISK_KEYWORDS_SECURITY = [
    "security", "sanitizer", "vulnerability", "vulnerabilities", "bandit",
    "secret_service", "security_service", "security_event",
    "security_header", "security_panel",
]
HIGH_RISK_KEYWORDS_CLINICAL_SEMANTICS = [
    "notation", "fdi", "universal_notation",
    "treatment_plan", "condition_type", "tooth_identity",
    "tooth_types", "procedure_layers",
]
HIGH_RISK_KEYWORDS_CONTAINER = [
    "dockerfile", "docker-compose", "dockerignore",
    "gunicorn", "entrypoint",
]
HIGH_RISK_KEYWORDS_GOVERNANCE = [
    ".github/workflows/", ".github/scripts/",
    ".github/rulesets/",
    "ruff.toml", ".pre-commit-config",
]

# Combine all keyword families for fast iteration
_ALL_KEYWORD_FAMILIES = [
    ("auth",              HIGH_RISK_KEYWORDS_AUTH),
    ("tenancy",           HIGH_RISK_KEYWORDS_TENANCY),
    ("finance",           HIGH_RISK_KEYWORDS_FINANCE),
    ("migration",         HIGH_RISK_KEYWORDS_MIGRATION),
    ("security",          HIGH_RISK_KEYWORDS_SECURITY),
    ("clinical_semantics", HIGH_RISK_KEYWORDS_CLINICAL_SEMANTICS),
    ("container",         HIGH_RISK_KEYWORDS_CONTAINER),
    ("governance",        HIGH_RISK_KEYWORDS_GOVERNANCE),
]

# Files at the repository root that are high-risk
HIGH_RISK_ROOT_FILES = {
    "backend/main.py",
    "backend/database.py",
    "backend/auth.py",
}

# High-risk labels that force full CI
HIGH_RISK_LABELS = {
    "mode:high-risk",
    "risk:high-risk",
    "risk:auth-rbac",
    "risk:tenancy-rls",
    "risk:finance",
    "risk:database",
    "risk:security",
    "risk:clinical-semantics",
    "risk:deployment",
}

# Closed-list HIGH_RISK structural surfaces from the V2.1 contract. These are
# intentionally broader than filename keywords because a neutral filename can
# still change schema lineage, core security, or a shared contract.
HIGH_RISK_MIGRATION_PREFIXES = (
    "backend/alembic/",
    "backend/migrations_adhoc/",
    "backend/scripts/migrations/",
    "backend/models/",
)
HIGH_RISK_SECURITY_PREFIXES = (
    "backend/core/",
)
HIGH_RISK_SHARED_CONTRACT_PREFIXES = (
    "backend/schemas/",
    "frontend/src/api/",
)

CLINICAL_UI_PREFIXES = (
    "frontend/src/features/clinical-chart",
    "frontend/src/features/odontogram",
)

BACKEND_CLINICAL_SEMANTIC_TOKENS = {
    "clinical", "tooth", "odontogram",
}

# Admin pages/features in the frontend are always high-risk
FRONTEND_ADMIN_PATTERNS = [
    r"^frontend/src/pages/admin/",
    r"^frontend/src/features/admin/",
    r"^frontend/src/locales/superAdmin",
]


def get_changed_files_from_git(base_ref: str = "origin/staging") -> List[str]:
    """Retrieve changed files from git diff."""
    try:
        cmd = ["git", "diff", "--name-only", f"{base_ref}...HEAD"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        files = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
        if not files:
            cmd = ["git", "diff", "--name-only", base_ref, "HEAD"]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            files = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
        return files
    except Exception as e:
        sys.stderr.write(f"Warning: git diff failed ({e}), falling back to fail-safe full validation.\n")
        return []


def parse_labels(labels_input: Union[str, List[str], None]) -> List[str]:
    """Safely parse labels from strings, lists, or JSON objects."""
    if not labels_input:
        return []
    if isinstance(labels_input, list):
        parsed = []
        for item in labels_input:
            if isinstance(item, dict) and "name" in item:
                parsed.append(item["name"])
            elif isinstance(item, str):
                try:
                    obj = json.loads(item)
                    if isinstance(obj, list):
                        parsed.extend([x.get("name", x) if isinstance(x, dict) else str(x) for x in obj])
                    elif isinstance(obj, dict) and "name" in obj:
                        parsed.append(obj["name"])
                    else:
                        parsed.append(item)
                except Exception:
                    parsed.append(item)
        return parsed
    if isinstance(labels_input, str):
        try:
            obj = json.loads(labels_input)
            if isinstance(obj, list):
                return [x.get("name", x) if isinstance(x, dict) else str(x) for x in obj]
            elif isinstance(obj, dict) and "name" in obj:
                return [obj["name"]]
        except Exception:
            return [l.strip() for l in labels_input.split(",") if l.strip()]
    return []


def _normalize_path_tokens(path: str) -> str:
    """Normalize separators and camelCase into underscore-delimited tokens."""
    camel_split = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", path)
    return re.sub(r"[^a-z0-9]+", "_", camel_split.lower()).strip("_")


def _contains_keyword(normalized_path: str, keyword: str) -> bool:
    normalized_keyword = _normalize_path_tokens(keyword)
    return bool(re.search(rf"(?:^|_){re.escape(normalized_keyword)}(?:_|$)", normalized_path))


def _keyword_scan(path: str) -> Dict[str, bool]:
    """Scan a source path for high-risk token sequences and return domain hits."""
    normalized_path = _normalize_path_tokens(path)
    hits: Dict[str, bool] = {}
    for family_name, keywords in _ALL_KEYWORD_FAMILIES:
        for kw in keywords:
            if _contains_keyword(normalized_path, kw):
                hits[family_name] = True
                break
    return hits


def classify_files(
    changed_files: List[str],
    event_name: str = "pull_request",
    target_branch: str = "staging",
    labels: Union[str, List[str], None] = None,
) -> Dict[str, bool]:
    """Classify the changed files and event context into boolean CI flags."""
    label_list = parse_labels(labels)

    classification = {
        "frontend": False,
        "backend": False,
        "mobile": False,
        "dependencies": False,
        "pwa": False,
        "container": False,
        "auth": False,
        "tenancy": False,
        "finance": False,
        "migration": False,
        "security": False,
        "clinical_semantics": False,
        "clinical_ui": False,
        "workflow_governance": False,
        "docs_only": False,
        "force_full": False,
    }

    # ── Rule 1: Protected pushes always force full ──
    if event_name == "push" and target_branch in (
        "staging", "main",
        "refs/heads/staging", "refs/heads/main",
    ):
        classification["force_full"] = True
        return classification

    # ── Rule 2: Manual dispatch always forces full ──
    if event_name == "workflow_dispatch":
        classification["force_full"] = True
        return classification

    # ── Rule 3: High-risk labels force full ──
    for label in label_list:
        if str(label).lower().strip() in HIGH_RISK_LABELS:
            classification["force_full"] = True
            break

    # ── Rule 4: No changed files → fail-safe full ──
    if not changed_files:
        classification["force_full"] = True
        return classification

    unrecognized = []
    docs_files = []

    for f in changed_files:
        path_str = f.replace("\\", "/").strip()
        if not path_str:
            continue

        path_lower = path_str.lower()

        # ── Executable governance surfaces ──
        if path_lower.startswith((
            ".github/workflows/",
            ".github/scripts/",
            ".github/rulesets/",
        )):
            classification["workflow_governance"] = True
            classification["force_full"] = True
            continue

        # ── Documentation / metadata / agent policy ──
        # A document named for a high-risk domain is still documentation, not a
        # production-code change. Executable GitHub surfaces were handled above.
        if (
            path_str.startswith("docs/")
            or path_str.startswith(".agents/")
            or path_str.endswith(".md")
            or path_str in ("AGENTS.md", "PROJECT_STANDARDS.md", "LICENSE", ".gitignore")
            or path_str.startswith(".github/ISSUE_TEMPLATE/")
            or path_str.startswith(".github/PULL_REQUEST_TEMPLATE/")
            or path_str == ".github/pull_request_template.md"
        ):
            docs_files.append(path_str)
            continue

        # ── Dependency files ──
        if path_str in (
            "uv.lock", "pyproject.toml",
            "requirements.txt", "requirements-dev.txt",
            "frontend/package-lock.json", "frontend/package.json",
        ):
            classification["dependencies"] = True
            if path_str.startswith("frontend/"):
                classification["frontend"] = True
            else:
                classification["backend"] = True
            continue

        # ── Closed-list structural HIGH_RISK surfaces ──
        if path_lower.startswith(HIGH_RISK_MIGRATION_PREFIXES):
            classification["backend"] = True
            classification["migration"] = True
            classification["force_full"] = True

        if path_lower.startswith(HIGH_RISK_SECURITY_PREFIXES):
            classification["backend"] = True
            classification["security"] = True
            classification["force_full"] = True

        if path_lower.startswith(HIGH_RISK_SHARED_CONTRACT_PREFIXES):
            subsystem = "frontend" if path_lower.startswith("frontend/") else "backend"
            classification[subsystem] = True
            classification["force_full"] = True

        # ── Keyword-based high-risk scan (primary ambiguity fail-safe) ──
        kw_hits = _keyword_scan(path_str)

        # Backend clinical/tooth/odontogram source is semantic by default. The
        # corresponding frontend feature is clinical UI unless one of the
        # explicit semantic tokens above is present.
        normalized_tokens = set(_normalize_path_tokens(path_str).split("_"))
        if path_lower.startswith("backend/") and normalized_tokens & BACKEND_CLINICAL_SEMANTIC_TOKENS:
            kw_hits["clinical_semantics"] = True

        if kw_hits:
            classification["force_full"] = True
            if "auth" in kw_hits:
                classification["auth"] = True
                classification["security"] = True
            if "tenancy" in kw_hits:
                classification["tenancy"] = True
            if "finance" in kw_hits:
                classification["finance"] = True
            if "migration" in kw_hits:
                classification["migration"] = True
            if "security" in kw_hits:
                classification["security"] = True
            if "clinical_semantics" in kw_hits:
                classification["clinical_semantics"] = True
                if path_lower.startswith(CLINICAL_UI_PREFIXES):
                    classification["clinical_ui"] = True
            if "container" in kw_hits:
                classification["container"] = True
            if "governance" in kw_hits:
                classification["workflow_governance"] = True
            # Still set subsystem flags
            if path_str.startswith("frontend/"):
                classification["frontend"] = True
            elif path_str.startswith("backend/"):
                classification["backend"] = True
            elif path_str.startswith("mobile/") or path_str.startswith("dentix_mobile/"):
                classification["mobile"] = True
            continue

        # ── Known high-risk root files ──
        if path_str in HIGH_RISK_ROOT_FILES:
            classification["force_full"] = True
            classification["backend"] = True
            continue

        # ── Frontend admin pages (always high-risk) ──
        for pat in FRONTEND_ADMIN_PATTERNS:
            if re.search(pat, path_str, re.IGNORECASE):
                classification["force_full"] = True
                classification["frontend"] = True
                classification["auth"] = True
                break
        else:
            # Not an admin pattern - continue to next checks
            pass

        # ── Safe frontend subsystem ──
        if path_str.startswith("frontend/"):
            classification["frontend"] = True
            if path_lower.startswith(CLINICAL_UI_PREFIXES):
                classification["clinical_ui"] = True
            if any(p in path_lower for p in ["pwa", "sw.js", "manifest.json", "preloadrecovery"]):
                classification["pwa"] = True
            continue

        # ── Safe backend subsystem ──
        if path_str.startswith("backend/"):
            classification["backend"] = True
            continue

        # ── Mobile subsystem ──
        if path_str.startswith("mobile/") or path_str.startswith("dentix_mobile/"):
            classification["mobile"] = True
            continue

        # ── Unrecognized path: fail-safe to force_full ──
        unrecognized.append(path_str)

    if unrecognized:
        classification["force_full"] = True

    # Pure docs-only check
    if len(docs_files) == len(changed_files) and not classification["force_full"]:
        classification["docs_only"] = True

    return classification


def main():
    parser = argparse.ArgumentParser(description="Classify DENTIX CI scope from changed files.")
    parser.add_argument("--event", default=os.getenv("GITHUB_EVENT_NAME", "pull_request"))
    parser.add_argument("--base-ref", default=os.getenv("GITHUB_BASE_REF", "origin/staging"))
    parser.add_argument("--target-branch", default=os.getenv("GITHUB_BASE_REF", "staging"))
    parser.add_argument("--files", nargs="*", default=None)
    parser.add_argument("--labels", nargs="*", default=[])
    parser.add_argument("--labels-json", default=os.getenv("PR_LABELS", ""))
    parser.add_argument("--output-format", choices=["json", "github-env", "github-output"], default="json")

    args = parser.parse_args()

    files = args.files if (args.files is not None and len(args.files) > 0) else get_changed_files_from_git(args.base_ref)
    labels = args.labels_json if args.labels_json else args.labels

    result = classify_files(
        changed_files=files,
        event_name=args.event,
        target_branch=args.target_branch,
        labels=labels,
    )

    if args.output_format == "json":
        print(json.dumps(result, indent=2))
    elif args.output_format == "github-output":
        output_file = os.getenv("GITHUB_OUTPUT")
        if output_file:
            with open(output_file, "a", encoding="utf-8") as f:
                for k, v in result.items():
                    f.write(f"{k}={str(v).lower()}\n")
        else:
            for k, v in result.items():
                print(f"{k}={str(v).lower()}")
    elif args.output_format == "github-env":
        env_file = os.getenv("GITHUB_ENV")
        if env_file:
            with open(env_file, "a", encoding="utf-8") as f:
                for k, v in result.items():
                    f.write(f"CI_SCOPE_{k.upper()}={str(v).lower()}\n")
        else:
            for k, v in result.items():
                print(f"CI_SCOPE_{k.upper()}={str(v).lower()}")


if __name__ == "__main__":
    main()
