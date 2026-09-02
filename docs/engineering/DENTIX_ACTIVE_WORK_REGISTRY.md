# DENTIX Execution State & Repository Authority

## Execution Authority Model

DENTIX tracks live work through GitHub and Git repository branches, not mutable documentation files:

* **GitHub Issues**: Authoritative record of ready, blocked, and planned tasks.
* **Pull Requests**: Authoritative record of active review, validation, and integration state.
* **`origin/staging`**: The canonical integration branch for verified development work.
* **`origin/main`**: The protected production branch.
* **Feature Branches & Worktrees**: Ephemeral execution containers for isolated changes.

## Non-Stateful Policy

This document does **not** track:
- the current active issue,
- the current active wave,
- the next executable task,
- current product branches or local worktrees.

Live execution state must always be read directly from GitHub Issues, Pull Requests, and the current Git repository truth.
