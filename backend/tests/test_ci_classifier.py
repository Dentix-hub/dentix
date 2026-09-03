import json
import sys
from pathlib import Path
import pytest

script_path = Path(__file__).parent.parent.parent / ".github" / "scripts"
sys.path.insert(0, str(script_path.resolve()))
from classify_ci_scope import classify_files, parse_labels


# ── Basic subsystem classification ──

def test_frontend_test_only():
    res = classify_files(["frontend/src/shared/ui/__tests__/Button.test.jsx"])
    assert res["frontend"] is True
    assert res["backend"] is False
    assert res["force_full"] is False


def test_frontend_presentational():
    res = classify_files(["frontend/src/components/Navbar.jsx"])
    assert res["frontend"] is True
    assert res["backend"] is False
    assert res["force_full"] is False


def test_pwa_service_worker():
    res = classify_files(["frontend/src/pwa/preloadRecovery.js"])
    assert res["frontend"] is True
    assert res["pwa"] is True
    assert res["force_full"] is False


def test_backend_standard_router():
    res = classify_files(["backend/routers/patients.py"])
    assert res["backend"] is True
    assert res["frontend"] is False
    assert res["force_full"] is False


def test_mixed_frontend_backend_non_keyword():
    res = classify_files(["frontend/src/App.jsx", "backend/routers/patients.py"])
    assert res["frontend"] is True
    assert res["backend"] is True
    assert res["force_full"] is False


def test_docs_only():
    res = classify_files(["docs/engineering/README.md", "AGENTS.md"])
    assert res["docs_only"] is True
    assert res["force_full"] is False


def test_dependencies():
    res = classify_files(["uv.lock"])
    assert res["dependencies"] is True
    assert res["backend"] is True


# ── Codex Review Gate 2: 13 representative high-risk paths ──
# Every path listed by the reviewer as bypassing force_full must now
# correctly classify as force_full=True.

def test_bypass_backend_auth_root():
    """backend/auth.py — auth keyword at backend root."""
    res = classify_files(["backend/auth.py"])
    assert res["force_full"] is True, "backend/auth.py must force full"
    assert res["auth"] is True


def test_bypass_backend_crud_auth():
    """backend/crud/auth.py — auth keyword in crud directory."""
    res = classify_files(["backend/crud/auth.py"])
    assert res["force_full"] is True, "backend/crud/auth.py must force full"
    assert res["auth"] is True


def test_bypass_frontend_auth_provider():
    """frontend/src/auth/AuthProvider.jsx — auth keyword in frontend auth dir."""
    res = classify_files(["frontend/src/auth/AuthProvider.jsx"])
    assert res["force_full"] is True, "frontend/src/auth/AuthProvider.jsx must force full"
    assert res["auth"] is True


def test_bypass_frontend_store_auth():
    """frontend/src/store/auth.store.js — auth keyword in store."""
    res = classify_files(["frontend/src/store/auth.store.js"])
    assert res["force_full"] is True, "frontend/src/store/auth.store.js must force full"
    assert res["auth"] is True


def test_bypass_frontend_api_auth():
    """frontend/src/api/auth.js — auth keyword in api."""
    res = classify_files(["frontend/src/api/auth.js"])
    assert res["force_full"] is True, "frontend/src/api/auth.js must force full"
    assert res["auth"] is True


def test_bypass_migrations_adhoc():
    """backend/migrations_adhoc/... — migration keyword."""
    res = classify_files(["backend/migrations_adhoc/add_doctor_visibility.py"])
    assert res["force_full"] is True, "backend/migrations_adhoc must force full"
    assert res["migration"] is True


def test_bypass_ai_security_sanitizer():
    """backend/ai/security/sanitizer.py — security keyword."""
    res = classify_files(["backend/ai/security/sanitizer.py"])
    assert res["force_full"] is True, "backend/ai/security/sanitizer.py must force full"
    assert res["security"] is True


def test_bypass_clinical_chart_procedure_layers():
    """procedureLayers changes clinical meaning, not only presentation."""
    res = classify_files(["frontend/src/features/clinical-chart-v2/procedureLayers.js"])
    assert res["force_full"] is True, "clinical-chart-v2 must force full"
    assert res["clinical_semantics"] is True
    assert res["clinical_ui"] is True


def test_bypass_clinical_service():
    """backend/services/clinical_service.py — clinical keyword."""
    res = classify_files(["backend/services/clinical_service.py"])
    assert res["force_full"] is True, "clinical_service.py must force full"
    assert res["clinical_semantics"] is True


# ── Additional real-repo high-risk paths ──

def test_core_permissions():
    res = classify_files(["backend/core/permissions.py"])
    assert res["force_full"] is True
    assert res["security"] is True


def test_core_tenant_scope():
    res = classify_files(["backend/core/tenant_scope.py"])
    assert res["force_full"] is True
    assert res["tenancy"] is True


def test_routers_payments():
    res = classify_files(["backend/routers/payments.py"])
    assert res["force_full"] is True
    assert res["finance"] is True


def test_routers_auth_login():
    res = classify_files(["backend/routers/auth/login.py"])
    assert res["force_full"] is True
    assert res["auth"] is True


def test_schemas_auth():
    res = classify_files(["backend/schemas/auth.py"])
    assert res["force_full"] is True
    assert res["auth"] is True


@pytest.mark.parametrize(
    "path",
    [
        "frontend/src/api/apiClient.js",
        "backend/models/inventory.py",
        "backend/schemas/patient.py",
        "backend/core/cache.py",
    ],
)
def test_closed_list_structural_high_risk_surfaces(path):
    res = classify_files([path])
    assert res["force_full"] is True, f"{path} is a closed-list HIGH_RISK surface"


@pytest.mark.parametrize(
    "path",
    [
        "frontend/src/features/clinical-chart-v2/ToothRenderer.jsx",
        "frontend/src/features/clinical-chart-v2/ClinicalChartPage.jsx",
        "frontend/src/features/odontogram/InspectorPanel.jsx",
    ],
)
def test_clinical_ui_is_standard_when_semantics_are_untouched(path):
    res = classify_files([path])
    assert res["frontend"] is True
    assert res["clinical_ui"] is True
    assert res["clinical_semantics"] is False
    assert res["force_full"] is False


def test_auth_is_token_aware_not_a_raw_substring():
    res = classify_files(["frontend/src/components/AuthorCard.jsx"])
    assert res["frontend"] is True
    assert res["auth"] is False
    assert res["force_full"] is False


def test_high_risk_domain_documentation_remains_docs_only():
    res = classify_files(["docs/engineering/auth-migration-notes.md"])
    assert res["docs_only"] is True
    assert res["force_full"] is False


def test_frontend_admin_pages():
    paths = [
        "frontend/src/pages/admin/TenantsPage.jsx",
        "frontend/src/pages/admin/FinancePage.jsx",
        "frontend/src/features/admin/SuperAdmin/SecurityPanel.jsx",
    ]
    for p in paths:
        res = classify_files([p])
        assert res["force_full"] is True, f"Expected force_full for {p}"


def test_alembic_migration():
    res = classify_files(["backend/alembic/versions/test_migration.py"])
    assert res["force_full"] is True
    assert res["migration"] is True


def test_models_tenant():
    res = classify_files(["backend/models/tenant.py"])
    assert res["force_full"] is True
    assert res["tenancy"] is True


def test_middleware_tenant():
    res = classify_files(["backend/middleware/tenant.py"])
    assert res["force_full"] is True
    assert res["tenancy"] is True


def test_frontend_finance_permissions():
    res = classify_files(["frontend/src/features/finance/useFinancePermissions.js"])
    assert res["force_full"] is True
    assert res["finance"] is True


def test_billing_crud():
    res = classify_files(["backend/crud/billing.py"])
    assert res["force_full"] is True
    assert res["finance"] is True


def test_ai_handlers_finance():
    res = classify_files(["backend/ai/handlers/finance.py"])
    assert res["force_full"] is True
    assert res["finance"] is True


def test_ai_handlers_clinical():
    res = classify_files(["backend/ai/handlers/clinical.py"])
    assert res["force_full"] is True
    assert res["clinical_semantics"] is True


def test_frontend_auth_session():
    res = classify_files(["frontend/src/api/authSession.js"])
    assert res["force_full"] is True
    assert res["auth"] is True


def test_backend_database():
    res = classify_files(["backend/database.py"])
    assert res["force_full"] is True


def test_backend_main():
    res = classify_files(["backend/main.py"])
    assert res["force_full"] is True


def test_security_headers_middleware():
    res = classify_files(["backend/middleware/security_headers.py"])
    assert res["force_full"] is True
    assert res["security"] is True


def test_ci_test_rls():
    res = classify_files(["backend/ci_tests/test_rls_concurrency_postgres.py"])
    assert res["force_full"] is True
    assert res["tenancy"] is True


# ── Container & Governance ──

def test_container_runtime():
    res = classify_files(["Dockerfile"])
    assert res["force_full"] is True
    assert res["container"] is True


def test_workflow_governance():
    res = classify_files([".github/workflows/ci.yml"])
    assert res["force_full"] is True
    assert res["workflow_governance"] is True


# ── Event, Promotion & Label classification ──

def test_protected_push_staging_reuses_pr_validation():
    res = classify_files(
        ["backend/auth.py"],
        event_name="push",
        target_branch="staging",
    )
    assert not any(res.values())


def test_protected_push_main_reuses_pr_validation():
    res = classify_files(
        [".github/workflows/ci.yml"],
        event_name="push",
        target_branch="refs/heads/main",
    )
    assert not any(res.values())


def test_staging_to_main_promotion_reuses_validated_revision():
    res = classify_files(
        ["backend/auth.py", ".github/workflows/ci.yml"],
        event_name="pull_request",
        target_branch="main",
        source_branch="staging",
    )
    assert not any(res.values())


def test_high_risk_label_can_force_fresh_staging_to_main_validation():
    res = classify_files(
        ["frontend/src/App.jsx"],
        event_name="pull_request",
        target_branch="main",
        source_branch="staging",
        labels=["risk:high-risk"],
    )
    assert res["force_full"] is True


def test_release_to_main_is_not_treated_as_trusted_staging_promotion():
    res = classify_files(
        [".github/workflows/ci.yml"],
        event_name="pull_request",
        target_branch="main",
        source_branch="release/workflow-sync",
    )
    assert res["force_full"] is True
    assert res["workflow_governance"] is True


def test_workflow_dispatch():
    res = classify_files(["frontend/src/App.jsx"], event_name="workflow_dispatch")
    assert res["force_full"] is True


def test_labels_string():
    res = classify_files(["frontend/src/App.jsx"], labels=["mode:high-risk"])
    assert res["force_full"] is True


def test_labels_json():
    json_labels = json.dumps([{"name": "risk:auth-rbac", "color": "red"}])
    res = classify_files(["frontend/src/App.jsx"], labels=json_labels)
    assert res["force_full"] is True


def test_labels_non_high_risk():
    res = classify_files(
        ["frontend/src/components/Navbar.jsx"],
        labels=json.dumps([{"name": "mode:fast"}]),
    )
    assert res["force_full"] is False


# ── Unknown root path ──

def test_unknown_path_fail_safe():
    res = classify_files(["unexpected_root_file.sh"])
    assert res["force_full"] is True


# ── GitHub templates are docs ──

def test_issue_template_is_docs():
    res = classify_files([".github/ISSUE_TEMPLATE/dentix-agent-task.yml"])
    assert res["force_full"] is False
    assert res["docs_only"] is True


def test_pr_template_is_docs():
    res = classify_files([".github/pull_request_template.md"])
    assert res["force_full"] is False
    assert res["docs_only"] is True
