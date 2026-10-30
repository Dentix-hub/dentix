import pytest
from backend import models, schemas
from backend.clinical.catalog import ProcedureCode
from backend.clinical.legacy_mapping import map_legacy_procedure
from backend.cache import invalidate_cache


@pytest.mark.asyncio
async def test_procedures_canonical_code_mapping_and_exact_match(client, admin_headers, async_db_session):
    """
    U1.1 Contract Verification:
    - Seeded names map to expected canonical_code (cover all code families incl PROS_DENTURE).
    - Unknown/custom procedure names return canonical_code = null.
    - Whitespace and case variants return canonical_code = null (exact allowlist match contract).
    """
    # 1. Create one procedure per code family
    test_procedures = [
        ("حشو كومبوزيت -- Composite Filling Class I", ProcedureCode.REST_COMPOSITE.value),
        ("حشو عصب – Root Canal Treatment", ProcedureCode.ENDO_RCT.value),
        ("تاج بورسلين – Porcelain Crown", ProcedureCode.PROS_CROWN.value),
        ("جسر ثابت – Fixed Bridge", ProcedureCode.PROS_BRIDGE.value),
        ("IMPLANT_FIXTURE", ProcedureCode.IMPLANT_FIXTURE.value),
        ("IMPLANT_CROWN", ProcedureCode.IMPLANT_CROWN.value),
        ("خلع عادي – Simple Extraction", ProcedureCode.SURG_EXTRACTION.value),
        ("طقم مرن – Flexible Denture", ProcedureCode.PROS_DENTURE.value),
        # Custom/unknown procedure
        ("Custom Clinic Whitening 123", None),
        # Whitespace and case variants (must NOT match exact allowlist)
        (" Composite Filling ", None),
        ("composite filling", None),
        ("root canal", None),
    ]

    for name, _ in test_procedures:
        resp = client.post(
            "/api/v1/procedures",
            json={"name": name, "price": 250},
            headers=admin_headers,
        )
        assert resp.status_code in (200, 201), f"Failed to create procedure '{name}': {resp.text}"

    # 2. Query GET /procedures
    resp = client.get("/api/v1/procedures", headers=admin_headers)
    assert resp.status_code == 200
    items = resp.json()
    items_by_name = {item["name"]: item for item in items}

    for name, expected_code in test_procedures:
        assert name in items_by_name, f"Procedure '{name}' not returned in GET /procedures"
        actual_code = items_by_name[name].get("canonical_code")
        assert actual_code == expected_code, (
            f"Expected canonical_code for '{name}' to be {expected_code}, got {actual_code}"
        )


@pytest.mark.asyncio
async def test_procedures_global_and_tenant_override_canonical_code(client, admin_headers):
    """
    U1.1 Contract Verification:
    - Pure computation: Global templates and tenant procedures map identically.
    - Tenant-created procedures expose canonical_code in GET /procedures.
    - Repeated requests exercise cache miss followed by cache hit with invariant output.
    """
    proc_name = "تاج زيركون – Zirconia Crown"
    expected_code = ProcedureCode.PROS_CROWN.value

    # Pure computation invariant: map_legacy_procedure gives identical code
    code_result, _ = map_legacy_procedure(proc_name)
    assert code_result == expected_code

    # Create procedure via API for current tenant
    resp = client.post(
        "/api/v1/procedures",
        json={"name": proc_name, "price": 1200.0},
        headers=admin_headers,
    )
    assert resp.status_code in (200, 201)

    from backend.cache import invalidate_cache
    invalidate_cache("_get_cached_procedures")

    # Call GET /procedures twice to exercise cache miss then hit
    resp1 = client.get("/api/v1/procedures", headers=admin_headers)
    assert resp1.status_code == 200
    items1 = resp1.json()
    item1 = next((p for p in items1 if p["name"] == proc_name), None)
    assert item1 is not None
    assert item1["canonical_code"] == expected_code

    resp2 = client.get("/api/v1/procedures", headers=admin_headers)
    assert resp2.status_code == 200
    items2 = resp2.json()
    item2 = next((p for p in items2 if p["name"] == proc_name), None)
    assert item2 is not None
    assert item2["canonical_code"] == expected_code


@pytest.mark.asyncio
async def test_procedures_tenant_isolation(client, admin_headers, async_db_session):
    """
    U1.1 Contract Verification:
    - Tenant isolation: Procedures created in Tenant A must not appear in Tenant B.
    """
    # Tenant A procedure (created via admin_headers)
    resp = client.post(
        "/api/v1/procedures",
        json={"name": "Tenant A Secret Procedure", "price": 999},
        headers=admin_headers,
    )
    assert resp.status_code in (200, 201)

    # In default fixtures, doctor_headers belongs to Tenant 1 as well or a different tenant?
    # Let's check: doctor_headers is in the same tenant.
    # To test strict isolation, create a procedure in Tenant 999 directly
    other_tenant_proc = models.Procedure(name="Tenant 999 Procedure", price=777.0, tenant_id=999)
    async_db_session.add(other_tenant_proc)
    await async_db_session.commit()
    invalidate_cache("_get_cached_procedures")

    resp = client.get("/api/v1/procedures", headers=admin_headers)
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert "Tenant A Secret Procedure" in names
    assert "Tenant 999 Procedure" not in names
