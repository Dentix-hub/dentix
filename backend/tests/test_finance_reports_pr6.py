"""PR6 regression tests for server-backed Finance reports and safe export."""

from datetime import date

import pytest

from backend import models
from backend.auth import create_access_token, get_password_hash
from backend.services.cost_engine import CostEngine
from backend.services.finance_report_service import build_csv_document, sanitize_csv_text


def _headers(user):
    token = create_access_token(
        data={"sub": user.username, "role": user.role, "tenant_id": user.tenant_id}
    )
    return {"Authorization": f"Bearer {token}"}


def test_csv_formula_injection_is_neutralized_without_corrupting_numbers():
    assert sanitize_csv_text("=2+2") == "'=2+2"
    assert sanitize_csv_text("+SUM(A1:A2)") == "'+SUM(A1:A2)"
    assert sanitize_csv_text("-CMD") == "'-CMD"
    assert sanitize_csv_text("@HYPERLINK") == "'@HYPERLINK"
    assert sanitize_csv_text("\tformula") == "'\tformula"
    assert sanitize_csv_text(-150.25) == -150.25

    document = build_csv_document(
        columns=[("name", "Name"), ("amount", "Amount")],
        rows=[{"name": "=unsafe", "amount": -25.5}],
        metadata={"Definition": "finance-summary-v1"},
    )
    assert "'=unsafe" in document
    assert "-25.5" in document


def test_report_permissions_block_receptionist_and_allow_accountant(
    client, db_session, test_tenant
):
    receptionist = models.User(
        username="pr6_receptionist",
        email="pr6-receptionist@example.com",
        hashed_password=get_password_hash("testpass123"),
        role="receptionist",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    accountant = models.User(
        username="pr6_accountant",
        email="pr6-accountant@example.com",
        hashed_password=get_password_hash("testpass123"),
        role="accountant",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add_all([receptionist, accountant])
    db_session.commit()

    params = {"start_date": "2026-08-01", "end_date": "2026-08-15"}

    denied_read = client.get(
        "/api/v1/accounting/reports/period-comparison",
        params=params,
        headers=_headers(receptionist),
    )
    denied_export = client.get(
        "/api/v1/accounting/reports/period-comparison/export.csv",
        params={**params, "locale": "en"},
        headers=_headers(receptionist),
    )
    assert denied_read.status_code == 403
    assert denied_export.status_code == 403

    allowed_read = client.get(
        "/api/v1/accounting/reports/period-comparison",
        params=params,
        headers=_headers(accountant),
    )
    allowed_export = client.get(
        "/api/v1/accounting/reports/period-comparison/export.csv",
        params={**params, "locale": "en"},
        headers=_headers(accountant),
    )
    assert allowed_read.status_code == 200
    assert allowed_export.status_code == 200
    assert allowed_export.headers["content-type"].startswith("text/csv")


def test_period_comparison_infers_equal_previous_range(client, admin_headers):
    response = client.get(
        "/api/v1/accounting/reports/period-comparison",
        params={"start_date": "2026-08-08", "end_date": "2026-08-14"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["current_period"]["start"] == "2026-08-08"
    assert data["current_period"]["end"] == "2026-08-14"
    assert data["comparison_period"]["start"] == "2026-08-01"
    assert data["comparison_period"]["end"] == "2026-08-07"
    assert data["definition_version"] == "finance-summary-v1"
    assert len(data["metrics"]) == 8


@pytest.mark.asyncio
async def test_missing_material_cost_never_becomes_fake_100_percent_margin(
    async_db_session, test_tenant
):
    procedure = models.Procedure(
        id=9601,
        name="PR6 Missing Cost Procedure",
        price=1000,
        tenant_id=test_tenant.id,
    )
    material = models.Material(
        id=9602,
        tenant_id=test_tenant.id,
        name="PR6 Material Without Cost",
        type="DIVISIBLE",
        base_unit="g",
        packaging_ratio=5,
    )
    weight = models.ProcedureMaterialWeight(
        id=9603,
        procedure_id=procedure.id,
        material_id=material.id,
        tenant_id=test_tenant.id,
        weight=1,
        current_average_usage=0.5,
        sample_size=12,
    )
    async_db_session.add_all([procedure, material, weight])
    await async_db_session.commit()

    analysis = await CostEngine(async_db_session, test_tenant.id).calculate_procedure_cost(
        procedure.id
    )

    assert analysis["definition_version"] == "estimated-material-margin-v2"
    assert analysis["metric_scope"] == "materials_only"
    assert analysis["coverage"]["is_complete"] is False
    assert analysis["coverage"]["missing_cost_materials"] == 1
    assert analysis["coverage"]["confidence"] == "unavailable"
    assert analysis["total_actual_cost"] is None
    assert analysis["actual_profit_margin"] is None
    assert analysis["actual_margin_percentage"] is None


@pytest.mark.asyncio
async def test_material_margin_report_is_server_paginated(async_db_session, test_tenant):
    procedures = [
        models.Procedure(
            id=9700 + index,
            name=f"PR6 Procedure {index}",
            price=100 + index,
            tenant_id=test_tenant.id,
        )
        for index in range(1, 4)
    ]
    async_db_session.add_all(procedures)
    await async_db_session.commit()

    report = await CostEngine(async_db_session, test_tenant.id).calculate_material_margin_report(
        search="PR6 Procedure",
        skip=0,
        limit=2,
        sort="name_asc",
    )

    assert report["pagination"]["total"] == 3
    assert report["pagination"]["returned"] == 2
    assert len(report["items"]) == 2
    assert all(item["material_margin"] is None for item in report["items"])
    assert report["completeness"]["unavailable"] == 2
    assert report["warning"] is not None


def test_cross_tenant_procedure_analysis_does_not_leak(
    client, db_session, admin_user, admin_headers
):
    other_tenant = models.Tenant(name="PR6 Other Clinic", is_active=True)
    db_session.add(other_tenant)
    db_session.commit()
    db_session.refresh(other_tenant)

    procedure = models.Procedure(
        name="PR6 Tenant B Procedure",
        price=500,
        tenant_id=other_tenant.id,
    )
    db_session.add(procedure)
    db_session.commit()
    db_session.refresh(procedure)

    response = client.get(
        f"/api/v1/financials/procedure/{procedure.id}/analysis",
        headers=admin_headers,
    )
    assert admin_user.tenant_id != other_tenant.id
    assert response.status_code == 404


def test_material_margin_report_and_export_require_report_permissions(
    client, db_session, test_tenant
):
    receptionist = models.User(
        username="pr6_margin_receptionist",
        email="pr6-margin-receptionist@example.com",
        hashed_password=get_password_hash("testpass123"),
        role="receptionist",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    accountant = models.User(
        username="pr6_margin_accountant",
        email="pr6-margin-accountant@example.com",
        hashed_password=get_password_hash("testpass123"),
        role="accountant",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add_all([receptionist, accountant])
    db_session.commit()

    report_path = "/api/v1/financials/reports/material-margin"
    export_path = "/api/v1/financials/reports/material-margin/export.csv"

    assert client.get(report_path, headers=_headers(receptionist)).status_code == 403
    assert client.get(export_path, headers=_headers(receptionist)).status_code == 403

    allowed_report = client.get(report_path, headers=_headers(accountant))
    allowed_export = client.get(
        export_path,
        params={"locale": "ar"},
        headers=_headers(accountant),
    )
    assert allowed_report.status_code == 200
    assert allowed_export.status_code == 200
    assert "estimated-material-margin-v2" in allowed_export.text
