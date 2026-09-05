#!/usr/bin/env python3
"""
scripts/verify_external_skills.py
=================================
Deterministic, offline-capable provenance verifier for external delegate skills.
Verifies integrity and origin against docs/engineering/EXTERNAL_SKILLS_LOCK.json.

Gate Contract:
- Full provenance verification requires both:
    1. Validating the lock manifest against the pinned upstream source repository (--source-root)
    2. Validating installed skills against that verified manifest (--installed-root)
  When both pass, returns exit code 0 and emits:
    EXTERNAL_SKILL_PROVENANCE = PASS
- When --source-root is omitted, the verifier runs in DIAGNOSTIC ONLY mode:
  It inspects installed skills but CANNOT award gate PASS.
  If installed skills match, it exits with code 2 (DIAGNOSTIC_PASS_SOURCE_UNVERIFIED).
  If any check fails, it exits with code 1 (VERIFICATION_FAILURE).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Any

SCHEMA_VERSION = "1.0.0"
SOURCE_NAME = "delegate-skills"
CANONICAL_REPO_URL = "https://github.com/amElnagdy/delegate-skills.git"
CANONICAL_PINNED_COMMIT = "b781ee2e23089630e2fbee1cfd6174afe4edeb76"
REQUIRED_SKILLS = ["delegate-setup", "agy-delegate", "codex-delegate"]
DECLARED_VERSION = "0.5.0"
DECLARED_LICENSE = "MIT"

ALLOWED_ROOT_KEYS = {"schema_version", "source", "skills"}
ALLOWED_SOURCE_KEYS = {"name", "repository_url", "pinned_commit", "license", "declared_version"}
ALLOWED_SKILL_KEYS = {"upstream_subpath", "installed_subpath", "declared_version", "license", "file_count", "files"}
ALLOWED_FILE_META_KEYS = {"sha256", "size"}

IGNORED_DIRS = {".git", "__pycache__"}
IGNORED_EXTENSIONS = {".pyc", ".pyo"}
IGNORED_FILES = {".ds_store", "thumbs.db", "desktop.ini", ".directory"}

ABSOLUTE_PATH_PATTERN = re.compile(
    r"^(?:[a-zA-Z]:[\\/]|/(?:home|Users|tmp|var|opt|usr|etc|root)(?:/|$))",
    re.IGNORECASE,
)
SHA256_HEX_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def is_ignored(path: Path, rel_to_skill: Path) -> bool:
    """Return True if the file should be ignored as non-source / OS metadata."""
    for p in rel_to_skill.parts[:-1]:
        if p in IGNORED_DIRS or p.startswith(".git"):
            return True
    filename = path.name.lower()
    if filename in IGNORED_FILES:
        return True
    if path.suffix.lower() in IGNORED_EXTENSIONS:
        return True
    if filename.startswith(".") and filename.endswith(".swp"):
        return True
    return False


def validate_safe_relative_path(path_str: str, context: str, failures: list[str]) -> bool:
    """Strict validation rejecting absolute paths, drive letters, UNC, empty components, and traversals."""
    if not isinstance(path_str, str):
        failures.append(f"Path at '{context}' must be a string.")
        return False
    if "\\" in path_str:
        failures.append(
            f"Unsafe path rejected at '{context}': contains backslashes ('{path_str}'). Must use portable forward slashes."
        )
        return False
    if re.search(r"^[a-zA-Z]:", path_str):
        failures.append(f"Unsafe path rejected at '{context}': Windows drive path ('{path_str}').")
        return False
    if path_str.startswith("//"):
        failures.append(f"Unsafe path rejected at '{context}': UNC path ('{path_str}').")
        return False
    if path_str.startswith("/"):
        failures.append(
            f"Unsafe path rejected at '{context}': leading slash / absolute path ('{path_str}')."
        )
        return False

    parts = path_str.split("/")
    if any(part == "" for part in parts):
        failures.append(
            f"Unsafe path rejected at '{context}': empty path component in ('{path_str}')."
        )
        return False
    if any(part in (".", "..") for part in parts):
        failures.append(
            f"Unsafe path rejected at '{context}': path traversal component in ('{path_str}')."
        )
        return False

    posix_p = PurePosixPath(path_str)
    if posix_p.is_absolute():
        failures.append(f"Unsafe path rejected at '{context}': absolute path ('{path_str}').")
        return False
    if any(part in (".", "..") for part in posix_p.parts):
        failures.append(
            f"Unsafe path rejected at '{context}': path traversal component in PurePosixPath ('{path_str}')."
        )
        return False

    return True


def safe_resolve_under(
    base_root: Path, rel_subpath: str, context: str, failures: list[str]
) -> Path | None:
    """Resolve rel_subpath under base_root, strictly preventing path escape and outside symlinks."""
    if not validate_safe_relative_path(rel_subpath, context, failures):
        return None
    try:
        resolved_base = base_root.resolve()
        candidate = (base_root / rel_subpath).resolve()
        candidate.relative_to(resolved_base)
        return candidate
    except ValueError:
        failures.append(
            f"Path escape detected at '{context}': '{rel_subpath}' resolves outside root '{base_root}'."
        )
        return None
    except Exception as exc:
        failures.append(f"Error resolving path at '{context}': {exc}")
        return None


def check_for_absolute_paths(obj: Any, failures: list[str], path_context: str = "") -> None:
    """Recursively ensure no machine-specific absolute paths exist in lock data structure."""
    if isinstance(obj, str):
        if ABSOLUTE_PATH_PATTERN.search(obj.strip()) or "\\" in obj:
            if "\\" in obj and not obj.startswith("http"):
                failures.append(
                    f"Machine-specific path or backslash rejected in lock at '{path_context}': '{obj}'"
                )
            elif ABSOLUTE_PATH_PATTERN.search(obj.strip()):
                failures.append(
                    f"Machine-specific absolute path rejected in lock at '{path_context}': '{obj}'"
                )
    elif isinstance(obj, dict):
        for k, v in obj.items():
            new_ctx = f"{path_context}.{k}" if path_context else k
            if isinstance(k, str) and (ABSOLUTE_PATH_PATTERN.search(k.strip()) or "\\" in k):
                failures.append(
                    f"Machine-specific absolute path rejected in lock key at '{new_ctx}': '{k}'"
                )
            check_for_absolute_paths(v, failures, new_ctx)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            check_for_absolute_paths(item, failures, f"{path_context}[{idx}]")


def validate_lock_schema(lock_data: dict[str, Any], failures: list[str]) -> None:
    """Validate that lock_data strictly adheres to the required schema."""
    if not isinstance(lock_data, dict):
        failures.append("Lock file root must be a JSON object.")
        return

    # Check for machine-specific absolute paths
    check_for_absolute_paths(lock_data, failures, "root")

    # 1. Root-level key enforcement
    root_keys = set(lock_data.keys())
    unexpected_root = root_keys - ALLOWED_ROOT_KEYS
    if unexpected_root:
        failures.append(f"Unexpected root field(s) in lock file: {sorted(unexpected_root)}.")
    missing_root = ALLOWED_ROOT_KEYS - root_keys
    if missing_root:
        failures.append(f"Missing root field(s) in lock file: {sorted(missing_root)}.")

    schema_version = lock_data.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        failures.append(
            f"Lock 'schema_version' must exactly equal '{SCHEMA_VERSION}', got '{schema_version}'."
        )

    # 2. Source-level key enforcement
    source = lock_data.get("source")
    if not isinstance(source, dict):
        failures.append("Lock file missing 'source' object.")
    else:
        src_keys = set(source.keys())
        unexpected_src = src_keys - ALLOWED_SOURCE_KEYS
        if unexpected_src:
            failures.append(f"Unexpected source field(s) in lock file: {sorted(unexpected_src)}.")
        missing_src = ALLOWED_SOURCE_KEYS - src_keys
        if missing_src:
            failures.append(f"Missing source field(s) in lock file: {sorted(missing_src)}.")

        src_name = source.get("name")
        if src_name != SOURCE_NAME:
            failures.append(
                f"Lock 'source.name' must exactly equal '{SOURCE_NAME}', got '{src_name}'."
            )

        repo_url = source.get("repository_url")
        if repo_url != CANONICAL_REPO_URL:
            failures.append(
                f"Lock 'source.repository_url' must match canonical URL '{CANONICAL_REPO_URL}', got '{repo_url}'."
            )

        pinned = source.get("pinned_commit")
        if not isinstance(pinned, str) or not COMMIT_SHA_PATTERN.match(pinned):
            failures.append(
                f"Lock 'source.pinned_commit' must be an exact 40-character lowercase git commit SHA, got '{pinned}'."
            )
        elif pinned != CANONICAL_PINNED_COMMIT:
            failures.append(
                f"Lock 'source.pinned_commit' must exactly match canonical pinned commit '{CANONICAL_PINNED_COMMIT}', got '{pinned}'."
            )

        declared_ver = source.get("declared_version")
        if declared_ver != DECLARED_VERSION:
            failures.append(
                f"Lock 'source.declared_version' must match '{DECLARED_VERSION}', got '{declared_ver}'."
            )

        license_val = source.get("license")
        if license_val != DECLARED_LICENSE:
            failures.append(
                f"Lock 'source.license' must match '{DECLARED_LICENSE}', got '{license_val}'."
            )

    # 3. Skills-level key enforcement
    skills = lock_data.get("skills")
    if not isinstance(skills, dict):
        failures.append("Lock file missing 'skills' object.")
        return

    unexpected_skills = set(skills.keys()) - set(REQUIRED_SKILLS)
    if unexpected_skills:
        failures.append(f"Unexpected skill entry in lock file: {sorted(unexpected_skills)}.")

    missing_skills = set(REQUIRED_SKILLS) - set(skills.keys())
    if missing_skills:
        for ms in sorted(missing_skills):
            failures.append(f"Required external skill '{ms}' is missing from lock file.")

    for required_skill in REQUIRED_SKILLS:
        if required_skill not in skills:
            continue

        skill_entry = skills[required_skill]
        if not isinstance(skill_entry, dict):
            failures.append(f"Lock skill entry '{required_skill}' must be an object.")
            continue

        sk_keys = set(skill_entry.keys())
        unexpected_sk_keys = sk_keys - ALLOWED_SKILL_KEYS
        if unexpected_sk_keys:
            failures.append(
                f"Unexpected skill field(s) in '{required_skill}': {sorted(unexpected_sk_keys)}."
            )
        missing_sk_keys = ALLOWED_SKILL_KEYS - sk_keys
        if missing_sk_keys:
            failures.append(
                f"Missing skill field(s) in '{required_skill}': {sorted(missing_sk_keys)}."
            )

        file_count = skill_entry.get("file_count")
        if file_count is None or not isinstance(file_count, int) or file_count < 0:
            failures.append(
                f"Skill '{required_skill}' missing valid non-negative integer 'file_count'."
            )

        sk_ver = skill_entry.get("declared_version")
        if sk_ver != DECLARED_VERSION:
            failures.append(
                f"Skill '{required_skill}' declared_version must match '{DECLARED_VERSION}'."
            )

        sk_lic = skill_entry.get("license")
        if sk_lic != DECLARED_LICENSE:
            failures.append(f"Skill '{required_skill}' license must match '{DECLARED_LICENSE}'.")

        upstream = skill_entry.get("upstream_subpath")
        if isinstance(upstream, str):
            validate_safe_relative_path(upstream, f"skills.{required_skill}.upstream_subpath", failures)

        installed = skill_entry.get("installed_subpath")
        if isinstance(installed, str):
            validate_safe_relative_path(
                installed, f"skills.{required_skill}.installed_subpath", failures
            )

        files = skill_entry.get("files")
        if not isinstance(files, dict) or len(files) == 0:
            failures.append(f"Skill '{required_skill}' has no file manifest entries in lock.")
            continue

        if file_count is not None and isinstance(file_count, int) and file_count != len(files):
            failures.append(
                f"Skill '{required_skill}' file_count ({file_count}) does not match manifest length ({len(files)})."
            )

        for rel_file, file_meta in files.items():
            validate_safe_relative_path(
                rel_file, f"skills.{required_skill}.files.{rel_file}", failures
            )
            if not isinstance(file_meta, dict):
                failures.append(
                    f"Skill '{required_skill}' file metadata for '{rel_file}' must be an object."
                )
                continue

            fm_keys = set(file_meta.keys())
            unexpected_fm = fm_keys - ALLOWED_FILE_META_KEYS
            if unexpected_fm:
                failures.append(
                    f"Unexpected file-metadata field(s) in '{required_skill}.files.{rel_file}': {sorted(unexpected_fm)}."
                )
            missing_fm = ALLOWED_FILE_META_KEYS - fm_keys
            if missing_fm:
                failures.append(
                    f"Missing file-metadata field(s) in '{required_skill}.files.{rel_file}': {sorted(missing_fm)}."
                )

            sha = file_meta.get("sha256")
            if not sha or not isinstance(sha, str) or not SHA256_HEX_PATTERN.match(sha):
                failures.append(
                    f"Skill '{required_skill}' file '{rel_file}' missing valid 64-char lowercase hex 'sha256'."
                )
            size = file_meta.get("size")
            if size is None or not isinstance(size, int) or size < 0:
                failures.append(
                    f"Skill '{required_skill}' file '{rel_file}' missing valid non-negative integer 'size'."
                )


def compute_file_sha256(path: Path) -> tuple[str, int]:
    """Strict read-only calculation of SHA-256 and size in bytes."""
    h = hashlib.sha256()
    size = 0
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def scan_directory(
    dir_path: Path, root_boundary: Path, failures: list[str]
) -> dict[str, tuple[str, int]]:
    """Scan all non-ignored files in dir_path, ensuring no symlinks exist and no escapes occur."""
    results: dict[str, tuple[str, int]] = {}
    resolved_boundary = root_boundary.resolve()

    if dir_path.is_symlink():
        failures.append(
            f"Symlink rejected: Skill directory '{dir_path}' is a symlink. Symlinks are prohibited in external skills."
        )
        return results

    try:
        dir_path.resolve().relative_to(resolved_boundary)
    except ValueError:
        failures.append(
            f"Symlink escape detected: Skill directory '{dir_path}' resolves outside boundary '{root_boundary}'."
        )
        return results

    def _walk_dir(current_dir: Path):
        try:
            entries = sorted(current_dir.iterdir(), key=lambda x: x.name)
        except Exception as exc:
            failures.append(f"Error accessing directory '{current_dir}': {exc}")
            return

        for p in entries:
            # 1. Check and reject p.is_symlink() before any is_file/is_dir filtering
            if p.is_symlink():
                is_dir_sym = False
                try:
                    is_dir_sym = p.is_dir()
                except Exception:
                    pass
                if is_dir_sym:
                    failures.append(
                        f"Symlink rejected: '{p}' is a symlinked directory. Symlinks are prohibited in external skills."
                    )
                else:
                    failures.append(
                        f"Symlink rejected: '{p}' is a symlink. Symlinks are prohibited in external skills."
                    )
                # Do not follow or process symlinks
                continue

            # 2. Verify path resolves within boundary
            try:
                resolved_p = p.resolve()
                resolved_p.relative_to(resolved_boundary)
            except ValueError:
                failures.append(
                    f"Symlink escape detected: '{p}' resolves outside skill boundary '{root_boundary}'."
                )
                continue

            # 3. Recurse into real directories (never follow symlink directories)
            if p.is_dir():
                rel_d = p.relative_to(dir_path)
                if any(part in IGNORED_DIRS or part.startswith(".git") for part in rel_d.parts):
                    continue
                _walk_dir(p)
            elif p.is_file():
                rel = p.relative_to(dir_path)
                if is_ignored(p, rel):
                    continue
                posix_rel = rel.as_posix()
                sha256, size = compute_file_sha256(p)
                results[posix_rel] = (sha256, size)

    _walk_dir(dir_path)
    return results


def resolve_skill_dir(
    root: Path, installed_subpath: str, skill_name: str, failures: list[str]
) -> Path | None:
    """Resolve installed skill directory supporting both root/.codex and root/skills structures."""
    raw_path = root / installed_subpath
    if raw_path.is_symlink():
        failures.append(
            f"Symlink rejected: Installed skill root '{raw_path}' for '{skill_name}' is a symlink. Symlinks are prohibited in external skills."
        )
        return None

    safe_path = safe_resolve_under(
        root, installed_subpath, f"installed_subpath.{skill_name}", failures
    )
    if safe_path is not None and safe_path.is_dir():
        if safe_path.is_symlink():
            failures.append(
                f"Symlink rejected: Installed skill root '{safe_path}' for '{skill_name}' is a symlink. Symlinks are prohibited in external skills."
            )
            return None
        return safe_path

    raw_alt = root / skill_name
    if raw_alt.is_symlink():
        failures.append(
            f"Symlink rejected: Installed skill root '{raw_alt}' for '{skill_name}' is a symlink. Symlinks are prohibited in external skills."
        )
        return None

    safe_alt = safe_resolve_under(root, skill_name, f"skill_name.{skill_name}", failures)
    if safe_alt is not None and safe_alt.is_dir():
        if safe_alt.is_symlink():
            failures.append(
                f"Symlink rejected: Installed skill root '{safe_alt}' for '{skill_name}' is a symlink. Symlinks are prohibited in external skills."
            )
            return None
        return safe_alt
    return None


def verify_skills(
    lock_file: Path,
    installed_root: Path | None = None,
    source_root: Path | None = None,
    source_commit: str | None = None,
    diagnostic: bool = False,
    verbose: bool = False,
) -> tuple[int, list[str], dict[str, Any]]:
    """
    Run complete external skill provenance verification.

    Returns:
      (exit_code, failures, summary)
      exit_code:
        0 = FULL GATE PASS (source-root validated + installed skills match)
        1 = VERIFICATION FAILURE (mismatch, missing files, schema error, etc.)
        2 = DIAGNOSTIC PASS / SOURCE UNVERIFIED (installed matches, but source-root was omitted)
    """
    failures: list[str] = []
    summary: dict[str, Any] = {
        "skills": {},
        "matched_files": 0,
        "total_expected_files": 0,
        "source_verified": False,
        "mode": "FULL_GATE" if (source_root is not None and not diagnostic) else "DIAGNOSTIC",
        "source_verification_reason": (
            "diagnostic mode was requested" if diagnostic else
            "source root was not provided" if source_root is None else ""
        ),
    }

    if not lock_file.exists():
        failures.append(f"Lock file not found: '{lock_file}'")
        return 1, failures, summary

    try:
        raw_text = lock_file.read_text(encoding="utf-8")
        lock_data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        failures.append(f"Lock file is malformed JSON: {exc}")
        return 1, failures, summary
    except Exception as exc:
        failures.append(f"Failed to read lock file: {exc}")
        return 1, failures, summary

    validate_lock_schema(lock_data, failures)
    if failures:
        return 1, failures, summary

    source_info = lock_data["source"]
    pinned_commit = source_info["pinned_commit"].strip()
    summary["pinned_commit"] = pinned_commit
    summary["repository_url"] = source_info["repository_url"]

    # 1. Source root verification
    is_git = False
    if source_root is not None and not diagnostic:
        summary["source_root"] = str(source_root)
        if not source_root.exists() or not source_root.is_dir():
            failures.append(f"Specified source root does not exist: '{source_root}'")
            summary["source_verification_reason"] = "specified source root does not exist or is not a directory"
        else:
            is_git = (source_root / ".git").exists()
            if is_git:
                # Confirm HEAD resolves to the pinned commit
                res_head = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=source_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if res_head.returncode != 0:
                    failures.append(
                        f"Failed to resolve HEAD in git repository at '{source_root}': {res_head.stderr.strip()}"
                    )
                else:
                    head_sha = res_head.stdout.strip().lower()
                    if head_sha != pinned_commit.lower():
                        failures.append(
                            f"Reference source Git HEAD mismatch: expected '{pinned_commit}', got '{head_sha}'"
                        )

                # Enumerate the exact committed tree using: git ls-tree -r --name-only <pinned_commit> <upstream_subpath>
                for skill_name, skill_meta in lock_data["skills"].items():
                    upstream_sub = skill_meta["upstream_subpath"]
                    res_tree = subprocess.run(
                        ["git", "ls-tree", "-r", "--name-only", pinned_commit, upstream_sub],
                        cwd=source_root,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if res_tree.returncode != 0:
                        failures.append(
                            f"Failed to query git tree for '{skill_name}' at commit '{pinned_commit}': {res_tree.stderr.strip()}"
                        )
                        continue

                    git_tree_files: set[str] = set()
                    for raw_line in res_tree.stdout.strip().splitlines():
                        line = raw_line.strip()
                        if not line:
                            continue
                        if line.startswith(upstream_sub):
                            rel_f = line[len(upstream_sub) :].lstrip("/")
                        else:
                            rel_f = line

                        if is_ignored(Path(line), Path(rel_f)):
                            continue
                        git_tree_files.add(rel_f)

                    expected_files = set(skill_meta["files"].keys())

                    # Unexpected in Git tree
                    unexpected_in_source = git_tree_files - expected_files
                    for unf in sorted(unexpected_in_source):
                        failures.append(
                            f"UNEXPECTED_SOURCE_FILE: [{skill_name}] '{unf}' exists in source Git tree at '{pinned_commit}' but is omitted from lock manifest."
                        )

                    # Missing in Git tree
                    missing_in_source = expected_files - git_tree_files
                    for misf in sorted(missing_in_source):
                        failures.append(
                            f"MISSING_SOURCE_FILE: [{skill_name}] '{misf}' in lock manifest not found in source Git tree at '{pinned_commit}'."
                        )

                    # Content comparison from canonical git blobs
                    for f in sorted(expected_files & git_tree_files):
                        exp_meta = skill_meta["files"][f]
                        blob_path = f"{upstream_sub}/{f}"
                        cat_res = subprocess.run(
                            ["git", "cat-file", "-p", f"{pinned_commit}:{blob_path}"],
                            cwd=source_root,
                            capture_output=True,
                            check=False,
                        )
                        if cat_res.returncode != 0:
                            failures.append(
                                f"Failed to read git blob for [{skill_name}] '{blob_path}' at commit '{pinned_commit}'"
                            )
                            continue
                        blob_bytes = cat_res.stdout
                        blob_sha = hashlib.sha256(blob_bytes).hexdigest()
                        blob_size = len(blob_bytes)
                        if blob_sha != exp_meta["sha256"]:
                            failures.append(
                                f"MODIFIED_SOURCE_FILE: [{skill_name}] '{f}' hash mismatch in source Git tree (expected {exp_meta['sha256']}, got {blob_sha})"
                            )
                        if blob_size != exp_meta["size"]:
                            failures.append(
                                f"MODIFIED_SOURCE_FILE: [{skill_name}] '{f}' size mismatch in source Git tree (expected {exp_meta['size']}, got {blob_size})"
                            )

            else:
                # A non-Git tree can support diagnostic byte comparison, but it
                # cannot prove immutable commit/tree provenance for the full gate.
                summary["mode"] = "DIAGNOSTIC"
                summary["source_verification_reason"] = (
                    "source root is not a Git repository; full provenance requires "
                    "git HEAD, ls-tree, and cat-file verification"
                )
                marker_path = source_root / ".git-commit"
                if source_commit:
                    found_commit = source_commit.strip().lower()
                elif marker_path.exists() and marker_path.is_file():
                    found_commit = marker_path.read_text(encoding="utf-8").strip().lower()
                else:
                    failures.append(
                        f"Non-Git offline source root at '{source_root}' missing required '.git-commit' marker matching pinned commit."
                    )
                    found_commit = None

                if found_commit and found_commit != pinned_commit.lower():
                    failures.append(
                        f"Reference source commit mismatch: expected '{pinned_commit}', got '{found_commit}'"
                    )

                for skill_name, skill_meta in lock_data["skills"].items():
                    raw_src_dir = source_root / skill_meta["upstream_subpath"]
                    if raw_src_dir.is_symlink():
                        failures.append(
                            f"Symlink rejected: Source skill root '{raw_src_dir}' for '{skill_name}' is a symlink. Symlinks are prohibited in external skills."
                        )
                        continue

                    src_skill_dir = safe_resolve_under(
                        source_root,
                        skill_meta["upstream_subpath"],
                        f"source_subpath.{skill_name}",
                        failures,
                    )
                    if src_skill_dir is None or not src_skill_dir.is_dir():
                        failures.append(
                            f"Source skill directory '{skill_meta['upstream_subpath']}' not found in source root."
                        )
                        continue

                    if src_skill_dir.is_symlink():
                        failures.append(
                            f"Symlink rejected: Source skill root '{src_skill_dir}' for '{skill_name}' is a symlink. Symlinks are prohibited in external skills."
                        )
                        continue

                    src_files = scan_directory(src_skill_dir, src_skill_dir, failures)
                    expected_files_dict = skill_meta["files"]

                    for act_p in sorted(set(src_files.keys()) - set(expected_files_dict.keys())):
                        failures.append(
                            f"UNEXPECTED_SOURCE_FILE: [{skill_name}] '{act_p}' exists in source directory but is omitted from lock manifest."
                        )
                    for exp_p in sorted(set(expected_files_dict.keys()) - set(src_files.keys())):
                        failures.append(
                            f"MISSING_SOURCE_FILE: [{skill_name}] '{exp_p}' in lock manifest not found in source directory."
                        )
                    for common_p in sorted(set(expected_files_dict.keys()) & set(src_files.keys())):
                        act_sha, act_size = src_files[common_p]
                        exp_m = expected_files_dict[common_p]
                        if act_sha != exp_m["sha256"]:
                            failures.append(
                                f"MODIFIED_SOURCE_FILE: [{skill_name}] '{common_p}' hash mismatch in source directory (expected {exp_m['sha256']}, got {act_sha})"
                            )
                        if act_size != exp_m["size"]:
                            failures.append(
                                f"MODIFIED_SOURCE_FILE: [{skill_name}] '{common_p}' size mismatch in source directory (expected {exp_m['size']}, got {act_size})"
                            )

        if is_git and not failures:
            summary["source_verified"] = True

    # 2. Installed skills verification
    if installed_root is None:
        codex_home_env = os.environ.get("CODEX_HOME")
        if codex_home_env:
            installed_root = Path(codex_home_env)
        else:
            installed_root = Path.home() / ".codex"

    summary["installed_root"] = str(installed_root)

    for skill_name in REQUIRED_SKILLS:
        skill_meta = lock_data["skills"][skill_name]
        expected_files = skill_meta["files"]
        summary["total_expected_files"] += len(expected_files)

        skill_dir = resolve_skill_dir(
            installed_root, skill_meta["installed_subpath"], skill_name, failures
        )
        if skill_dir is None:
            is_symlink_fail = any("Installed skill root" in f and skill_name in f for f in failures)
            if not is_symlink_fail:
                failures.append(
                    f"MISSING_INSTALLED_SKILL: '{skill_name}' not found in '{installed_root}' "
                    f"(expected under '{skill_meta['installed_subpath']}')."
                )
            summary["skills"][skill_name] = {
                "status": "FAIL" if is_symlink_fail else "MISSING",
                "matched": 0,
                "total": len(expected_files),
            }
            continue

        if skill_dir.is_symlink():
            failures.append(
                f"Symlink rejected: Installed skill root '{skill_dir}' for '{skill_name}' is a symlink. Symlinks are prohibited in external skills."
            )
            summary["skills"][skill_name] = {
                "status": "FAIL",
                "matched": 0,
                "total": len(expected_files),
            }
            continue

        failures_before = len(failures)
        actual_files = scan_directory(skill_dir, skill_dir, failures)
        matched_in_skill = 0
        skill_errors: list[str] = list(failures[failures_before:])

        # Missing files
        for exp_p, exp_m in expected_files.items():
            if exp_p not in actual_files:
                err = f"MISSING_FILE: [{skill_name}] '{exp_p}' not found on disk."
                failures.append(err)
                skill_errors.append(err)
            else:
                act_sha, act_size = actual_files[exp_p]
                if act_sha != exp_m["sha256"]:
                    err = (
                        f"MODIFIED_FILE: [{skill_name}] '{exp_p}' content modified "
                        f"(expected {exp_m['sha256'][:12]}..., actual {act_sha[:12]}...)"
                    )
                    failures.append(err)
                    skill_errors.append(err)
                elif act_size != exp_m["size"]:
                    err = (
                        f"MODIFIED_FILE: [{skill_name}] '{exp_p}' size mismatch "
                        f"(expected {exp_m['size']} bytes, actual {act_size} bytes)"
                    )
                    failures.append(err)
                    skill_errors.append(err)
                else:
                    matched_in_skill += 1

        # Unexpected files
        for act_p in actual_files:
            if act_p not in expected_files:
                err = f"UNEXPECTED_FILE: [{skill_name}] '{act_p}' is not in locked manifest."
                failures.append(err)
                skill_errors.append(err)

        summary["matched_files"] += matched_in_skill
        summary["skills"][skill_name] = {
            "status": "PASS" if not skill_errors else "FAIL",
            "matched": matched_in_skill,
            "total": len(expected_files),
            "errors": skill_errors,
        }

    # Determine final exit status and gate outcome
    if failures:
        return 1, failures, summary

    if not summary["source_verified"]:
        # Diagnostic mode passed installed checks, but full provenance was not established
        return 2, failures, summary

    return 0, failures, summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify external skill provenance against immutable lock manifest."
    )
    parser.add_argument(
        "--lock-file",
        type=Path,
        default=Path("docs/engineering/EXTERNAL_SKILLS_LOCK.json"),
        help="Path to EXTERNAL_SKILLS_LOCK.json (default: docs/engineering/EXTERNAL_SKILLS_LOCK.json)",
    )
    parser.add_argument(
        "--installed-root",
        type=Path,
        default=None,
        help="Root path where skills are installed (defaults to CODEX_HOME or ~/.codex)",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=None,
        help="Local reference clone of the upstream repository at pinned commit",
    )
    parser.add_argument(
        "--source-commit",
        type=str,
        default=None,
        help="Optional diagnostic assertion for a non-Git source; never establishes the full gate",
    )
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="Run in diagnostic mode (inspect installed skills without requiring source-root)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Display verbose details for all files",
    )
    args = parser.parse_args()

    exit_code, failures, summary = verify_skills(
        lock_file=args.lock_file,
        installed_root=args.installed_root,
        source_root=args.source_root,
        source_commit=args.source_commit,
        diagnostic=args.diagnostic,
        verbose=args.verbose,
    )

    print("=" * 72)
    print("DENTIX EXTERNAL SKILL PROVENANCE VERIFIER")
    print("=" * 72)
    mode_str = "FULL GATE (source-root + installed-tree)" if summary.get("source_verified") else "DIAGNOSTIC ONLY (source unverified)"
    print(f"Mode:                    {mode_str}")
    if "pinned_commit" in summary:
        print(f"Locked Canonical Source: {summary.get('repository_url')}")
        print(f"Pinned Immutable Commit: {summary.get('pinned_commit')}")
    if "source_root" in summary:
        print(f"Reference Source Root:   {summary.get('source_root')}")
    if "installed_root" in summary:
        print(f"Installed Root Location: {summary.get('installed_root')}")
    print("-" * 72)

    for skill_name, sk_info in summary.get("skills", {}).items():
        st = sk_info["status"]
        matched = sk_info["matched"]
        total = sk_info["total"]
        print(f"[{st}] {skill_name}: {matched}/{total} files verified")

    print("-" * 72)
    if exit_code == 0:
        print("[PASS] EXTERNAL_SKILL_PROVENANCE = PASS")
        print("  - Pinned upstream source commit and tree verified.")
        print("  - Installed skills match lock manifest byte-for-byte.")
        print("=" * 72)
        return 0
    elif exit_code == 2:
        print("[DIAGNOSTIC] Installed skill inspection completed.")
        print(
            "WARNING: Full provenance was NOT established because "
            f"{summary.get('source_verification_reason', 'the source was not Git-verified')}."
        )
        print("EXTERNAL_SKILL_PROVENANCE gate CANNOT pass without source verification against pinned commit.")
        print("Run full verification with:")
        print("  python scripts/verify_external_skills.py --source-root <path-to-pinned-source-repo>")
        print("=" * 72)
        return 2

    print(f"[FAIL] Provenance verification failed with {len(failures)} violation(s):")
    for idx, f in enumerate(failures, 1):
        print(f"  {idx}. {f}")
    print("=" * 72)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
