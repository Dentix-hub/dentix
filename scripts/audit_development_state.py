#!/usr/bin/env python3
"""
DENTIX Live Development State Auditor (V3 Contract)
====================================================
Read-only forensic audit tool for repository, branch, worktree,
and local-versus-remote development state.

This tool never performs any mutating actions (no write, no push, no fetch, no delete).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    """Execute command safely and return (returncode, stdout)."""
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


def audit_local_state(root: Path) -> dict:
    _, branch = run_cmd(["git", "branch", "--show-current"], cwd=root)
    _, head_sha = run_cmd(["git", "rev-parse", "HEAD"], cwd=root)
    _, status = run_cmd(["git", "status", "--porcelain"], cwd=root)

    # Local tracking refs
    _, local_origin_staging = run_cmd(["git", "rev-parse", "origin/staging"], cwd=root)
    _, local_origin_main = run_cmd(["git", "rev-parse", "origin/main"], cwd=root)

    # Local branch inventory and ahead/behind vs staging
    _, branch_lines_raw = run_cmd(["git", "for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads/"], cwd=root)
    local_branches: list[dict] = []

    for line in branch_lines_raw.splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        b_name = parts[0]
        b_sha = parts[1] if len(parts) > 1 else ""

        _, ahead = run_cmd(["git", "rev-list", "--count", f"staging..{b_name}"], cwd=root)
        _, behind = run_cmd(["git", "rev-list", "--count", f"{b_name}..staging"], cwd=root)

        local_branches.append({
            "name": b_name,
            "sha": b_sha,
            "ahead_vs_staging": int(ahead) if ahead.isdigit() else -1,
            "behind_vs_staging": int(behind) if behind.isdigit() else -1,
        })

    return {
        "current_branch": branch,
        "head_sha": head_sha,
        "is_clean": len(status) == 0,
        "uncommitted_lines": status.splitlines() if status else [],
        "local_origin_staging": local_origin_staging,
        "local_origin_main": local_origin_main,
        "local_branches": local_branches,
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


def audit_remote_github(root: Path, local_state: dict) -> dict:
    if not shutil.which("gh"):
        return {
            "status": "REMOTE_AUDIT_PARTIAL",
            "reason": "gh CLI not found on PATH",
        }

    auth_code, _ = run_cmd(["gh", "auth", "status"], cwd=root)
    if auth_code != 0:
        return {
            "status": "REMOTE_AUDIT_PARTIAL",
            "reason": "gh not authenticated",
        }

    # Determine nameWithOwner
    repo_code, repo_out = run_cmd(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"], cwd=root)
    repo_name = repo_out.strip() if repo_code == 0 and repo_out.strip() else "Dentix-hub/dentix"

    # Remote branches inventory
    branches_code, branches_out = run_cmd(
        ["gh", "api", f"repos/{repo_name}/branches", "--paginate", "--jq", ".[] | {name: .name, sha: .commit.sha}"],
        cwd=root,
    )
    remote_branches: dict[str, str] = {}
    if branches_code == 0:
        for line in branches_out.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                b_info = json.loads(line)
                remote_branches[b_info["name"]] = b_info["sha"]
            except Exception:
                pass

    remote_main_sha = remote_branches.get("main", "")
    remote_staging_sha = remote_branches.get("staging", "")

    # Compare remote vs local remote-tracking refs
    local_origin_main = local_state.get("local_origin_main", "")
    local_origin_staging = local_state.get("local_origin_staging", "")

    stale_refs: list[str] = []
    if remote_main_sha and local_origin_main and remote_main_sha != local_origin_main:
        stale_refs.append(f"origin/main (local tracking: {local_origin_main[:8]}, remote live: {remote_main_sha[:8]})")
    if remote_staging_sha and local_origin_staging and remote_staging_sha != local_origin_staging:
        stale_refs.append(f"origin/staging (local tracking: {local_origin_staging[:8]}, remote live: {remote_staging_sha[:8]})")

    # Open PRs
    prs: list[dict] = []
    pr_code, pr_out = run_cmd(
        ["gh", "pr", "list", "--state", "open", "--json", "number,title,headRefName,baseRefName,state"],
        cwd=root,
    )
    if pr_code == 0 and pr_out.strip():
        try:
            prs = json.loads(pr_out)
        except Exception:
            prs = []

    # Blocked issues (agent:blocked)
    blocked_issues: list[dict] = []
    issue_code, issue_out = run_cmd(
        ["gh", "issue", "list", "--state", "open", "--json", "number,title,labels,state"],
        cwd=root,
    )
    if issue_code == 0 and issue_out.strip():
        try:
            all_issues = json.loads(issue_out)
            for iss in all_issues:
                label_names = [lbl.get("name", "").lower() for lbl in iss.get("labels", [])]
                if any("blocked" in lbl for lbl in label_names):
                    blocked_issues.append({
                        "number": iss.get("number"),
                        "title": iss.get("title"),
                        "labels": [lbl.get("name") for lbl in iss.get("labels", [])],
                    })
        except Exception:
            pass

    # Governance drift between remote main and staging
    governance_files = [
        "AGENTS.md",
        "PROJECT_STANDARDS.md",
        "docs/engineering/DEVELOPMENT_WORKFLOW.md",
        ".agents/README.md",
        ".github/workflows/branch-governance.yml",
    ]
    drift_report: dict[str, str] = {}
    cmp_code, cmp_out = run_cmd(
        ["gh", "api", f"repos/{repo_name}/compare/main...staging"],
        cwd=root,
    )
    if cmp_code == 0 and cmp_out.strip():
        try:
            cmp_data = json.loads(cmp_out)
            changed_files = {f["filename"]: f.get("status", "modified") for f in cmp_data.get("files", [])}
            for gfile in governance_files:
                if gfile in changed_files:
                    drift_report[gfile] = f"DRIFT DETECTED ({changed_files[gfile]} on staging vs main)"
                else:
                    drift_report[gfile] = "IN SYNC (identical between remote main and staging)"
        except Exception as e:
            drift_report = {f: f"Error inspecting drift: {e}" for f in governance_files}
    else:
        drift_report = {f: "Unable to compare remote main..staging" for f in governance_files}

    return {
        "status": "REMOTE_AUDIT_LIVE",
        "repo_name": repo_name,
        "remote_branches_count": len(remote_branches),
        "remote_branches": remote_branches,
        "remote_main_sha": remote_main_sha,
        "remote_staging_sha": remote_staging_sha,
        "stale_tracking_refs": stale_refs,
        "open_prs": prs,
        "blocked_issues": blocked_issues,
        "governance_drift": drift_report,
    }


def detect_duplicate_work(local_branches: list[dict], open_prs: list[dict], blocked_issues: list[dict]) -> list[dict]:
    """
    Heuristic detection for duplicate ticket work across active branches and PRs.
    Identifies ticket IDs like ODG-A12, ODG-144, or shared functional keywords.
    """
    findings: list[dict] = []

    # Map ticket/feature keys to candidate targets
    token_pattern = re.compile(r"(ODG-[A-Z0-9]+|ODONTOGRAM|PROMOTION|RECONCILIATION|APPROVAL-SLICE)", re.IGNORECASE)
    items_by_token: dict[str, list[str]] = {}

    for b in local_branches:
        name = b["name"]
        # Only active unmerged or candidate branches
        if b.get("ahead_vs_staging", 0) > 0 or "odontogram" in name.lower() or "codex" in name.lower() or "workflow" in name.lower():
            tokens = set(token_pattern.findall(name.upper()))
            for tok in tokens:
                items_by_token.setdefault(tok, []).append(f"local-branch:{name}")

    for pr in open_prs:
        title = pr.get("title", "")
        head = pr.get("headRefName", "")
        tokens = set(token_pattern.findall(f"{title} {head}".upper()))
        for tok in tokens:
            items_by_token.setdefault(tok, []).append(f"pr:#{pr.get('number')} ({head})")

    for tok, sources in items_by_token.items():
        unique_sources = sorted(set(sources))
        if len(unique_sources) > 1:
            findings.append({
                "identifier": tok,
                "sources": unique_sources,
                "label": "POSSIBLE_DUPLICATE_WORK",
            })

    return findings


def main() -> int:
    root = get_repo_root()
    print("=" * 72)
    print(f"DENTIX LIVE DEVELOPMENT STATE AUDITOR (V3 READ-ONLY)")
    print(f"Repository Root: {root}")
    print("=" * 72)

    # 1. Local State
    local_state = audit_local_state(root)
    print("\n[LOCAL WORKSPACE STATE]")
    print(f"  Current Branch: {local_state['current_branch']}")
    print(f"  HEAD SHA:       {local_state['head_sha']}")
    print(f"  Working Tree:   {'CLEAN' if local_state['is_clean'] else 'DIRTY'}")
    if not local_state["is_clean"]:
        print(f"  Uncommitted changes ({len(local_state['uncommitted_lines'])} lines):")
        for line in local_state["uncommitted_lines"]:
            print(f"    {line}")

    # 2. Registered Worktrees
    worktrees = audit_worktrees(root)
    print(f"\n[REGISTERED WORKTREES ({len(worktrees)})]")
    for wt in worktrees:
        clean_str = "CLEAN" if wt.get("is_clean") else "DIRTY"
        print(f"  - {wt.get('branch', 'DETACHED'):<38} [{clean_str}] {wt['path']}")

    # 3. Local Branches & Staging Delta
    print(f"\n[LOCAL BRANCHES & DELTA VS STAGING ({len(local_state['local_branches'])})]")
    for b in local_state["local_branches"]:
        ahead = b["ahead_vs_staging"]
        behind = b["behind_vs_staging"]
        delta_str = f"ahead={ahead:<3} behind={behind:<3}"
        print(f"  - {b['name']:<42} {b['sha'][:8]}  [{delta_str}]")

    # 4. Remote State & Live Checks
    remote_info = audit_remote_github(root, local_state)
    print("\n[REMOTE GITHUB LIVE STATE]")
    print(f"  Audit Status:        {remote_info['status']}")

    if remote_info["status"] == "REMOTE_AUDIT_LIVE":
        print(f"  Remote Repository:   {remote_info['repo_name']}")
        print(f"  Remote Branches:     {remote_info['remote_branches_count']} branches discovered")
        print(f"  Remote 'main' SHA:    {remote_info['remote_main_sha']}")
        print(f"  Remote 'staging' SHA: {remote_info['remote_staging_sha']}")
        print(f"  Local origin/staging: {local_state['local_origin_staging']}")
        print(f"  Local origin/main:    {local_state['local_origin_main']}")

        if remote_info["stale_tracking_refs"]:
            print("  [WARN] Stale Local Tracking Refs Detected:")
            for s in remote_info["stale_tracking_refs"]:
                print(f"    ! {s}")
        else:
            print("  Local tracking refs are in sync with live remote.")

        # PRs
        prs = remote_info["open_prs"]
        print(f"\n[OPEN PULL REQUESTS ({len(prs)})]")
        if prs:
            for pr in prs:
                print(f"  - PR #{pr.get('number')} [{pr.get('headRefName')} -> {pr.get('baseRefName')}]: {pr.get('title')}")
        else:
            print("  0 open pull requests found.")

        # Blocked Issues
        blocked = remote_info["blocked_issues"]
        print(f"\n[BLOCKED ISSUES / AGENT EXECUTION STATE ({len(blocked)})]")
        if blocked:
            for iss in blocked:
                lbls = ", ".join(iss.get("labels", []))
                print(f"  - Issue #{iss.get('number')}: {iss.get('title')}")
                print(f"    Labels: [{lbls}]")
        else:
            print("  No open issues carrying 'agent:blocked' state.")

        # Main vs Staging Governance Drift
        drift = remote_info.get("governance_drift", {})
        print("\n[MAIN / STAGING GOVERNANCE DRIFT]")
        for f, res in drift.items():
            print(f"  - {f:<46} : {res}")

        # Duplicate Work Detection
        dup_findings = detect_duplicate_work(local_state["local_branches"], prs, blocked)
        print(f"\n[DUPLICATE TICKET DETECTION ({len(dup_findings)})]")
        if dup_findings:
            for f in dup_findings:
                print(f"  - [{f['label']}] Target Token '{f['identifier']}':")
                for src in f["sources"]:
                    print(f"      * {src}")
        else:
            print("  No duplicate active branch targets detected.")

    else:
        print(f"  Reason: {remote_info.get('reason')}")
        print("  Remote queries skipped to preserve non-mutating local offline contract.")

    print("\n" + "=" * 72)
    print("Audit completed successfully. Mode: READ-ONLY (no state altered).")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
