#!/usr/bin/env python3
"""
DENTIX Live Development State Auditor (V3 Contract)
====================================================
Read-only forensic audit tool for repository, branch, worktree,
and local-versus-remote development state.

This tool never performs any mutating actions (no write, no push, no fetch, no delete).
"""

from __future__ import annotations

import argparse
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
    local_errors: list[str] = []

    code_b, branch = run_cmd(["git", "branch", "--show-current"], cwd=root)
    if code_b != 0:
        local_errors.append(f"git branch --show-current failed: {branch}")

    code_h, head_sha = run_cmd(["git", "rev-parse", "HEAD"], cwd=root)
    if code_h != 0:
        local_errors.append(f"git rev-parse HEAD failed: {head_sha}")

    code_s, status = run_cmd(["git", "status", "--porcelain"], cwd=root)
    if code_s != 0:
        local_errors.append(f"git status --porcelain failed: {status}")

    # Local tracking refs
    code_ostag, local_origin_staging = run_cmd(["git", "rev-parse", "origin/staging"], cwd=root)
    if code_ostag != 0:
        local_errors.append(f"git rev-parse origin/staging failed: {local_origin_staging}")

    code_omain, local_origin_main = run_cmd(["git", "rev-parse", "origin/main"], cwd=root)
    if code_omain != 0:
        local_errors.append(f"git rev-parse origin/main failed: {local_origin_main}")

    branch_delta_baseline_ref = "origin/staging"
    branch_delta_baseline_sha = local_origin_staging if code_ostag == 0 else "UNKNOWN"

    # Local branch inventory and ahead/behind vs the remote-tracking staging ref.
    code_refs, branch_lines_raw = run_cmd(
        ["git", "for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads/"], cwd=root
    )
    if code_refs != 0:
        local_errors.append(f"git for-each-ref failed: {branch_lines_raw}")

    local_branches: list[dict] = []
    if code_refs == 0:
        for line in branch_lines_raw.splitlines():
            parts = line.strip().split()
            if not parts:
                continue
            b_name = parts[0]
            b_sha = parts[1] if len(parts) > 1 else ""
            if not b_sha:
                local_errors.append(f"Missing SHA for branch '{b_name}' in branch inventory: '{line}'")

            code_ahead, ahead = run_cmd(
                ["git", "rev-list", "--count", f"{branch_delta_baseline_ref}..{b_name}"], cwd=root
            )
            if code_ahead != 0:
                local_errors.append(
                    f"git rev-list --count {branch_delta_baseline_ref}..{b_name} failed: {ahead}"
                )
                ahead_val = -1
            else:
                ahead_val = int(ahead) if ahead.isdigit() else -1

            code_behind, behind = run_cmd(
                ["git", "rev-list", "--count", f"{b_name}..{branch_delta_baseline_ref}"], cwd=root
            )
            if code_behind != 0:
                local_errors.append(
                    f"git rev-list --count {b_name}..{branch_delta_baseline_ref} failed: {behind}"
                )
                behind_val = -1
            else:
                behind_val = int(behind) if behind.isdigit() else -1

            local_branches.append({
                "name": b_name,
                "sha": b_sha,
                "ahead_vs_staging": ahead_val,
                "behind_vs_staging": behind_val,
            })

    return {
        "current_branch": branch if code_b == 0 else "UNKNOWN",
        "head_sha": head_sha if code_h == 0 else "UNKNOWN",
        "is_clean": len(status) == 0 if code_s == 0 else False,
        "uncommitted_lines": status.splitlines() if (code_s == 0 and status) else [],
        "local_origin_staging": local_origin_staging if code_ostag == 0 else "UNKNOWN",
        "local_origin_main": local_origin_main if code_omain == 0 else "UNKNOWN",
        "branch_delta_baseline_ref": branch_delta_baseline_ref,
        "branch_delta_baseline_sha": branch_delta_baseline_sha,
        "local_branches": local_branches,
        "errors": local_errors,
    }


def audit_worktrees(root: Path) -> tuple[list[dict], list[str]]:
    errors: list[str] = []
    code, wt_raw = run_cmd(["git", "worktree", "list", "--porcelain"], cwd=root)
    if code != 0:
        errors.append(f"git worktree list failed: {wt_raw}")
        return [], errors

    worktrees: list[dict] = []
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
            status_code, wt_status = run_cmd(["git", "status", "--porcelain"], cwd=wt_path)
            if status_code != 0:
                wt["is_clean"] = False
                wt["status_failed"] = True
                errors.append(f"git status --porcelain failed for worktree at '{wt_path}': {wt_status}")
            else:
                wt["is_clean"] = len(wt_status) == 0
                wt["status_failed"] = False
        else:
            wt["exists"] = False
            wt["is_clean"] = False
            wt["status_failed"] = True
            errors.append(f"Registered worktree directory does not exist: '{wt_path}'")

    return worktrees, errors


def audit_remote_github(root: Path, local_state: dict) -> dict:
    if not shutil.which("gh"):
        return {
            "status": "REMOTE_AUDIT_FAILED",
            "reason": "gh CLI not found on PATH",
            "errors": ["gh CLI not found on PATH"],
        }

    auth_code, auth_out = run_cmd(["gh", "auth", "status"], cwd=root)
    if auth_code != 0:
        return {
            "status": "REMOTE_AUDIT_FAILED",
            "reason": f"gh not authenticated: {auth_out.splitlines()[0] if auth_out else 'unknown error'}",
            "errors": [f"gh auth status failed: {auth_out}"],
        }

    # Determine nameWithOwner
    repo_code, repo_out = run_cmd(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"], cwd=root
    )
    if repo_code != 0 or not repo_out.strip():
        return {
            "status": "REMOTE_AUDIT_FAILED",
            "reason": f"Failed to determine repository identity: {repo_out}",
            "errors": [f"gh repo view failed: {repo_out}"],
        }

    repo_name = repo_out.strip()
    query_errors: list[str] = []

    # Remote branches inventory
    branches_code, branches_out = run_cmd(
        ["gh", "api", f"repos/{repo_name}/branches", "--paginate", "--jq", ".[] | {name: .name, sha: .commit.sha}"],
        cwd=root,
    )
    remote_branches: dict[str, str] = {}
    if branches_code != 0:
        query_errors.append(f"Failed to query remote branches: {branches_out}")
    else:
        for line in branches_out.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                b_info = json.loads(line)
                remote_branches[b_info["name"]] = b_info["sha"]
            except Exception as exc:
                query_errors.append(f"Malformed branch JSON line '{line}': {exc}")

        if not remote_branches and not query_errors:
            query_errors.append("Remote branch inventory returned empty list from API")

    remote_main_sha = remote_branches.get("main", "")
    remote_staging_sha = remote_branches.get("staging", "")

    if not remote_main_sha:
        query_errors.append("Remote branch 'main' not found in remote branch inventory")
    if not remote_staging_sha:
        query_errors.append("Remote branch 'staging' not found in remote branch inventory")

    # Compare remote vs local remote-tracking refs
    local_origin_main = local_state.get("local_origin_main", "")
    local_origin_staging = local_state.get("local_origin_staging", "")

    stale_refs: list[str] = []
    if remote_main_sha and local_origin_main and remote_main_sha != local_origin_main:
        stale_refs.append(
            f"origin/main (local tracking: {local_origin_main[:8]}, remote live: {remote_main_sha[:8]})"
        )
    if remote_staging_sha and local_origin_staging and remote_staging_sha != local_origin_staging:
        stale_refs.append(
            f"origin/staging (local tracking: {local_origin_staging[:8]}, remote live: {remote_staging_sha[:8]})"
        )

    # Open PRs
    prs: list[dict] | None = None
    pr_code, pr_out = run_cmd(
        ["gh", "pr", "list", "--state", "open", "--json", "number,title,headRefName,baseRefName,state"],
        cwd=root,
    )
    if pr_code != 0:
        query_errors.append(f"Failed to query open PRs: {pr_out}")
    else:
        try:
            prs = json.loads(pr_out)
        except Exception as exc:
            query_errors.append(f"Malformed open PR JSON response: {exc}")
            prs = None

    # Blocked issues
    blocked_issues: list[dict] | None = None
    issue_code, issue_out = run_cmd(
        ["gh", "issue", "list", "--state", "open", "--json", "number,title,labels,state"],
        cwd=root,
    )
    if issue_code != 0:
        query_errors.append(f"Failed to query open issues: {issue_out}")
    else:
        try:
            all_issues = json.loads(issue_out)
            blocked_issues = []
            for iss in all_issues:
                label_names = [lbl.get("name", "").lower() for lbl in iss.get("labels", [])]
                if any("blocked" in lbl for lbl in label_names):
                    blocked_issues.append({
                        "number": iss.get("number"),
                        "title": iss.get("title"),
                        "labels": [lbl.get("name") for lbl in iss.get("labels", [])],
                    })
        except Exception as exc:
            query_errors.append(f"Malformed open issues JSON response: {exc}")
            blocked_issues = None

    # Main / Staging governance drift
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
    if cmp_code != 0:
        query_errors.append(f"Failed to compare remote main...staging: {cmp_out}")
        drift_report = {f: "Comparison query failed" for f in governance_files}
    else:
        try:
            cmp_data = json.loads(cmp_out)
            changed_files = {f["filename"]: f.get("status", "modified") for f in cmp_data.get("files", [])}
            for gfile in governance_files:
                if gfile in changed_files:
                    drift_report[gfile] = f"DRIFT DETECTED ({changed_files[gfile]} on staging vs main)"
                else:
                    drift_report[gfile] = "IN SYNC (identical between remote main and staging)"
        except Exception as exc:
            query_errors.append(f"Malformed compare JSON response: {exc}")
            drift_report = {f: f"Error parsing compare JSON: {exc}" for f in governance_files}

    # Final Remote Status Determination
    status = "REMOTE_AUDIT_LIVE" if not query_errors else "REMOTE_AUDIT_PARTIAL"

    return {
        "status": status,
        "repo_name": repo_name,
        "remote_branches_count": len(remote_branches),
        "remote_branches": remote_branches,
        "remote_main_sha": remote_main_sha,
        "remote_staging_sha": remote_staging_sha,
        "stale_tracking_refs": stale_refs,
        "open_prs": prs,
        "blocked_issues": blocked_issues,
        "governance_drift": drift_report,
        "errors": query_errors,
    }


def detect_duplicate_work(
    local_branches: list[dict],
    open_prs: list[dict] | None,
    blocked_issues: list[dict] | None,
) -> list[dict]:
    """
    Heuristic detection for duplicate ticket work across active branches and PRs.
    Identifies ticket IDs like ODG-A12, ODG-144, or shared functional keywords.
    """
    findings: list[dict] = []
    token_pattern = re.compile(
        r"(ODG-[A-Z0-9]+|ODONTOGRAM|PROMOTION|RECONCILIATION|APPROVAL-SLICE)", re.IGNORECASE
    )
    items_by_token: dict[str, list[str]] = {}

    for b in local_branches:
        name = b["name"]
        if (
            b.get("ahead_vs_staging", 0) > 0
            or "odontogram" in name.lower()
            or "codex" in name.lower()
            or "workflow" in name.lower()
        ):
            tokens = set(token_pattern.findall(name.upper()))
            for tok in tokens:
                items_by_token.setdefault(tok, []).append(f"local-branch:{name}")

    if open_prs:
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DENTIX Live Development State Auditor (Read-Only)")
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Strict qualification mode: exits non-zero if the workspace/worktrees are dirty, "
            "remote audit is not LIVE, refs are stale, unresolved duplicate work exists, or errors occur"
        ),
    )
    parser.add_argument(
        "--allow-duplicate-token",
        action="append",
        default=[],
        metavar="TOKEN",
        help="Explicitly accept one duplicate-work token for this audit run; repeat for multiple tokens",
    )
    args = parser.parse_args(argv)

    root = get_repo_root()
    print("=" * 72)
    print("DENTIX LIVE DEVELOPMENT STATE AUDITOR (V3 READ-ONLY)")
    print(f"Repository Root: {root}")
    print(f"Mode: {'STRICT QUALIFICATION' if args.strict else 'INFORMATIONAL READ-ONLY'}")
    print("=" * 72)

    has_failures = False

    # 1. Local State
    local_state = audit_local_state(root)
    print("\n[LOCAL WORKSPACE STATE]")
    print(f"  Current Branch: {local_state['current_branch']}")
    print(f"  HEAD SHA:       {local_state['head_sha']}")
    print(f"  Working Tree:   {'CLEAN' if local_state['is_clean'] else 'DIRTY'}")
    if not local_state["is_clean"]:
        has_failures = True
        print(f"  Uncommitted changes ({len(local_state['uncommitted_lines'])} lines):")
        for line in local_state["uncommitted_lines"]:
            print(f"    {line}")

    if local_state.get("errors"):
        has_failures = True
        print("  [ERROR] Local Git inspection encountered errors:")
        for err in local_state["errors"]:
            print(f"    ! {err}")

    # 2. Registered Worktrees
    worktrees, wt_errors = audit_worktrees(root)
    print(f"\n[REGISTERED WORKTREES ({len(worktrees)})]")
    for wt in worktrees:
        if wt.get("status_failed"):
            clean_str = "STATUS_FAILED"
        elif wt.get("is_clean"):
            clean_str = "CLEAN"
        else:
            clean_str = "DIRTY"
        print(f"  - {wt.get('branch', 'DETACHED'):<38} [{clean_str}] {wt['path']}")
    if wt_errors:
        has_failures = True
        for err in wt_errors:
            print(f"    ! {err}")
    if any(not wt.get("is_clean", False) for wt in worktrees):
        has_failures = True

    # 3. Local Branches & Staging Delta
    baseline_ref = local_state.get("branch_delta_baseline_ref", "UNKNOWN")
    baseline_sha = local_state.get("branch_delta_baseline_sha", "UNKNOWN")
    print(f"\n[LOCAL BRANCHES & DELTA VS {baseline_ref.upper()} ({len(local_state['local_branches'])})]")
    print(f"  Baseline: {baseline_ref} @ {baseline_sha}")
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
            has_failures = True
            print("  [WARN] Stale Local Tracking Refs Detected:")
            for s in remote_info["stale_tracking_refs"]:
                print(f"    ! {s}")
        else:
            print("  Local tracking refs are in sync with live remote.")

        # PRs
        prs = remote_info["open_prs"]
        if prs is not None:
            print(f"\n[OPEN PULL REQUESTS ({len(prs)})]")
            if prs:
                for pr in prs:
                    print(
                        f"  - PR #{pr.get('number')} [{pr.get('headRefName')} -> {pr.get('baseRefName')}]: {pr.get('title')}"
                    )
            else:
                print("  0 open pull requests found.")
        else:
            has_failures = True
            print("\n[OPEN PULL REQUESTS]")
            print("  [ERROR] Failed to retrieve open pull requests from GitHub.")

        # Blocked Issues
        blocked = remote_info["blocked_issues"]
        if blocked is not None:
            print(f"\n[BLOCKED ISSUES / AGENT EXECUTION STATE ({len(blocked)})]")
            if blocked:
                for iss in blocked:
                    lbls = ", ".join(iss.get("labels", []))
                    print(f"  - Issue #{iss.get('number')}: {iss.get('title')}")
                    print(f"    Labels: [{lbls}]")
            else:
                print("  No open issues carrying 'agent:blocked' state.")
        else:
            has_failures = True
            print("\n[BLOCKED ISSUES]")
            print("  [ERROR] Failed to retrieve open issues from GitHub.")

        # Main vs Staging Governance Drift
        drift = remote_info.get("governance_drift", {})
        print("\n[MAIN / STAGING GOVERNANCE DRIFT]")
        for f, res in drift.items():
            print(f"  - {f:<46} : {res}")

        # Duplicate Work Detection
        dup_findings = detect_duplicate_work(local_state["local_branches"], prs, blocked)
        accepted_duplicate_tokens = {
            token.strip().upper() for token in args.allow_duplicate_token if token.strip()
        }
        unresolved_duplicates = [
            finding
            for finding in dup_findings
            if finding["identifier"].upper() not in accepted_duplicate_tokens
        ]
        print(f"\n[DUPLICATE TICKET DETECTION ({len(dup_findings)})]")
        if dup_findings:
            for f in dup_findings:
                accepted = f["identifier"].upper() in accepted_duplicate_tokens
                label = "ACCEPTED_DUPLICATE" if accepted else f["label"]
                print(f"  - [{label}] Target Token '{f['identifier']}':")
                for src in f["sources"]:
                    print(f"      * {src}")
            if unresolved_duplicates:
                has_failures = True
        else:
            print("  No duplicate active branch targets detected.")

    else:
        has_failures = True
        print(f"  Reason: {remote_info.get('reason', 'Remote query error')}")
        if remote_info.get("errors"):
            print("  Diagnostic Errors:")
            for err in remote_info["errors"]:
                print(f"    ! {err}")

        # Print partial PR/issues if present
        prs = remote_info.get("open_prs")
        if prs is not None:
            print(f"\n[OPEN PULL REQUESTS ({len(prs)})]")
            for pr in prs:
                print(f"  - PR #{pr.get('number')}: {pr.get('title')}")
        else:
            print("\n[OPEN PULL REQUESTS: QUERY FAILED OR SKIPPED]")

        blocked = remote_info.get("blocked_issues")
        if blocked is not None:
            print(f"\n[BLOCKED ISSUES ({len(blocked)})]")
            for iss in blocked:
                print(f"  - Issue #{iss.get('number')}: {iss.get('title')}")
        else:
            print("\n[BLOCKED ISSUES: QUERY FAILED OR SKIPPED]")

    print("\n" + "=" * 72)
    if has_failures:
        print("Audit completed with warnings/partial state. Mode: READ-ONLY (no state altered).")
    else:
        print("Audit completed successfully. Mode: READ-ONLY (no state altered).")
    print("=" * 72)

    if args.strict and has_failures:
        print("\n::error::STRICT QUALIFICATION FAILURE: One or more qualification checks failed.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
