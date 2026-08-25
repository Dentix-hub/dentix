"""
Tests for scripts/security/scan_changed_content.py
"""

from scripts.security.scan_changed_content import scan_git_diff, scan_text


def test_scan_text_clean_content():
    clean_sample = """
    def get_patient(id: int):
        return {"id": id, "name": "Anonymous Patient"}
    """
    findings = scan_text(clean_sample, "test_file.py")
    assert len(findings) == 0


def test_scan_text_detects_canaries_and_redacts():
    sensitive_sample = (
        "DB_URI = 'postgresql://admin:super_secret_password@localhost:5432/dentix_dev'\n"
        "NATIONAL_ID = '29501011234567'\n"
        "PHONE = '01012345678'\n"
    )
    findings = scan_text(sensitive_sample, "sensitive_fixture.py")
    assert len(findings) >= 3

    rule_ids = {f["rule_id"] for f in findings}
    assert "SEC003_PASSWORD_IN_URL" in rule_ids
    assert "PHI001_EGYPTIAN_NATIONAL_ID" in rule_ids
    assert "PHI002_PHONE_RAW_11DIGIT" in rule_ids

    # Verify no secret text is present in findings dictionary
    for f in findings:
        assert "super_secret_password" not in str(f)
        assert "29501011234567" not in str(f)
        assert "01012345678" not in str(f)


def test_scan_git_diff_checks_only_added_lines_and_redacts_values():
    secret = "postgresql://admin:unsafe-pass@db.example/dentix"
    diff = "\n".join([
        "diff --git a/app.py b/app.py",
        "--- a/app.py",
        "+++ b/app.py",
        "@@ -10,2 +10,2 @@",
        "-DATABASE_URL = 'postgresql://old:deleted@db.example/old'",
        f"+DATABASE_URL = '{secret}'",
        " context = True",
    ])

    findings = scan_git_diff(diff)

    assert len(findings) == 1
    assert findings[0]["file"] == "app.py"
    assert findings[0]["line"] == "10"
    assert secret not in str(findings)


def test_scan_git_diff_ignores_deleted_sensitive_content():
    diff = "\n".join([
        "diff --git a/app.py b/app.py",
        "--- a/app.py",
        "+++ b/app.py",
        "@@ -1 +1 @@",
        "-DATABASE_URL = 'postgresql://admin:deleted@db.example/dentix'",
        "+DATABASE_URL = os.environ['DATABASE_URL']",
    ])

    assert scan_git_diff(diff) == []
