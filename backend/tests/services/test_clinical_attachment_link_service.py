"""
Clinical Attachment Link Service & Context Linking Tests (Slice S23 / Phase G15).

Covers:
- G15-M01: Keep attachment storage unchanged (no duplicate uploads, no file deletes).
- G15-M02: Add context links only (models.ClinicalAttachmentLink).
- G15-M06: Add purpose codes (Decision PD05 allowlist enforcement).
- Tenant & patient isolation: cross-tenant/cross-patient references fail closed (404).
- Fail-closed gate: clinical_vnext_native_writes required for mutations (404 when disabled).
- Duplicate context link rejection (409 Conflict).
- Delete unlinks context while leaving underlying Attachment row 100% intact.
"""

from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from backend import models, schemas
from backend.clinical.catalog import CANONICAL_ATTACHMENT_PURPOSE_CODES, AttachmentPurposeCode
from backend.services.clinical_attachment_link_service import (
    FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
    ClinicalAttachmentLinkService,
)
from backend.services.feature_service import FeatureFlagService


@pytest.fixture
async def seed_data(async_db_session):
    """Seed tenants, doctors, patients, attachments, and work items."""
    tenant_1 = models.Tenant(name="Apex Dental Clinic", domain="apex.example.com", is_active=True)
    tenant_2 = models.Tenant(name="Other Clinic", domain="other.example.com", is_active=True)
    async_db_session.add_all([tenant_1, tenant_2])
    await async_db_session.flush()

    doctor_1 = models.User(
        tenant_id=tenant_1.id,
        username="dr_apex",
        email="doctor@apex.com",
        hashed_password="test-hashed-password",
        role="doctor",
        is_active=True,
    )
    doctor_2 = models.User(
        tenant_id=tenant_2.id,
        username="dr_other",
        email="doctor@other.com",
        hashed_password="test-hashed-password",
        role="doctor",
        is_active=True,
    )
    receptionist_1 = models.User(
        tenant_id=tenant_1.id,
        username="recep_apex",
        email="recep@apex.com",
        hashed_password="test-hashed-password",
        role="receptionist",
        is_active=True,
    )
    async_db_session.add_all([doctor_1, doctor_2, receptionist_1])
    await async_db_session.flush()

    patient_1 = models.Patient(
        tenant_id=tenant_1.id,
        name="Tariq Ali",
        age=35,
        phone="+966500000001",
        medical_history="No systemic allergies",
        notes="",
        assigned_doctor_id=doctor_1.id,
        is_deleted=False,
    )
    patient_2 = models.Patient(
        tenant_id=tenant_1.id,
        name="Sara Ahmed",
        age=28,
        phone="+966500000002",
        medical_history="None",
        notes="",
        assigned_doctor_id=doctor_1.id,
        is_deleted=False,
    )
    patient_3 = models.Patient(
        tenant_id=tenant_2.id,
        name="Omar Farooq",
        age=42,
        phone="+966500000003",
        medical_history="None",
        notes="",
        assigned_doctor_id=doctor_2.id,
        is_deleted=False,
    )
    async_db_session.add_all([patient_1, patient_2, patient_3])
    await async_db_session.flush()

    # Create attachments
    att_1 = models.Attachment(
        tenant_id=tenant_1.id,
        patient_id=patient_1.id,
        filename="periapical_tooth16.png",
        file_path="/storage/attachments/periapical_tooth16.png",
        file_type="image/png",
        note="Tooth 16 diagnostic periapical radiograph",
    )
    att_2 = models.Attachment(
        tenant_id=tenant_1.id,
        patient_id=patient_1.id,
        filename="working_length_t16.png",
        file_path="/storage/attachments/working_length_t16.png",
        file_type="image/png",
        note="Tooth 16 working length X-ray",
    )
    att_p2 = models.Attachment(
        tenant_id=tenant_1.id,
        patient_id=patient_2.id,
        filename="patient2_file.pdf",
        file_path="/storage/attachments/patient2_file.pdf",
        file_type="application/pdf",
        note="Patient 2 general medical report",
    )
    att_t2 = models.Attachment(
        tenant_id=tenant_2.id,
        patient_id=patient_3.id,
        filename="tenant2_xray.png",
        file_path="/storage/attachments/tenant2_xray.png",
        file_type="image/png",
        note="Tenant 2 X-ray",
    )
    async_db_session.add_all([att_1, att_2, att_p2, att_t2])
    await async_db_session.flush()

    # Create clinical work item on patient 1
    work_item_1 = models.ClinicalWorkItem(
        tenant_id=tenant_1.id,
        patient_id=patient_1.id,
        code="ENDO_RCT",
        kind="procedure",
        status="active",
        created_by_user_id=doctor_1.id,
    )
    # Create clinical work item on patient 2
    work_item_2 = models.ClinicalWorkItem(
        tenant_id=tenant_1.id,
        patient_id=patient_2.id,
        code="REST_COMPOSITE",
        kind="procedure",
        status="active",
        created_by_user_id=doctor_1.id,
    )
    async_db_session.add_all([work_item_1, work_item_2])
    await async_db_session.flush()

    # Create care session on patient 1
    care_session_1 = models.CareSession(
        tenant_id=tenant_1.id,
        patient_id=patient_1.id,
        status="in_progress",
        started_at=datetime.now(timezone.utc),
        provider_user_id=doctor_1.id,
    )
    # Create care session on patient 2
    care_session_2 = models.CareSession(
        tenant_id=tenant_1.id,
        patient_id=patient_2.id,
        status="in_progress",
        started_at=datetime.now(timezone.utc),
        provider_user_id=doctor_1.id,
    )
    async_db_session.add_all([care_session_1, care_session_2])
    await async_db_session.flush()

    # Ensure FeatureFlag exists and enable for tenant 1
    stmt = select(models.FeatureFlag).where(
        models.FeatureFlag.key == FEATURE_FLAG_CLINICAL_NATIVE_WRITES
    )
    flag = (await async_db_session.execute(stmt)).scalar_one_or_none()
    if not flag:
        flag = models.FeatureFlag(
            key=FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
            description="Clinical native writes",
            is_global_enabled=True,
            rollout_percentage=0,
        )
        async_db_session.add(flag)
        await async_db_session.commit()
        await async_db_session.refresh(flag)

    await FeatureFlagService.set_tenant_override(
        async_db_session, tenant_1.id, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True
    )
    await async_db_session.commit()

    return {
        "tenant_1": tenant_1,
        "tenant_2": tenant_2,
        "doctor_1": doctor_1,
        "doctor_2": doctor_2,
        "receptionist_1": receptionist_1,
        "patient_1": patient_1,
        "patient_2": patient_2,
        "patient_3": patient_3,
        "att_1": att_1,
        "att_2": att_2,
        "att_p2": att_p2,
        "att_t2": att_t2,
        "work_item_1": work_item_1,
        "work_item_2": work_item_2,
        "care_session_1": care_session_1,
        "care_session_2": care_session_2,
    }


@pytest.mark.asyncio
async def test_feature_flag_gate_fails_closed(async_db_session, seed_data):
    """Mutations fail-closed with 404 when clinical_vnext_native_writes is OFF."""
    t1 = seed_data["tenant_1"]
    doc1 = seed_data["doctor_1"]
    pat1 = seed_data["patient_1"]
    att1 = seed_data["att_1"]

    # Disable flag
    await FeatureFlagService.set_tenant_override(
        async_db_session, t1.id, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, False
    )
    await async_db_session.commit()

    service = ClinicalAttachmentLinkService(async_db_session, t1.id, doc1)

    # create_attachment_link must fail 404
    with pytest.raises(HTTPException) as exc_info:
        await service.create_attachment_link(
            patient_id=pat1.id,
            data=schemas.ClinicalAttachmentLinkCreate(
                attachment_id=att1.id,
                tooth_key="16",
                purpose_code="PRE_OP_XRAY",
            ),
        )
    assert exc_info.value.status_code == 404
    assert "Clinical native writes are disabled" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_attachment_link_tooth_and_work_item(async_db_session, seed_data):
    """
    Test creating a context link associating an attachment with a tooth and work item.
    Proves G15-M01 (underlying attachment unchanged) and G15-M02 (context link created).
    """
    t1 = seed_data["tenant_1"]
    doc1 = seed_data["doctor_1"]
    pat1 = seed_data["patient_1"]
    att1 = seed_data["att_1"]
    wi1 = seed_data["work_item_1"]

    service = ClinicalAttachmentLinkService(async_db_session, t1.id, doc1)

    link_read = await service.create_attachment_link(
        patient_id=pat1.id,
        data=schemas.ClinicalAttachmentLinkCreate(
            attachment_id=att1.id,
            work_item_id=wi1.id,
            tooth_key="16",
            purpose_code=AttachmentPurposeCode.PRE_OP_XRAY.value,
            notes="Initial diagnostic radiograph for Tooth 16 RCT",
        ),
    )

    assert link_read.id is not None
    assert link_read.tenant_id == t1.id
    assert link_read.patient_id == pat1.id
    assert link_read.attachment_id == att1.id
    assert link_read.work_item_id == wi1.id
    assert link_read.tooth_key == "16"
    assert link_read.purpose_code == "PRE_OP_XRAY"
    assert link_read.filename == "periapical_tooth16.png"

    # Verify underlying attachment in DB was NOT modified or moved (G15-M01)
    db_att = (
        await async_db_session.execute(
            select(models.Attachment).where(models.Attachment.id == att1.id)
        )
    ).scalar_one()
    assert db_att.filename == "periapical_tooth16.png"
    assert db_att.file_path == "/storage/attachments/periapical_tooth16.png"
    assert db_att.patient_id == pat1.id


@pytest.mark.asyncio
async def test_pd05_purpose_code_allowlist_validation(async_db_session, seed_data):
    """Verify all 8 Decision PD05 canonical purpose codes are accepted and invalid codes rejected."""
    t1 = seed_data["tenant_1"]
    doc1 = seed_data["doctor_1"]
    pat1 = seed_data["patient_1"]
    att1 = seed_data["att_1"]

    service = ClinicalAttachmentLinkService(async_db_session, t1.id, doc1)

    # Test all 8 canonical purpose codes from PD05
    teeth = ["11", "12", "13", "14", "15", "16", "17", "18"]
    for idx, purpose in enumerate(CANONICAL_ATTACHMENT_PURPOSE_CODES):
        tooth = teeth[idx]
        link = await service.create_attachment_link(
            patient_id=pat1.id,
            data=schemas.ClinicalAttachmentLinkCreate(
                attachment_id=att1.id,
                tooth_key=tooth,
                purpose_code=purpose,
            ),
        )
        assert link.purpose_code == purpose

    # Test invalid purpose code rejected by Pydantic validation (422)
    with pytest.raises(Exception):
        schemas.ClinicalAttachmentLinkCreate(
            attachment_id=att1.id,
            tooth_key="21",
            purpose_code="INVALID_RANDOM_CODE",
        )


@pytest.mark.asyncio
async def test_clinical_context_and_fdi_validation(async_db_session, seed_data):
    """Verify at least one clinical context is required and tooth keys must be valid FDI."""
    att1 = seed_data["att_1"]

    # No clinical context provided -> raises ValueError
    with pytest.raises(ValueError) as exc_info:
        schemas.ClinicalAttachmentLinkCreate(
            attachment_id=att1.id,
            work_item_id=None,
            care_session_id=None,
            clinical_event_id=None,
            tooth_key=None,
            purpose_code="PRE_OP_XRAY",
        )
    assert "At least one clinical context" in str(exc_info.value)

    # Invalid FDI tooth key -> raises ValueError
    with pytest.raises(ValueError) as exc_info_fdi:
        schemas.ClinicalAttachmentLinkCreate(
            attachment_id=att1.id,
            tooth_key="99",  # Invalid FDI
            purpose_code="PRE_OP_XRAY",
        )
    assert "not a valid FDI tooth notation" in str(exc_info_fdi.value)


@pytest.mark.asyncio
async def test_tenant_and_patient_boundary_isolation(async_db_session, seed_data):
    """Verify strict tenant and patient boundary enforcement across all referenced entities."""
    t1 = seed_data["tenant_1"]
    doc1 = seed_data["doctor_1"]
    pat1 = seed_data["patient_1"]
    att1 = seed_data["att_1"]
    att_p2 = seed_data["att_p2"]
    att_t2 = seed_data["att_t2"]
    wi_p2 = seed_data["work_item_2"]
    cs_p2 = seed_data["care_session_2"]

    service = ClinicalAttachmentLinkService(async_db_session, t1.id, doc1)

    # 1. Cross-tenant attachment (att_t2 belongs to tenant 2) -> 404
    with pytest.raises(HTTPException) as exc_cross_tenant:
        await service.create_attachment_link(
            patient_id=pat1.id,
            data=schemas.ClinicalAttachmentLinkCreate(
                attachment_id=att_t2.id,
                tooth_key="16",
                purpose_code="PRE_OP_XRAY",
            ),
        )
    assert exc_cross_tenant.value.status_code == 404

    # 2. Cross-patient attachment (att_p2 belongs to patient 2) -> 404
    with pytest.raises(HTTPException) as exc_cross_patient_att:
        await service.create_attachment_link(
            patient_id=pat1.id,
            data=schemas.ClinicalAttachmentLinkCreate(
                attachment_id=att_p2.id,
                tooth_key="16",
                purpose_code="PRE_OP_XRAY",
            ),
        )
    assert exc_cross_patient_att.value.status_code == 404

    # 3. Cross-patient work item (wi_p2 belongs to patient 2) -> 404
    with pytest.raises(HTTPException) as exc_cross_patient_wi:
        await service.create_attachment_link(
            patient_id=pat1.id,
            data=schemas.ClinicalAttachmentLinkCreate(
                attachment_id=att1.id,
                work_item_id=wi_p2.id,
                purpose_code="PRE_OP_XRAY",
            ),
        )
    assert exc_cross_patient_wi.value.status_code == 404

    # 4. Cross-patient care session (cs_p2 belongs to patient 2) -> 404
    with pytest.raises(HTTPException) as exc_cross_patient_cs:
        await service.create_attachment_link(
            patient_id=pat1.id,
            data=schemas.ClinicalAttachmentLinkCreate(
                attachment_id=att1.id,
                care_session_id=cs_p2.id,
                purpose_code="PRE_OP_XRAY",
            ),
        )
    assert exc_cross_patient_cs.value.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_context_link_raises_409(async_db_session, seed_data):
    """Creating the exact same attachment context link twice raises 409 Conflict."""
    t1 = seed_data["tenant_1"]
    doc1 = seed_data["doctor_1"]
    pat1 = seed_data["patient_1"]
    att1 = seed_data["att_1"]

    service = ClinicalAttachmentLinkService(async_db_session, t1.id, doc1)

    # First link succeeds
    await service.create_attachment_link(
        patient_id=pat1.id,
        data=schemas.ClinicalAttachmentLinkCreate(
            attachment_id=att1.id,
            tooth_key="16",
            purpose_code="PRE_OP_XRAY",
        ),
    )

    # Second link with identical context raises 409
    with pytest.raises(HTTPException) as exc_info:
        await service.create_attachment_link(
            patient_id=pat1.id,
            data=schemas.ClinicalAttachmentLinkCreate(
                attachment_id=att1.id,
                tooth_key="16",
                purpose_code="PRE_OP_XRAY",
            ),
        )
    assert exc_info.value.status_code == 409
    assert "already exists" in exc_info.value.detail


@pytest.mark.asyncio
async def test_list_and_delete_attachment_link_g15_m01(async_db_session, seed_data):
    """
    Test listing attachment links with filtering, and deleting a link.
    Proves G15-M01: deleting link NEVER deletes or alters the underlying Attachment row.
    """
    t1 = seed_data["tenant_1"]
    doc1 = seed_data["doctor_1"]
    pat1 = seed_data["patient_1"]
    att1 = seed_data["att_1"]
    att2 = seed_data["att_2"]
    cs1 = seed_data["care_session_1"]

    service = ClinicalAttachmentLinkService(async_db_session, t1.id, doc1)

    # Create 2 links
    link1 = await service.create_attachment_link(
        patient_id=pat1.id,
        data=schemas.ClinicalAttachmentLinkCreate(
            attachment_id=att1.id,
            tooth_key="16",
            purpose_code="PRE_OP_XRAY",
        ),
    )
    link2 = await service.create_attachment_link(
        patient_id=pat1.id,
        data=schemas.ClinicalAttachmentLinkCreate(
            attachment_id=att2.id,
            care_session_id=cs1.id,
            tooth_key="16",
            purpose_code="WORKING_LENGTH_XRAY",
        ),
    )

    # List all links
    all_links = await service.list_attachment_links(patient_id=pat1.id)
    assert len(all_links) == 2

    # Filter by purpose code
    wl_links = await service.list_attachment_links(
        patient_id=pat1.id,
        filters=schemas.ClinicalAttachmentLinkFilter(purpose_code="WORKING_LENGTH_XRAY"),
    )
    assert len(wl_links) == 1
    assert wl_links[0].id == link2.id

    # Filter by care session
    cs_links = await service.list_attachment_links(
        patient_id=pat1.id,
        filters=schemas.ClinicalAttachmentLinkFilter(care_session_id=cs1.id),
    )
    assert len(cs_links) == 1
    assert cs_links[0].id == link2.id

    # Get single link
    retrieved = await service.get_attachment_link(patient_id=pat1.id, link_id=link1.id)
    assert retrieved.id == link1.id
    assert retrieved.tooth_key == "16"

    # Delete link1
    del_res = await service.delete_attachment_link(patient_id=pat1.id, link_id=link1.id)
    assert del_res["deleted"] is True

    # Link1 is gone
    with pytest.raises(HTTPException) as exc_info:
        await service.get_attachment_link(patient_id=pat1.id, link_id=link1.id)
    assert exc_info.value.status_code == 404

    # CRITICAL: Underlying att1 is STILL in database untouched (G15-M01)
    db_att1 = (
        await async_db_session.execute(
            select(models.Attachment).where(models.Attachment.id == att1.id)
        )
    ).scalar_one_or_none()
    assert db_att1 is not None
    assert db_att1.filename == "periapical_tooth16.png"
    assert db_att1.patient_id == pat1.id


@pytest.mark.asyncio
async def test_g15_m03_m04_m05_individual_and_composite_context_linking(async_db_session, seed_data):
    """
    Test G15-M03 (link to tooth), G15-M04 (link to work item), and G15-M05 (link to care session).
    Verifies that attachments can be linked to any combination of these contexts and queried reliably.
    """
    t1 = seed_data["tenant_1"]
    doc1 = seed_data["doctor_1"]
    pat1 = seed_data["patient_1"]
    att1 = seed_data["att_1"]
    att2 = seed_data["att_2"]
    wi1 = seed_data["work_item_1"]
    cs1 = seed_data["care_session_1"]

    service = ClinicalAttachmentLinkService(async_db_session, t1.id, doc1)

    # G15-M03: Link attachment to tooth only
    link_tooth = await service.create_attachment_link(
        patient_id=pat1.id,
        data=schemas.ClinicalAttachmentLinkCreate(
            attachment_id=att1.id,
            tooth_key="16",
            purpose_code=AttachmentPurposeCode.PRE_OP_XRAY.value,
            notes="G15-M03 tooth-only link",
        ),
    )
    assert link_tooth.tooth_key == "16"
    assert link_tooth.work_item_id is None
    assert link_tooth.care_session_id is None

    # G15-M04: Link attachment to work item
    link_wi = await service.create_attachment_link(
        patient_id=pat1.id,
        data=schemas.ClinicalAttachmentLinkCreate(
            attachment_id=att2.id,
            work_item_id=wi1.id,
            purpose_code=AttachmentPurposeCode.WORKING_LENGTH_XRAY.value,
            notes="G15-M04 work-item link",
        ),
    )
    assert link_wi.work_item_id == wi1.id
    assert link_wi.tooth_key is None

    # G15-M05: Composite link to both tooth 16 and care session 1 (Acceptance Scenario)
    link_composite = await service.create_attachment_link(
        patient_id=pat1.id,
        data=schemas.ClinicalAttachmentLinkCreate(
            attachment_id=att1.id,
            tooth_key="16",
            care_session_id=cs1.id,
            purpose_code=AttachmentPurposeCode.INTRAORAL_PHOTO.value,
            notes="G15-M05 composite link to tooth and active session",
        ),
    )
    assert link_composite.tooth_key == "16"
    assert link_composite.care_session_id == cs1.id

    # Query by tooth_key="16" (finds both link_tooth and link_composite)
    tooth_links = await service.list_attachment_links(
        patient_id=pat1.id,
        filters=schemas.ClinicalAttachmentLinkFilter(tooth_key="16"),
    )
    assert len(tooth_links) == 2
    assert {lnk.id for lnk in tooth_links} == {link_tooth.id, link_composite.id}

    # Query by care_session_id=cs1.id (finds link_composite)
    cs_links = await service.list_attachment_links(
        patient_id=pat1.id,
        filters=schemas.ClinicalAttachmentLinkFilter(care_session_id=cs1.id),
    )
    assert len(cs_links) == 1
    assert cs_links[0].id == link_composite.id

    # Query by work_item_id=wi1.id (finds link_wi)
    wi_links = await service.list_attachment_links(
        patient_id=pat1.id,
        filters=schemas.ClinicalAttachmentLinkFilter(work_item_id=wi1.id),
    )
    assert len(wi_links) == 1
    assert wi_links[0].id == link_wi.id


def test_router_endpoints_and_rbac(client, seed_data):
    """
    Test FastAPI router endpoints for clinical attachment links.
    Verifies RBAC permissions:
    - Receptionist with CLINICAL_READ can list/get but cannot create/delete (403).
    - Doctor with CLINICAL_WRITE can create and delete links (200).
    """
    from backend.auth import create_access_token

    t1 = seed_data["tenant_1"]
    doc1 = seed_data["doctor_1"]
    recep1 = seed_data["receptionist_1"]
    pat1 = seed_data["patient_1"]
    att1 = seed_data["att_1"]

    doc_headers = {
        "Authorization": f"Bearer {create_access_token(data={'sub': doc1.username, 'tenant_id': t1.id, 'role': doc1.role})}"
    }
    recep_headers = {
        "Authorization": f"Bearer {create_access_token(data={'sub': recep1.username, 'tenant_id': t1.id, 'role': recep1.role})}"
    }

    payload = {
        "attachment_id": att1.id,
        "tooth_key": "24",
        "purpose_code": "PRE_OP_XRAY",
        "notes": "Route contract test",
    }

    # 1. Receptionist tries to create link -> 403 Forbidden (requires CLINICAL_WRITE)
    res_recep_post = client.post(
        f"/api/v1/patients/{pat1.id}/clinical-attachment-links",
        json=payload,
        headers=recep_headers,
    )
    assert res_recep_post.status_code == 403

    # 2. Doctor creates link -> 200 OK
    res_doc_post = client.post(
        f"/api/v1/patients/{pat1.id}/clinical-attachment-links",
        json=payload,
        headers=doc_headers,
    )
    assert res_doc_post.status_code == 200
    created_link = res_doc_post.json()["data"]
    link_id = created_link["id"]
    assert created_link["tooth_key"] == "24"
    assert created_link["purpose_code"] == "PRE_OP_XRAY"
    assert created_link["filename"] == "periapical_tooth16.png"

    # 3. Receptionist lists links -> 200 OK (has CLINICAL_READ)
    res_recep_get = client.get(
        f"/api/v1/patients/{pat1.id}/clinical-attachment-links",
        headers=recep_headers,
    )
    assert res_recep_get.status_code == 200
    links_data = res_recep_get.json()["data"]
    assert any(item["id"] == link_id for item in links_data)

    # 4. Receptionist gets single link -> 200 OK
    res_recep_single = client.get(
        f"/api/v1/patients/{pat1.id}/clinical-attachment-links/{link_id}",
        headers=recep_headers,
    )
    assert res_recep_single.status_code == 200
    assert res_recep_single.json()["data"]["id"] == link_id

    # 5. Receptionist tries to delete link -> 403 Forbidden
    res_recep_del = client.delete(
        f"/api/v1/patients/{pat1.id}/clinical-attachment-links/{link_id}",
        headers=recep_headers,
    )
    assert res_recep_del.status_code == 403

    # 6. Doctor deletes link -> 200 OK
    res_doc_del = client.delete(
        f"/api/v1/patients/{pat1.id}/clinical-attachment-links/{link_id}",
        headers=doc_headers,
    )
    assert res_doc_del.status_code == 200
    assert res_doc_del.json()["data"]["deleted"] is True

