"""PR6 contracts for canonical operational-page CSV exports."""

from datetime import date, datetime, timezone

from backend import models
from backend.auth import create_access_token, get_password_hash


def _headers(user):
    token = create_access_token(
        data={"sub": user.username, "role": user.role, "tenant_id": user.tenant_id}
    )
    return {"Authorization": f"Bearer {token}"}


def test_operational_exports_require_report_export_permission(
    client, db_session, test_tenant
):
    receptionist = models.User(
        username="pr6_export_receptionist",
        email="pr6-export-receptionist@example.com",
        hashed_password=get_password_hash("testpass123"),
        role="receptionist",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add(receptionist)
    db_session.commit()

    headers = _headers(receptionist)
    period = {"start_date": "2026-08-01", "end_date": "2026-08-31"}
    paths = [
        ("/api/v1/financials/reports/summary/export.csv", period),
        ("/api/v1/financials/reports/patient-accounts/export.csv", period),
        ("/api/v1/financials/reports/expenses/export.csv", period),
        ("/api/v1/financials/reports/providers/export.csv", period),
    ]

    for path, params in paths:
        response = client.get(path, params=params, headers=headers)
        assert response.status_code == 403, (path, response.text)


def test_operational_exports_are_registered_for_authorized_admin(client, admin_headers):
    period = {"start_date": "2026-08-01", "end_date": "2026-08-31", "locale": "en"}
    for path in (
        "/api/v1/financials/reports/summary/export.csv",
        "/api/v1/financials/reports/patient-accounts/export.csv",
        "/api/v1/financials/reports/expenses/export.csv",
        "/api/v1/financials/reports/providers/export.csv",
    ):
        response = client.get(path, params=period, headers=admin_headers)
        assert response.status_code == 200, (path, response.text)
        assert response.headers["content-type"].startswith("text/csv")
        assert response.content.startswith(b"\xef\xbb\xbf")


def test_expense_export_applies_active_search_and_category_filters(
    client, db_session, test_tenant, admin_headers
):
    db_session.add_all(
        [
            models.Expense(
                item_name="PR6 Gloves",
                cost=250,
                category="Supplies",
                date=date(2026, 8, 10),
                tenant_id=test_tenant.id,
                notes="=unsafe-note",
            ),
            models.Expense(
                item_name="PR6 Rent",
                cost=5000,
                category="Rent",
                date=date(2026, 8, 10),
                tenant_id=test_tenant.id,
                notes="other",
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        "/api/v1/financials/reports/expenses/export.csv",
        params={
            "search": "Gloves",
            "category": "Supplies",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "locale": "en",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    text = response.content.decode("utf-8-sig")
    assert "PR6 Gloves" in text
    assert "PR6 Rent" not in text
    assert "'=unsafe-note" in text
    assert "manual_expense" in text


def test_patient_account_export_is_tenant_scoped_and_honors_file_filter(
    client, db_session, test_tenant, admin_headers
):
    patient = models.Patient(
        name="PR6 Export Patient",
        phone="01000009601",
        age=30,
        medical_history="",
        notes="",
        tenant_id=test_tenant.id,
        is_deleted=False,
    )
    other_tenant = models.Tenant(name="PR6 Export Other Clinic", is_active=True)
    db_session.add_all([patient, other_tenant])
    db_session.commit()
    db_session.refresh(patient)
    db_session.refresh(other_tenant)

    other_patient = models.Patient(
        name="PR6 Other Patient",
        phone="01000009602",
        age=31,
        medical_history="",
        notes="",
        tenant_id=other_tenant.id,
        is_deleted=False,
    )
    db_session.add(other_patient)
    db_session.commit()
    db_session.refresh(other_patient)

    # Patient Accounts intentionally reports finance-active accounts. Give both
    # patients real activity so this test proves filtering/isolation rather than
    # relying on an inactive patient being present in a finance report.
    db_session.add_all(
        [
            models.Treatment(
                patient_id=patient.id,
                diagnosis="Caries",
                procedure="PR6 Filling",
                cost=1000,
                discount=0,
                date=datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc),
                tenant_id=test_tenant.id,
                is_deleted=False,
            ),
            models.Treatment(
                patient_id=other_patient.id,
                diagnosis="Caries",
                procedure="PR6 Other Filling",
                cost=9000,
                discount=0,
                date=datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc),
                tenant_id=other_tenant.id,
                is_deleted=False,
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        "/api/v1/financials/reports/patient-accounts/export.csv",
        params={
            "patient_id": patient.id,
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "locale": "en",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    text = response.content.decode("utf-8-sig")
    assert "PR6 Export Patient" in text
    assert "PR6 Other Patient" not in text
