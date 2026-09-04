#!/usr/bin/env python3
"""
DENTIX Live Development State Auditor
======================================
Read-only forensic audit tool for repository, branch, worktree,
and local-versus-remote development state.

This tool never performs any mutating actions (no write, no push, no delete).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    try:
        res = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return res.returncode, res.stdout.strip()
    except Exception as exc:
        return 1, str(exc)


def get_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    return current.parent.parent


def audit_head_and_status(root: Path) -> dict:
    _, branch = run_cmd(["git", "branch", "--show-current"], cwd=root)
    _, head_sha = run_cmd(["git", "rev-parse", "HEAD"], cwd=root)
    _, status = run_cmd(["git", "status", "--porcelain"], cwd=root)

    _, origin_staging_sha = run_cmd(["git", "rev-parse", "origin/staging"], cwd=root)
    _, origin_main_sha = run_cmd(["git", "rev-parse", "origin/main"], cwd=root)

    return {
        "current_branch": branch,
        "head_sha": head_sha,
        "is_clean": len(status) == 0,
        "uncommitted_lines": status.splitlines() if status else [],
        "origin_staging_sha": origin_staging_sha,
        "origin_main_sha": origin_main_sha,
        "matches_origin_staging": head_sha == origin_staging_sha,
    }


def audit_branches(root: Path) -> dict:
    # Merged into staging
    _, merged_staging_raw = run_cmd(["git", "branch", "--merged", "staging"], cwd=root)
    merged_staging = [
        line.strip().replace("* ", "").replace("+ ", "")
        for line in merged_staging_raw.splitlines()
        if line.strip()
    ]

    # Merged into main
    _, merged_main_raw = run_cmd(["git", "branch", "--merged", "main"], cwd=root)
    merged_main = [
        line.strip().replace("* ", "").replace("+ ", "")
        for line in merged_main_raw.splitlines()
        if line.strip()
    ]

    # Unmerged into staging
    _, unmerged_raw = run_cmd(["git", "branch", "--no-merged", "staging"], cwd=root)
    unmerged = []
    for line in unmerged_raw.splitlines():
        branch = line.strip().replace("* ", "").replace("+ ", "")
        if not branch:
            continue
        _, ahead = run_cmd(["git", "rev-list", "--count", f"staging..{branch}"], cwd=root)
        _, behind = run_cmd(["git", "rev-list", "--count", f"{branch}..staging"], cwd=root)
        unmerged.append({
            "branch": branch,
            "ahead": int(ahead) if ahead.isdigit() else -1,
            "behind": int(behind) if behind.isdigit() else -1,
        })

    return {
        "merged_into_staging": merged_staging,
        "merged_into_main": merged_main,
        "unmerged_to_staging": unmerged,
    }


def audit_worktrees(root: Path) -> list[dict]:
    _, wt_raw = run_cmd(["git", "worktree", "list", "--porcelain"], cwd=root)
    worktrees = []
    current_wt: dict = {}

    for line in wt_raw.splitlines():
        if line.startswith("worktree "):
            if current_wt:
                worktrees.append(current_wt)
            current_wt = {"path": line.split(" ", 1)[1], "is_clean": True}
        elif line.startswith("HEAD "):
            current_wt["head"] = line.split(" ", 1)[1]
        elif line.startswith("branch "):
            current_wt["branch"] = line.split(" ", 1)[1].replace("refs/heads/", "")

    if current_wt:
        worktrees.append(current_wt)

    for wt in worktrees:
        wt_path = Path(wt["path"])
        if wt_path.exists():
            _, wt_status = run_cmd(["git", "status", "--porcelain"], cwd=wt_path)
            wt["is_clean"] = len(wt_status) == 0
        else:
            wt["exists"] = False

    return worktrees


def audit_github_readonly(root: Path) -> dict:
    if not shutil.which("gh"):
        return {"gh_available": False, "authenticated": False}

    code, auth_out = run_cmd(["gh", "auth", "status"], cwd=root)
    authenticated = code == 0

    prs: list[dict] = []
    if authenticated:
        pr_code, pr_out = run_cmd(
            ["gh", "pr", "list", "--json", "number,title,headRefName,baseRefName,state"],
            cwd=root,
        )
        if pr_code == 0:
            try:
                prs = json.loads(pr_out)
            except Exception:
                prs = []

    return {
        "gh_available": True,
        "authenticated": authenticated,
        "open_prs": prs,
    }


def main() -> int:
    root = get_repo_root()
    print("=" * 65)
    print(f"DENTIX LIVE REPOSITORY AUDIT — {root}")
    print("=" * 65)

    head_info = audit_head_and_status(root)
    print("\n[PRIMARY WORKSPACE]")
    print(f"  Current Branch: {head_info['current_branch']}")
    print(f"  HEAD SHA:       {head_info['head_sha']}")
    print(f"  Working Tree:   {'CLEAN' if head_info['is_clean'] else 'DIRTY'}")
    if not head_info["is_clean"]:
        for line in head_info["uncommitted_lines"]:
            print(f"    {line}")
    print(f"  origin/staging: {head_info['origin_staging_sha']}")
    print(f"  origin/main:    {head_info['origin_main_sha']}")

    branches = audit_branches(root)
    print("\n[BRANCH HYGIENE]")
    print(f"  Merged into staging ({len(branches['merged_into_staging'])}):")
    for b in sorted(branches["merged_into_staging"]):
        print(f"    - {b}")

    print(f"\n  Unmerged branches ({len(branches['unmerged_to_staging'])}):")
    for item in branches["unmerged_to_staging"]:
        print(f"    - {item['branch']:<42} ahead={item['ahead']:<3} behind={item['behind']}")

    worktrees = audit_worktrees(root)
    print(f"\n[REGISTERED WORKTREES ({len(worktrees)})]")
    for wt in worktrees:
        clean_str = "CLEAN" if wt.get("is_clean") else "DIRTY"
        print(f"  - {wt.get('branch', 'DETACHED'):<40} [{clean_str}] {wt['path']}")

    gh_info = audit_github_readonly(root)
    print("\n[GITHUB READ-ONLY STATUS]")
    print(f"  GH CLI Available: {gh_info['gh_available']}")
    print(f"  Authenticated:    {gh_info['authenticated']}")
    if gh_info.get("open_prs"):
        print(f"  Open PRs ({len(gh_info['open_prs'])}):")
        for pr in gh_info["open_prs"]:
            print(f"    #{pr.get('number')} [{pr.get('headRefName')} -> {pr.get('baseRefName')}]: {pr.get('title')}")
    else:
        print("  Open PRs: 0 found")

    print("\n" + "=" * 65)
    print("Audit completed successfully. Mode: READ-ONLY (no state altered).")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(main())
