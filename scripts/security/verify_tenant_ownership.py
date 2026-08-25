#!/usr/bin/env python3
"""
Preflight Tenant Ownership Verification Script.
Inspects all ORM models and validates that sensitive clinic tables have direct tenant_id attributes and RLS policies.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import models

SENSITIVE_MODELS = [
    models.ToothStatus,
    models.Prescription,
    models.Attachment,
    models.MaterialSession,
    models.StockMovement,
    models.Patient,
    models.Treatment,
    models.Appointment,
    models.Payment,
]


def verify_tenant_ownership() -> bool:
    all_passed = True
    print("=== DENTIX Multi-Tenant Ownership & RLS Preflight ===")

    for model in SENSITIVE_MODELS:
        table_name = getattr(model, "__tablename__", str(model))
        has_tenant_id = hasattr(model, "tenant_id")
        has_rls = hasattr(model, "__rls_policies__") and len(model.__rls_policies__) > 0

        status = "[PASS]" if (has_tenant_id and has_rls) else "[FAIL]"
        if not (has_tenant_id and has_rls):
            all_passed = False

        print(f"{status} {table_name:30} | tenant_id: {str(has_tenant_id):5} | RLS: {str(has_rls):5}")

    if all_passed:
        print("\n[SUCCESS] All sensitive clinic models are directly tenant-scoped with active RLS definitions.")
        return True
    else:
        print("\n[FAILURE] One or more sensitive models are missing tenant_id or RLS policy definitions.", file=sys.stderr)
        return False


if __name__ == "__main__":
    if not verify_tenant_ownership():
        sys.exit(1)
