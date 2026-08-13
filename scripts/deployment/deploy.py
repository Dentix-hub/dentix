"""Request the protected Dentix deployment workflow.

All builds happen in CI. This helper never builds an image or connects directly
to production; it only dispatches the reviewed GitHub Actions workflow.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess


def request_deployment(target: str) -> bool:
    """Dispatch the official staging or production deployment."""
    if shutil.which("gh") is None:
        print("GitHub CLI is not installed.")
        print(
            "Open GitHub Actions, choose 'Dentix CD', and run it with "
            f"target={target}."
        )
        return False

    branch = "main" if target == "production" else "staging"
    result = subprocess.run(
        [
            "gh",
            "workflow",
            "run",
            "cd.yml",
            "--ref",
            branch,
            "-f",
            f"target={target}",
        ],
        check=False,
    )
    if result.returncode == 0:
        print(
            f"{target.title()} deployment requested from {branch}. "
            "Follow approval and health checks in GitHub Actions."
        )
        return True

    print(f"Failed to request the {target} deployment.")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Dentix deployment requester")
    parser.add_argument(
        "--env",
        choices=["staging", "production"],
        required=True,
        help="Protected environment to deploy",
    )
    args = parser.parse_args()
    return 0 if request_deployment(args.env) else 1


if __name__ == "__main__":
    raise SystemExit(main())
