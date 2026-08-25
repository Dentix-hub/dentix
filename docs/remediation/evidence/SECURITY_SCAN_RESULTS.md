# Changed-Content Security Scan — 2026-08-25

- Baseline: `e507691f`.
- Command: `.venv\Scripts\python.exe scripts/security/scan_changed_content.py --base-ref e507691f --exclude-test-fixtures .`
- Result: `[OK] Safe scan passed. No secrets or prohibited PHI patterns detected.`
- Scope: added committed/uncommitted production content plus untracked production files.
- Synthetic test/CI canaries are excluded only by the explicit flag and are covered by scanner unit tests; findings never print matched values.
