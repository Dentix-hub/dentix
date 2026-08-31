#!/usr/bin/env python3
"""
DENTIX Deterministic CI Signal Evaluator
Evaluates GitHub Actions check-runs and commit statuses for a PR head commit SHA,
sets agent:ci-green / agent:ci-red / agent:awaiting-ci labels, and posts a single
transition comment on state change without any AI model calls.

Guards:
  - Exact match with active ruleset required status checks (12 contexts)
  - App ID validation: only check-runs from the expected GitHub Actions app are trusted
  - Stale SHA race protection: re-fetches PR head SHA just before mutation
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple


# Exact snapshot matching GitHub ruleset "Protect main and staging"
REQUIRED_CHECK_CONTEXTS = [
    "Frozen Dependency Reproducibility",
    "Backend Tests + Security",
    "Frontend Tests",
    "E2E Critical Path (Playwright)",
    "Validate Production Container",
    "Concurrent Tenant Isolation",
    "Reproduce / Recover Stale Frontend Assets",
    "Responsive Acceptance Matrix",
    "Full Git History Secret Scan",
    "Validate promotion path",
    "Protect authoritative CD workflow",
    "Verify GitHub branch enforcement",
]

# GitHub Actions app ID (the official GitHub-hosted runner integration)
GITHUB_ACTIONS_APP_ID = 15368

ACCEPTED_CONCLUSIONS = {"success", "neutral", "skipped"}
CHECK_RUNS_PAGE_SIZE = 100


def github_api_request(
    endpoint: str,
    method: str = "GET",
    data: Optional[dict] = None,
    token: Optional[str] = None,
    repo: Optional[str] = None,
) -> dict:
    """Execute authenticated GitHub API request."""
    token = token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    repo = repo or os.environ.get("GH_REPOSITORY") or os.environ.get("GITHUB_REPOSITORY")

    if not token:
        raise ValueError("GH_TOKEN / GITHUB_TOKEN environment variable required.")
    if not repo:
        raise ValueError("GH_REPOSITORY / GITHUB_REPOSITORY environment variable required.")

    url = f"https://api.github.com/repos/{repo}/{endpoint.lstrip('/')}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "dentix-ci-signal-evaluator",
    }

    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status == 204:
                return {}
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"::error::GitHub API {e.code} for {endpoint}: {err_body[:400]}")
        raise


def get_pr_details(pr_number: int, token: str, repo: str) -> Optional[dict]:
    """Fetch PR details by number."""
    try:
        return github_api_request(f"pulls/{pr_number}", token=token, repo=repo)
    except Exception as e:
        print(f"Warning: could not fetch PR #{pr_number}: {e}")
        return None


def get_open_pr_for_sha(sha: str, token: str, repo: str) -> Optional[dict]:
    """Find open pull request where sha is the current HEAD."""
    try:
        prs = github_api_request(f"commits/{sha}/pulls", token=token, repo=repo)
        for pr in prs:
            if pr.get("state") == "open":
                # Verify sha is indeed current head sha
                pr_head_sha = pr.get("head", {}).get("sha")
                if pr_head_sha == sha:
                    return pr
                else:
                    print(f"Notice: PR #{pr.get('number')} found for commit {sha[:8]}, but current head is {pr_head_sha[:8]}. Skipping stale association.")
    except Exception as e:
        print(f"Warning: could not lookup PR for SHA {sha}: {e}")
    return None


def get_all_check_runs(sha: str, token: str, repo: str) -> List[dict]:
    """Fetch every check-run page for a commit SHA."""
    check_runs = []
    page = 1

    while True:
        data = github_api_request(
            f"commits/{sha}/check-runs?per_page={CHECK_RUNS_PAGE_SIZE}&page={page}",
            token=token,
            repo=repo,
        )
        page_runs = data.get("check_runs", [])
        check_runs.extend(page_runs)

        total_count = data.get("total_count")
        if len(page_runs) < CHECK_RUNS_PAGE_SIZE:
            break
        if isinstance(total_count, int) and len(check_runs) >= total_count:
            break
        page += 1

    return check_runs


def evaluate_checks(sha: str, token: str, repo: str) -> Tuple[str, List[Dict[str, str]], List[str]]:
    """
    Evaluate check runs and statuses for a commit SHA.
    Returns: (state, failing_checks, pending_checks)
    state in ('GREEN', 'RED', 'PENDING')

    Only trusts check-runs from the expected GitHub Actions app (app.id validation).
    """
    check_runs = get_all_check_runs(sha, token=token, repo=repo)

    # Filter check runs to only those from the GitHub Actions app
    # This prevents spoofed or third-party check-runs from influencing the signal.
    trusted_runs = []
    untrusted_count = 0
    for c in check_runs:
        app = c.get("app", {})
        app_id = app.get("id")
        if app_id == GITHUB_ACTIONS_APP_ID:
            trusted_runs.append(c)
        else:
            untrusted_count += 1

    if untrusted_count > 0:
        print(f"Notice: Filtered out {untrusted_count} check-runs from non-GitHub-Actions apps.")

    check_by_name = {}
    for check_run in trusted_runs:
        name = check_run.get("name")
        if not name:
            continue
        current = check_by_name.get(name)
        if current is None or check_run.get("id", 0) > current.get("id", 0):
            check_by_name[name] = check_run

    failing = []
    pending = []

    for req_name in REQUIRED_CHECK_CONTEXTS:
        check = check_by_name.get(req_name)
        if not check:
            pending.append(req_name)
            continue

        status = check.get("status")
        conclusion = check.get("conclusion")

        if status != "completed":
            pending.append(req_name)
        elif conclusion not in ACCEPTED_CONCLUSIONS:
            failing.append({
                "name": req_name,
                "conclusion": conclusion or "unknown",
                "url": check.get("html_url", ""),
            })
        else:
            pass

    if failing:
        return "RED", failing, pending
    elif pending:
        return "PENDING", failing, pending
    else:
        return "GREEN", [], []


def verify_sha_still_current(pr_number: int, expected_sha: str, token: str, repo: str) -> bool:
    """
    Re-fetch PR head SHA just before mutation to guard against TOCTOU race.
    Returns True if the expected SHA is still the current HEAD.
    """
    pr_data = get_pr_details(pr_number, token=token, repo=repo)
    if not pr_data:
        print(f"::error::Could not re-fetch PR #{pr_number} for stale-SHA verification.")
        return False

    current_head = pr_data.get("head", {}).get("sha", "")
    if current_head != expected_sha:
        print(
            f"::warning::Stale SHA detected just before mutation: "
            f"evaluated {expected_sha[:8]} but current HEAD is {current_head[:8]}. "
            f"Aborting label/comment mutation to avoid race condition."
        )
        return False
    return True


def sync_labels(
    pr_number: int,
    target_label: str,
    expected_sha: str,
    token: str,
    repo: str,
) -> bool:
    """
    Ensure PR has exactly the target agent CI label and removes conflicting CI labels.
    Raises on failure instead of silently catching.
    """
    ci_labels = {"agent:ci-green", "agent:ci-red", "agent:awaiting-ci"}

    issue = github_api_request(f"issues/{pr_number}", token=token, repo=repo)
    existing_labels = {l.get("name") for l in issue.get("labels", [])}

    # Remove conflicting labels
    for l in (ci_labels - {target_label}):
        if l in existing_labels:
            if not verify_sha_still_current(
                pr_number, expected_sha, token=token, repo=repo
            ):
                return False
            try:
                github_api_request(
                    f"issues/{pr_number}/labels/{urllib.parse.quote(l)}",
                    method="DELETE",
                    token=token,
                    repo=repo,
                )
                print(f"Removed label '{l}' from PR #{pr_number}")
            except urllib.error.HTTPError as e:
                # 404 is acceptable (label already removed by another process)
                if e.code == 404:
                    print(f"Notice: label '{l}' already absent from PR #{pr_number}")
                else:
                    raise

    # Add target label if missing
    if target_label not in existing_labels:
        if not verify_sha_still_current(
            pr_number, expected_sha, token=token, repo=repo
        ):
            return False
        github_api_request(
            f"issues/{pr_number}/labels",
            method="POST",
            data={"labels": [target_label]},
            token=token,
            repo=repo,
        )
        print(f"Added label '{target_label}' to PR #{pr_number}")
    return True


def post_transition_comment(
    pr_number: int,
    state: str,
    sha: str,
    failing: List[Dict[str, str]],
    pending: List[str],
    token: str,
    repo: str,
) -> bool:
    """Post comment on PR only if state transition occurred."""
    marker = f"<!-- dentix-ci-signal-state:{state}:{sha} -->"

    try:
        comments = github_api_request(f"issues/{pr_number}/comments", token=token, repo=repo)
        for c in comments:
            if marker in c.get("body", ""):
                print(f"Signal comment already present for state {state} on SHA {sha}; skipping duplicate comment.")
                return True

        if state == "GREEN":
            body = (
                f"{marker}\n"
                f"### 🟢 DENTIX CI Signal: GREEN\n\n"
                f"All 12 required status checks have successfully passed for PR head commit `{sha[:8]}`.\n\n"
                f"- **State**: `agent:ci-green`\n"
                f"- **Next Action**: Ready for wave integration review and protected promotion.\n"
            )
        elif state == "RED":
            fail_list = "\n".join([f"- **{f['name']}**: [{f['conclusion']}]({f['url']})" for f in failing])
            body = (
                f"{marker}\n"
                f"### 🔴 DENTIX CI Signal: RED\n\n"
                f"Required status check failures detected on PR head commit `{sha[:8]}`:\n\n"
                f"{fail_list}\n\n"
                f"- **State**: `agent:ci-red`\n"
                f"- **Remediation**: Load `dentix-systematic-debugging`, inspect failing logs, apply minimal surgical fix.\n"
            )
        else:
            return True

        if not verify_sha_still_current(pr_number, sha, token=token, repo=repo):
            return False
        github_api_request(
            f"issues/{pr_number}/comments",
            method="POST",
            data={"body": body},
            token=token,
            repo=repo,
        )
        print(f"Posted {state} transition comment on PR #{pr_number}")
        return True
    except Exception:
        print("::error::post_transition_comment failed.")
        raise


def main():
    parser = argparse.ArgumentParser(description="Evaluate CI signal for PR / commit SHA.")
    parser.add_argument("--sha", required=True, help="Commit SHA to evaluate")
    parser.add_argument("--pr", type=int, default=None, help="PR number (optional)")

    args = parser.parse_args()
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GH_REPOSITORY") or os.environ.get("GITHUB_REPOSITORY", "")

    if not token or not repo:
        print("GH_TOKEN and GH_REPOSITORY environment variables are required.")
        sys.exit(1)

    # 1. Resolve PR and enforce head SHA verification
    pr_data = None
    if args.pr:
        pr_data = get_pr_details(args.pr, token=token, repo=repo)
        if pr_data:
            current_head_sha = pr_data.get("head", {}).get("sha")
            if current_head_sha != args.sha:
                print(f"Skipping PR #{args.pr}: evaluated SHA {args.sha[:8]} is stale (current head is {current_head_sha[:8]}).")
                sys.exit(0)
    else:
        pr_data = get_open_pr_for_sha(args.sha, token=token, repo=repo)

    if not pr_data:
        print(f"No active open PR found with head SHA {args.sha}. Skipping PR signal updates.")
        sys.exit(0)

    pr_number = pr_data["number"]
    state, failing, pending = evaluate_checks(args.sha, token=token, repo=repo)
    print(f"Evaluated CI Signal for PR #{pr_number} (HEAD SHA {args.sha[:8]}): STATE={state}")

    if state == "GREEN":
        if not sync_labels(
            pr_number, "agent:ci-green", args.sha, token=token, repo=repo
        ):
            print("Aborting remaining mutations due to stale SHA.")
            sys.exit(0)
        post_transition_comment(
            pr_number, "GREEN", args.sha, failing, pending, token=token, repo=repo
        )
    elif state == "RED":
        if not sync_labels(
            pr_number, "agent:ci-red", args.sha, token=token, repo=repo
        ):
            print("Aborting remaining mutations due to stale SHA.")
            sys.exit(0)
        post_transition_comment(
            pr_number, "RED", args.sha, failing, pending, token=token, repo=repo
        )
    else:
        sync_labels(
            pr_number, "agent:awaiting-ci", args.sha, token=token, repo=repo
        )


if __name__ == "__main__":
    main()
