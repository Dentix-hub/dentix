"""Entry-point alias for backend/scripts/report_unloginable_usernames.py."""

from __future__ import annotations

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.scripts.report_unloginable_usernames import (  # noqa: E402,F401
    find_unloginable_usernames,
    format_report,
    main,
)

if __name__ == "__main__":
    raise SystemExit(main())
