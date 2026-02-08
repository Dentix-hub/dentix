# 📜 Script Classification & Governance

**Last Updated:** 2026-01-24

This directory contains utility scripts for the backend. All scripts must be classified and documented.

---

## 🟢 Production Safe
*Scripts safe to run in production with standard precautions.*

- `migrations/env.py`: Alembic migration environment
- `seed_database.py`: Initial data seeding (idempotent)

## 🟡 Development Only
*Scripts for local testing and debugging. DO NOT RUN IN PROD.*

- `tests/`: All test runners
- `debug_tools/`: Any temporary debug scripts

## 🔴 One-Time Migrations
*Scripts designed to run exactly once for data fixes.*

- `migrations/legacy/fix_payments_doctors.py`: Legacy fix
- `migrations/legacy/fix_treatments_doctors.py`: Legacy fix

## 🗑️ Deprecated
*Scripts scheduled for deletion.*

- *None currently*

---

## ⚠️ Execution Rules

1. **Production:** Only run via CI/CD pipeline or by authorized DevOps lead.
2. **Migrations:** Must use Alembic (`alembic upgrade head`).
3. **One-Offs:** Check `docs/DO_NOT_TOUCH.md` before execution.
