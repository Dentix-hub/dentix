"""
backend/tests/test_external_skill_provenance.py
================================================
Targeted, deterministic automated test suite for external skill provenance lock and verifier.
Validates all required failure and success modes without depending on live network access.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VERIFIER_SCRIPT = REPO_ROOT / "scripts" / "verify_external_skills.py"

# Import verifier module dynamically
spec = importlib.util.spec_from_file_location("verify_external_skills", VERIFIER_SCRIPT)
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load verifier from {VERIFIER_SCRIPT}")
verifier_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier_mod)
verify_skills = verifier_mod.verify_skills
safe_resolve_under = verifier_mod.safe_resolve_under
scan_directory = verifier_mod.scan_directory

CANONICAL_PINNED_COMMIT = "b781ee2e23089630e2fbee1cfd6174afe4edeb76"
CANONICAL_REPO_URL = "https://github.com/amElnagdy/delegate-skills.git"

SAMPLE_SKILL_FILES: dict[str, dict[str, bytes]] = {
    "delegate-setup": {
        "SKILL.md": b"---\nname: delegate-setup\ndescription: setup lanes\n---\n# Setup\n",
        "references/schema.md": b"# Schema Reference\n",
        "scripts/config.mjs": b"// config script\nexport const config = {};\n",
    },
    "agy-delegate": {
        "SKILL.md": b"---\nname: agy-delegate\ndescription: delegate to agy\n---\n# AGY\n",
        "references/dispatch-and-poll.md": b"# Dispatch and Poll\n",
        "scripts/relay.mjs": b"// agy relay\n",
    },
    "codex-delegate": {
        "SKILL.md": b"---\nname: codex-delegate\ndescription: delegate to codex\n---\n# Codex\n",
        "references/dispatch-and-poll.md": b"# Codex Dispatch\n",
        "scripts/relay.mjs": b"// codex relay\n",
    },
}


def build_lock_dict(files_dict: dict[str, dict[str, bytes]]) -> dict[str, Any]:
    """Construct deterministic lock JSON data from provided skill file bytes."""
    lock_data: dict[str, Any] = {
        "schema_version": "1.0.0",
        "source": {
            "name": "delegate-skills",
            "repository_url": CANONICAL_REPO_URL,
            "pinned_commit": CANONICAL_PINNED_COMMIT,
            "license": "MIT",
            "declared_version": "0.5.0",
        },
        "skills": {},
    }
    for skill_name, files in files_dict.items():
        skill_manifest: dict[str, Any] = {}
        for rel_path, data in files.items():
            skill_manifest[rel_path] = {
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            }
        lock_data["skills"][skill_name] = {
            "upstream_subpath": f"skills/{skill_name}",
            "installed_subpath": f"skills/{skill_name}",
            "declared_version": "0.5.0",
            "license": "MIT",
            "file_count": len(skill_manifest),
            "files": skill_manifest,
        }
    return lock_data


def populate_fixture(
    root: Path,
    files_dict: dict[str, dict[str, bytes]],
    lock_data: dict[str, Any] | None = None,
) -> tuple[Path, Path, Path]:
    """Create lock file, installed skills tree, and source root tree in fixture root."""
    lock_file = root / "EXTERNAL_SKILLS_LOCK.json"
    if lock_data is None:
        lock_data = build_lock_dict(files_dict)
    lock_file.write_text(json.dumps(lock_data, indent=2), encoding="utf-8")

    installed_root = root / "installed"
    for skill_name, files in files_dict.items():
        skill_dir = installed_root / "skills" / skill_name
        for rel_path, content in files.items():
            f_path = skill_dir / rel_path
            f_path.parent.mkdir(parents=True, exist_ok=True)
            f_path.write_bytes(content)

    source_root = root / "source"
    source_root.mkdir(parents=True, exist_ok=True)
    (source_root / ".git-commit").write_text(CANONICAL_PINNED_COMMIT, encoding="utf-8")
    for skill_name, files in files_dict.items():
        src_skill_dir = source_root / "skills" / skill_name
        for rel_path, content in files.items():
            f_path = src_skill_dir / rel_path
            f_path.parent.mkdir(parents=True, exist_ok=True)
            f_path.write_bytes(content)

    return lock_file, installed_root, source_root


@pytest.fixture
def provenance_fixture():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        lock_file, installed_root, source_root = populate_fixture(root, SAMPLE_SKILL_FILES)
        yield {
            "root": root,
            "lock_file": lock_file,
            "installed_root": installed_root,
            "source_root": source_root,
        }


# 1. Exact match passes in full-gate mode
def test_exact_match_passes(provenance_fixture):
    code, failures, summary = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
        source_root=provenance_fixture["source_root"],
    )
    assert code == 0, f"Expected 0, got failures: {failures}"
    assert len(failures) == 0
    assert summary["source_verified"] is True
    assert summary["skills"]["delegate-setup"]["status"] == "PASS"
    assert summary["skills"]["agy-delegate"]["status"] == "PASS"
    assert summary["skills"]["codex-delegate"]["status"] == "PASS"


# 2. Changed file fails
def test_changed_file_fails(provenance_fixture):
    modified_file = (
        provenance_fixture["installed_root"]
        / "skills"
        / "codex-delegate"
        / "scripts"
        / "relay.mjs"
    )
    modified_file.write_bytes(b"// modified content with unexpected hash\n")

    code, failures, summary = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
        source_root=provenance_fixture["source_root"],
    )
    assert code == 1
    assert any("MODIFIED_FILE" in f and "codex-delegate" in f and "relay.mjs" in f for f in failures)
    assert summary["skills"]["codex-delegate"]["status"] == "FAIL"


# 3. Missing file fails
def test_missing_file_fails(provenance_fixture):
    target = (
        provenance_fixture["installed_root"]
        / "skills"
        / "agy-delegate"
        / "references"
        / "dispatch-and-poll.md"
    )
    target.unlink()

    code, failures, summary = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
        source_root=provenance_fixture["source_root"],
    )
    assert code == 1
    assert any("MISSING_FILE" in f and "agy-delegate" in f and "dispatch-and-poll.md" in f for f in failures)
    assert summary["skills"]["agy-delegate"]["status"] == "FAIL"


# 4. Unexpected file fails
def test_unexpected_file_fails(provenance_fixture):
    unexpected = (
        provenance_fixture["installed_root"]
        / "skills"
        / "delegate-setup"
        / "unexpected_script.sh"
    )
    unexpected.write_bytes(b"echo unexpected\n")

    # Add an ignored file that should NOT cause failure
    ignored = (
        provenance_fixture["installed_root"]
        / "skills"
        / "delegate-setup"
        / ".DS_Store"
    )
    ignored.write_bytes(b"dummy metadata\n")

    code, failures, summary = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
        source_root=provenance_fixture["source_root"],
    )
    assert code == 1
    assert any("UNEXPECTED_FILE" in f and "delegate-setup" in f and "unexpected_script.sh" in f for f in failures)
    assert not any(".DS_Store" in f for f in failures)


# 5. Missing installed skill fails
def test_missing_installed_skill_fails(provenance_fixture):
    skill_dir = provenance_fixture["installed_root"] / "skills" / "codex-delegate"
    shutil.rmtree(skill_dir)

    code, failures, summary = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
        source_root=provenance_fixture["source_root"],
    )
    assert code == 1
    assert any("MISSING_INSTALLED_SKILL" in f and "codex-delegate" in f for f in failures)
    assert summary["skills"]["codex-delegate"]["status"] == "MISSING"


# 6. Malformed lock fails
def test_malformed_lock_fails(provenance_fixture):
    provenance_fixture["lock_file"].write_text("{ unclosed json", encoding="utf-8")
    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
    )
    assert code == 1
    assert any("malformed json" in f.lower() for f in failures)

    valid_data = build_lock_dict(SAMPLE_SKILL_FILES)
    del valid_data["schema_version"]
    provenance_fixture["lock_file"].write_text(json.dumps(valid_data), encoding="utf-8")
    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
    )
    assert code == 1
    assert any("schema_version" in f for f in failures)


# 7. Incorrect pinned source commit fails
def test_incorrect_pinned_source_commit_fails(provenance_fixture):
    (provenance_fixture["source_root"] / ".git-commit").write_text(
        "1111111111111111111111111111111111111111", encoding="utf-8"
    )

    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
        source_root=provenance_fixture["source_root"],
    )
    assert code == 1
    assert any("commit mismatch" in f.lower() for f in failures)


# 8. All three required skill mappings are enforced
def test_all_three_required_skill_mappings_are_enforced(provenance_fixture):
    lock_data = build_lock_dict(SAMPLE_SKILL_FILES)
    del lock_data["skills"]["codex-delegate"]
    provenance_fixture["lock_file"].write_text(json.dumps(lock_data), encoding="utf-8")

    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
    )
    assert code == 1
    assert any("codex-delegate" in f and "missing from lock" in f.lower() for f in failures)


# 9. Machine-specific absolute paths are rejected
def test_machine_specific_absolute_paths_are_rejected(provenance_fixture):
    lock_data = build_lock_dict(SAMPLE_SKILL_FILES)
    lock_data["skills"]["delegate-setup"]["installed_subpath"] = r"C:\Users\es\.codex\skills\delegate-setup"
    provenance_fixture["lock_file"].write_text(json.dumps(lock_data), encoding="utf-8")

    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
    )
    assert code == 1
    assert any("absolute path" in f.lower() or "unsafe path" in f.lower() for f in failures)


# 10. Verifier never writes into installed skill directories
def test_verifier_never_writes_into_installed_skill_directories(provenance_fixture):
    installed_root = provenance_fixture["installed_root"]

    def snapshot_dir(d: Path) -> dict[str, tuple[int, int]]:
        state: dict[str, tuple[int, int]] = {}
        for p in d.rglob("*"):
            if p.is_file():
                st = p.stat()
                state[str(p.relative_to(d))] = (st.st_size, st.st_mtime_ns)
        return state

    before_state = snapshot_dir(installed_root)
    assert len(before_state) > 0

    verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=installed_root,
        source_root=provenance_fixture["source_root"],
    )

    corrupted_file = installed_root / "skills" / "agy-delegate" / "SKILL.md"
    corrupted_file.write_bytes(b"corrupted")
    before_state[str(corrupted_file.relative_to(installed_root))] = (
        corrupted_file.stat().st_size,
        corrupted_file.stat().st_mtime_ns,
    )

    verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=installed_root,
    )

    after_state = snapshot_dir(installed_root)
    assert before_state == after_state, "Verifier modified installed skill directory files!"


# 11. Source contains an unexpected file omitted from the lock
def test_source_unexpected_file_omitted_from_lock_fails(provenance_fixture):
    extra_src = (
        provenance_fixture["source_root"]
        / "skills"
        / "delegate-setup"
        / "extra_omitted.mjs"
    )
    extra_src.write_bytes(b"// not in lock\n")

    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
        source_root=provenance_fixture["source_root"],
    )
    assert code == 1
    assert any("UNEXPECTED_SOURCE_FILE" in f and "extra_omitted.mjs" in f for f in failures)


# 12. file_count does not match manifest length
def test_file_count_mismatch_fails(provenance_fixture):
    lock_data = build_lock_dict(SAMPLE_SKILL_FILES)
    lock_data["skills"]["delegate-setup"]["file_count"] = 99
    provenance_fixture["lock_file"].write_text(json.dumps(lock_data), encoding="utf-8")

    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
    )
    assert code == 1
    assert any("file_count (99) does not match manifest length" in f for f in failures)


# 13. missing file_count
def test_missing_file_count_fails(provenance_fixture):
    lock_data = build_lock_dict(SAMPLE_SKILL_FILES)
    del lock_data["skills"]["delegate-setup"]["file_count"]
    provenance_fixture["lock_file"].write_text(json.dumps(lock_data), encoding="utf-8")

    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
    )
    assert code == 1
    assert any("missing valid non-negative integer 'file_count'" in f for f in failures)


# 14. ../ path traversal
def test_dot_dot_traversal_fails(provenance_fixture):
    lock_data = build_lock_dict(SAMPLE_SKILL_FILES)
    lock_data["skills"]["delegate-setup"]["installed_subpath"] = "../escaped/delegate-setup"
    provenance_fixture["lock_file"].write_text(json.dumps(lock_data), encoding="utf-8")

    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
    )
    assert code == 1
    assert any("path traversal component" in f.lower() or "unsafe path" in f.lower() for f in failures)


# 15. nested ../../ traversal
def test_nested_traversal_fails(provenance_fixture):
    lock_data = build_lock_dict(SAMPLE_SKILL_FILES)
    lock_data["skills"]["delegate-setup"]["files"]["references/../../escape.md"] = {
        "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
        "size": 10,
    }
    lock_data["skills"]["delegate-setup"]["file_count"] += 1
    provenance_fixture["lock_file"].write_text(json.dumps(lock_data), encoding="utf-8")

    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
    )
    assert code == 1
    assert any("path traversal component" in f.lower() or "unsafe path" in f.lower() for f in failures)


# 16. /root absolute path
def test_root_absolute_path_fails(provenance_fixture):
    lock_data = build_lock_dict(SAMPLE_SKILL_FILES)
    lock_data["skills"]["delegate-setup"]["upstream_subpath"] = "/root/skills/delegate-setup"
    provenance_fixture["lock_file"].write_text(json.dumps(lock_data), encoding="utf-8")

    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
    )
    assert code == 1
    assert any("absolute path" in f.lower() or "unsafe path" in f.lower() for f in failures)


# 17. UNC path
def test_unc_path_fails(provenance_fixture):
    lock_data = build_lock_dict(SAMPLE_SKILL_FILES)
    lock_data["skills"]["delegate-setup"]["installed_subpath"] = "//remote-server/share/skill"
    provenance_fixture["lock_file"].write_text(json.dumps(lock_data), encoding="utf-8")

    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
    )
    assert code == 1
    assert any("unc path" in f.lower() or "unsafe path" in f.lower() for f in failures)


# 18. installed path resolving outside installed_root
def test_installed_path_resolving_outside_installed_root_fails(provenance_fixture):
    failures: list[str] = []
    res = safe_resolve_under(
        provenance_fixture["installed_root"],
        "../../outside_dir",
        "test_installed_escape",
        failures,
    )
    assert res is None
    assert len(failures) > 0
    assert any("path traversal" in f.lower() or "unsafe path" in f.lower() for f in failures)


# 19. source path resolving outside source_root
def test_source_path_resolving_outside_source_root_fails(provenance_fixture):
    failures: list[str] = []
    res = safe_resolve_under(
        provenance_fixture["source_root"],
        "../outside_source",
        "test_source_escape",
        failures,
    )
    assert res is None
    assert len(failures) > 0
    assert any("path traversal" in f.lower() or "unsafe path" in f.lower() for f in failures)


# 20. source Git HEAD mismatch
def test_source_git_head_mismatch_fails():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        git_repo = tmp_path / "git_source_mismatch"
        git_repo.mkdir()
        subprocess.run(["git", "init"], cwd=git_repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=git_repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=git_repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "--allow-empty", "-m", "fresh commit"], cwd=git_repo, capture_output=True, check=True)

        lock_file, installed_root, _ = populate_fixture(tmp_path, SAMPLE_SKILL_FILES)
        code, failures, summary = verify_skills(
            lock_file=lock_file,
            installed_root=installed_root,
            source_root=git_repo,
        )
        assert code == 1
        assert any("Git HEAD mismatch" in f for f in failures)


# 21. source Git tree at the pinned commit contains an omitted file
def test_source_git_tree_contains_omitted_file_fails(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        git_repo = tmp_path / "git_source_tree"
        git_repo.mkdir()
        subprocess.run(["git", "init"], cwd=git_repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=git_repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=git_repo, capture_output=True, check=True)

        for skill_name, files in SAMPLE_SKILL_FILES.items():
            sk_dir = git_repo / "skills" / skill_name
            sk_dir.mkdir(parents=True, exist_ok=True)
            for rel_p, content in files.items():
                f_p = sk_dir / rel_p
                f_p.parent.mkdir(parents=True, exist_ok=True)
                f_p.write_bytes(content)

        omitted_file = git_repo / "skills" / "delegate-setup" / "omitted_tree_file.mjs"
        omitted_file.write_bytes(b"// committed in git tree but omitted from lock\n")

        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "commit with omitted file"], cwd=git_repo, capture_output=True, check=True)

        lock_file, installed_root, _ = populate_fixture(tmp_path, SAMPLE_SKILL_FILES)

        orig_run = subprocess.run

        def fake_git_run(cmd, *args, **kwargs):
            if isinstance(cmd, list) and len(cmd) >= 3 and cmd[:3] == ["git", "rev-parse", "HEAD"]:
                return subprocess.CompletedProcess(cmd, 0, stdout=CANONICAL_PINNED_COMMIT, stderr="")
            if isinstance(cmd, list) and len(cmd) >= 5 and cmd[:4] == ["git", "ls-tree", "-r", "--name-only"]:
                new_cmd = list(cmd)
                new_cmd[4] = "HEAD"
                return orig_run(new_cmd, *args, **kwargs)
            if isinstance(cmd, list) and len(cmd) >= 4 and cmd[:3] == ["git", "cat-file", "-p"]:
                new_cmd = list(cmd)
                target = new_cmd[3]
                if target.startswith(f"{CANONICAL_PINNED_COMMIT}:"):
                    new_cmd[3] = "HEAD:" + target[len(CANONICAL_PINNED_COMMIT) + 1 :]
                return orig_run(new_cmd, *args, **kwargs)
            return orig_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", fake_git_run)

        code, failures, summary = verify_skills(
            lock_file=lock_file,
            installed_root=installed_root,
            source_root=git_repo,
        )
        assert code == 1
        assert any("UNEXPECTED_SOURCE_FILE" in f and "omitted_tree_file.mjs" in f for f in failures)


# 22. installed-only execution cannot report the full provenance gate as PASS
def test_installed_only_execution_cannot_report_full_gate_pass(provenance_fixture):
    # API invocation without source_root
    code, failures, summary = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
        source_root=None,
    )
    assert code == 2  # Distinct exit status: DIAGNOSTIC_PASS_SOURCE_UNVERIFIED
    assert summary["source_verified"] is False
    assert summary["mode"] == "DIAGNOSTIC"
    assert len(failures) == 0

    # CLI invocation without source_root
    res = subprocess.run(
        [
            sys.executable,
            str(VERIFIER_SCRIPT),
            "--lock-file",
            str(provenance_fixture["lock_file"]),
            "--installed-root",
            str(provenance_fixture["installed_root"]),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 2
    assert "[DIAGNOSTIC]" in res.stdout
    assert "Full provenance was NOT established" in res.stdout
    assert "EXTERNAL_SKILL_PROVENANCE = PASS" not in res.stdout


# 23. all six files of an alleged historical codex-delegate commit must match before attributing
def test_all_six_files_of_alleged_historical_commit_must_match_before_attributing():
    locked_files = {
        "SKILL.md": b"pinned SKILL",
        "references/dispatch-and-poll.md": b"pinned dispatch",
        "references/multi-task-queues.md": b"pinned queues",
        "references/review-and-land.md": b"pinned review",
        "references/writing-the-brief.md": b"pinned brief",
        "scripts/relay.mjs": b"pinned relay",
    }
    alleged_commit_files = copy.deepcopy(locked_files)
    alleged_commit_files["scripts/relay.mjs"] = b"historical relay"
    alleged_commit_files["SKILL.md"] = b"historical SKILL"

    def is_commit_proven(installed: dict[str, bytes], candidate: dict[str, bytes]) -> bool:
        if set(installed.keys()) != set(candidate.keys()):
            return False
        return all(installed[k] == candidate[k] for k in candidate)

    # If only 1 file matches the alleged commit, attribution is strictly invalid
    partially_matching_installed = copy.deepcopy(locked_files)
    partially_matching_installed["scripts/relay.mjs"] = b"historical relay"

    assert not is_commit_proven(partially_matching_installed, alleged_commit_files), (
        "Attribution must fail when only a subset of files matches the historical commit."
    )

    # Attribution is valid ONLY when all 6 files match exactly byte-for-byte
    fully_matching_installed = copy.deepcopy(alleged_commit_files)
    assert is_commit_proven(fully_matching_installed, alleged_commit_files)


# 24. CLI Execution Smoke Test with source-root passes full gate
def test_cli_execution_full_gate_smoke(provenance_fixture):
    res = subprocess.run(
        [
            sys.executable,
            str(VERIFIER_SCRIPT),
            "--lock-file",
            str(provenance_fixture["lock_file"]),
            "--installed-root",
            str(provenance_fixture["installed_root"]),
            "--source-root",
            str(provenance_fixture["source_root"]),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "[PASS] EXTERNAL_SKILL_PROVENANCE = PASS" in res.stdout
    assert "delegate-setup" in res.stdout


# 25. uppercase commit SHA fails
def test_uppercase_commit_sha_fails(provenance_fixture):
    lock_data = build_lock_dict(SAMPLE_SKILL_FILES)
    lock_data["source"]["pinned_commit"] = CANONICAL_PINNED_COMMIT.upper()
    provenance_fixture["lock_file"].write_text(json.dumps(lock_data), encoding="utf-8")

    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
    )
    assert code == 1
    assert any("40-character lowercase git commit SHA" in f for f in failures)


# 26. a different valid lowercase 40-character SHA fails
def test_different_valid_lowercase_commit_sha_fails(provenance_fixture):
    lock_data = build_lock_dict(SAMPLE_SKILL_FILES)
    lock_data["source"]["pinned_commit"] = "0123456789abcdef0123456789abcdef01234567"
    provenance_fixture["lock_file"].write_text(json.dumps(lock_data), encoding="utf-8")

    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
    )
    assert code == 1
    assert any("must exactly match canonical pinned commit" in f for f in failures)


# 27. unexpected root field fails
def test_unexpected_root_field_fails(provenance_fixture):
    lock_data = build_lock_dict(SAMPLE_SKILL_FILES)
    lock_data["unexpected_root_key"] = "prohibited"
    provenance_fixture["lock_file"].write_text(json.dumps(lock_data), encoding="utf-8")

    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
    )
    assert code == 1
    assert any("Unexpected root field(s)" in f for f in failures)


# 28. unexpected source field fails
def test_unexpected_source_field_fails(provenance_fixture):
    lock_data = build_lock_dict(SAMPLE_SKILL_FILES)
    lock_data["source"]["unexpected_src_key"] = "prohibited"
    provenance_fixture["lock_file"].write_text(json.dumps(lock_data), encoding="utf-8")

    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
    )
    assert code == 1
    assert any("Unexpected source field(s)" in f for f in failures)


# 29. unexpected skill field fails
def test_unexpected_skill_field_fails(provenance_fixture):
    lock_data = build_lock_dict(SAMPLE_SKILL_FILES)
    lock_data["skills"]["delegate-setup"]["unexpected_sk_key"] = "prohibited"
    provenance_fixture["lock_file"].write_text(json.dumps(lock_data), encoding="utf-8")

    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
    )
    assert code == 1
    assert any("Unexpected skill field(s)" in f for f in failures)


# 30. unexpected file-metadata field fails
def test_unexpected_file_metadata_field_fails(provenance_fixture):
    lock_data = build_lock_dict(SAMPLE_SKILL_FILES)
    lock_data["skills"]["delegate-setup"]["files"]["SKILL.md"]["unexpected_file_meta"] = "prohibited"
    provenance_fixture["lock_file"].write_text(json.dumps(lock_data), encoding="utf-8")

    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
    )
    assert code == 1
    assert any("Unexpected file-metadata field(s)" in f for f in failures)


# 31. incorrect schema_version fails
def test_incorrect_schema_version_fails(provenance_fixture):
    lock_data = build_lock_dict(SAMPLE_SKILL_FILES)
    lock_data["schema_version"] = "2.0.0"
    provenance_fixture["lock_file"].write_text(json.dumps(lock_data), encoding="utf-8")

    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
    )
    assert code == 1
    assert any("must exactly equal '1.0.0'" in f for f in failures)


# 32. incorrect source.name fails
def test_incorrect_source_name_fails(provenance_fixture):
    lock_data = build_lock_dict(SAMPLE_SKILL_FILES)
    lock_data["source"]["name"] = "wrong-source-name"
    provenance_fixture["lock_file"].write_text(json.dumps(lock_data), encoding="utf-8")

    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
    )
    assert code == 1
    assert any("must exactly equal 'delegate-skills'" in f for f in failures)


# 33. installed skill symlink escaping into another skill fails
def test_installed_skill_symlink_escaping_into_another_skill_fails(provenance_fixture, monkeypatch):
    dummy = (
        provenance_fixture["installed_root"]
        / "skills"
        / "delegate-setup"
        / "symlink_escape_installed.md"
    )
    dummy.write_bytes(b"target")
    target_in_other_skill = (
        provenance_fixture["installed_root"]
        / "skills"
        / "codex-delegate"
        / "SKILL.md"
    )

    orig_resolve = Path.resolve

    def fake_resolve(self, *args, **kwargs):
        if self.name == "symlink_escape_installed.md":
            return target_in_other_skill.resolve()
        return orig_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", fake_resolve)

    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
        source_root=provenance_fixture["source_root"],
    )
    assert code == 1
    assert any("Symlink escape detected" in f and "resolves outside skill boundary" in f for f in failures)


# 34. source skill symlink escaping into another skill fails
def test_source_skill_symlink_escaping_into_another_skill_fails(provenance_fixture, monkeypatch):
    dummy = (
        provenance_fixture["source_root"]
        / "skills"
        / "delegate-setup"
        / "symlink_escape_source.md"
    )
    dummy.write_bytes(b"target")
    target_in_other_skill = (
        provenance_fixture["source_root"]
        / "skills"
        / "codex-delegate"
        / "SKILL.md"
    )

    orig_resolve = Path.resolve

    def fake_resolve(self, *args, **kwargs):
        if self.name == "symlink_escape_source.md":
            return target_in_other_skill.resolve()
        return orig_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", fake_resolve)

    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
        source_root=provenance_fixture["source_root"],
    )
    assert code == 1
    assert any("Symlink escape detected" in f and "resolves outside skill boundary" in f for f in failures)


# 35. symlink escaping outside the overall root fails
def test_symlink_escaping_outside_the_overall_root_fails(provenance_fixture, monkeypatch):
    dummy = (
        provenance_fixture["installed_root"]
        / "skills"
        / "delegate-setup"
        / "symlink_escape_outside_root.md"
    )
    dummy.write_bytes(b"target")
    outside_target = provenance_fixture["root"] / "outside_root.txt"
    outside_target.write_bytes(b"secret outside overall root")

    orig_resolve = Path.resolve

    def fake_resolve(self, *args, **kwargs):
        if self.name == "symlink_escape_outside_root.md":
            return outside_target.resolve()
        return orig_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", fake_resolve)

    code, failures, _ = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
        source_root=provenance_fixture["source_root"],
    )
    assert code == 1
    assert any("Symlink escape detected" in f and "resolves outside skill boundary" in f for f in failures)


# 36. symlinked file inside an installed skill fails
def test_symlinked_file_inside_installed_skill_fails(provenance_fixture, monkeypatch):
    dummy_file = (
        provenance_fixture["installed_root"]
        / "skills"
        / "codex-delegate"
        / "symlink_file.txt"
    )
    dummy_file.write_bytes(b"symlinked file content")

    orig_is_symlink = Path.is_symlink

    def fake_is_symlink(self):
        if self.name == "symlink_file.txt":
            return True
        return orig_is_symlink(self)

    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)

    code, failures, summary = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
        source_root=provenance_fixture["source_root"],
    )
    assert code == 1
    assert any(
        "Symlink rejected" in f and "is a symlink" in f and "symlink_file.txt" in f
        for f in failures
    )
    assert summary["skills"]["codex-delegate"]["status"] == "FAIL"


# 37. symlinked directory inside an installed skill fails and is not followed
def test_symlinked_directory_inside_installed_skill_fails(provenance_fixture, monkeypatch):
    sym_dir = (
        provenance_fixture["installed_root"]
        / "skills"
        / "codex-delegate"
        / "symlink_dir"
    )
    sym_dir.mkdir(parents=True, exist_ok=True)
    child_file = sym_dir / "child.txt"
    child_file.write_bytes(b"child content inside symlink dir")

    orig_is_symlink = Path.is_symlink

    def fake_is_symlink(self):
        if self.name == "symlink_dir":
            return True
        return orig_is_symlink(self)

    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)

    code, failures, summary = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
        source_root=provenance_fixture["source_root"],
    )
    assert code == 1
    assert any(
        "Symlink rejected" in f and "is a symlinked directory" in f and "symlink_dir" in f
        for f in failures
    )
    # Ensure it did not follow or scan into child.txt
    assert not any("child.txt" in f for f in failures)
    assert summary["skills"]["codex-delegate"]["status"] == "FAIL"


# 38. symlinked file inside a non-Git source skill fails
def test_symlinked_file_inside_source_skill_fails(provenance_fixture, monkeypatch):
    dummy_file = (
        provenance_fixture["source_root"]
        / "skills"
        / "delegate-setup"
        / "symlink_src_file.txt"
    )
    dummy_file.write_bytes(b"source symlink file content")

    orig_is_symlink = Path.is_symlink

    def fake_is_symlink(self):
        if self.name == "symlink_src_file.txt":
            return True
        return orig_is_symlink(self)

    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)

    code, failures, summary = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
        source_root=provenance_fixture["source_root"],
    )
    assert code == 1
    assert any(
        "Symlink rejected" in f and "is a symlink" in f and "symlink_src_file.txt" in f
        for f in failures
    )
    assert summary["source_verified"] is False


# 39. symlinked directory inside a non-Git source skill fails and is not followed
def test_symlinked_directory_inside_source_skill_fails(provenance_fixture, monkeypatch):
    sym_dir = (
        provenance_fixture["source_root"]
        / "skills"
        / "delegate-setup"
        / "symlink_src_dir"
    )
    sym_dir.mkdir(parents=True, exist_ok=True)
    child_file = sym_dir / "src_child.txt"
    child_file.write_bytes(b"source child content inside symlink dir")

    orig_is_symlink = Path.is_symlink

    def fake_is_symlink(self):
        if self.name == "symlink_src_dir":
            return True
        return orig_is_symlink(self)

    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)

    code, failures, summary = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
        source_root=provenance_fixture["source_root"],
    )
    assert code == 1
    assert any(
        "Symlink rejected" in f and "is a symlinked directory" in f and "symlink_src_dir" in f
        for f in failures
    )
    # Ensure it did not follow or scan into src_child.txt
    assert not any("src_child.txt" in f for f in failures)
    assert summary["source_verified"] is False


# 40. installed skill root itself being a symlink fails
def test_installed_skill_root_itself_symlink_fails(provenance_fixture, monkeypatch):
    target_root = provenance_fixture["installed_root"] / "skills" / "codex-delegate"

    orig_is_symlink = Path.is_symlink

    def fake_is_symlink(self):
        if self == target_root or (self.name == "codex-delegate" and "installed" in str(self)):
            return True
        return orig_is_symlink(self)

    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)

    code, failures, summary = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
        source_root=provenance_fixture["source_root"],
    )
    assert code == 1
    assert any(
        "Symlink rejected: Installed skill root" in f and "codex-delegate" in f
        for f in failures
    )
    assert summary["skills"]["codex-delegate"]["status"] == "FAIL"


# 41. non-Git source skill root itself being a symlink fails
def test_source_skill_root_itself_symlink_fails(provenance_fixture, monkeypatch):
    target_src_root = provenance_fixture["source_root"] / "skills" / "delegate-setup"

    orig_is_symlink = Path.is_symlink

    def fake_is_symlink(self):
        if self == target_src_root or (self.name == "delegate-setup" and "source" in str(self)):
            return True
        return orig_is_symlink(self)

    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)

    code, failures, summary = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
        source_root=provenance_fixture["source_root"],
    )
    assert code == 1
    assert any(
        "Symlink rejected: Source skill root" in f and "delegate-setup" in f
        for f in failures
    )
    assert summary["source_verified"] is False


# 42. ordinary directory and ordinary files still pass
def test_ordinary_directory_and_ordinary_files_still_pass(provenance_fixture):
    # Directly verify scan_directory on ordinary nested directories and files
    skill_dir = provenance_fixture["installed_root"] / "skills" / "delegate-setup"
    failures_scan: list[str] = []
    scanned = scan_directory(skill_dir, skill_dir, failures_scan)
    assert len(failures_scan) == 0
    assert "SKILL.md" in scanned
    assert "references/schema.md" in scanned
    assert "scripts/config.mjs" in scanned

    # Full gate verification passes
    code, failures, summary = verify_skills(
        lock_file=provenance_fixture["lock_file"],
        installed_root=provenance_fixture["installed_root"],
        source_root=provenance_fixture["source_root"],
    )
    assert code == 0
    assert len(failures) == 0
    assert summary["source_verified"] is True
    assert summary["skills"]["delegate-setup"]["status"] == "PASS"
    assert summary["skills"]["agy-delegate"]["status"] == "PASS"
    assert summary["skills"]["codex-delegate"]["status"] == "PASS"


# 43. scan_directory rejects symlink directory before any is_file filtering
def test_scan_directory_rejects_symlink_directory_before_is_file_filtering(
    provenance_fixture, monkeypatch
):
    skill_dir = provenance_fixture["installed_root"] / "skills" / "delegate-setup"
    sym_dir = skill_dir / "symlinked_subdir"
    sym_dir.mkdir(parents=True, exist_ok=True)
    (sym_dir / "nested.txt").write_text("should never be read")

    call_order: list[str] = []

    orig_is_symlink = Path.is_symlink
    orig_is_file = Path.is_file

    def fake_is_symlink(self):
        if self.name == "symlinked_subdir":
            call_order.append("is_symlink")
            return True
        return orig_is_symlink(self)

    def fake_is_file(self):
        if self.name == "symlinked_subdir":
            call_order.append("is_file")
            return False
        return orig_is_file(self)

    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)
    monkeypatch.setattr(Path, "is_file", fake_is_file)

    failures: list[str] = []
    results = scan_directory(skill_dir, skill_dir, failures)

    assert any("symlinked directory" in f and "symlinked_subdir" in f for f in failures)
    assert not any("nested.txt" in f for f in failures)
    assert "is_symlink" in call_order
    assert (
        "is_file" not in call_order
    ), "is_file was called on symlink before or instead of is_symlink rejection"
    assert "symlinked_subdir/nested.txt" not in results
