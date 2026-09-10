"""Regression coverage for tenant-safe permanent patient deletion."""

import pytest
from sqlalchemy import select

from backend import models
from backend.core.tenancy import clear_tenant_context, set_current_tenant_id
from backend.crud.patient import (
    PATIENT_CLINICAL_DELETE_ORDER,
    delete_patient_permanently,
)
from backend.services.import_service import delete_tenant_data


def test_delete_order_covers_every_direct_clinical_patient_foreign_key():
    direct_patient_models = {
        mapper.class_
        for mapper in models.Base.registry.mappers
        if mapper.class_.__module__ == "backend.models.clinical_core"
        and "patient_id" in mapper.local_table.c
        and any(
            foreign_key.target_fullname == "patients.id"
            for foreign_key in mapper.local_table.c.patient_id.foreign_keys
        )
    }

    assert set(PATIENT_CLINICAL_DELETE_ORDER) == direct_patient_models


@pytest.mark.asyncio
async def test_full_replacement_cleanup_removes_only_matching_tenant_rows(
    async_db_session,
):
    tenant_a = models.Tenant(name="Import Replace Clinic A")
    tenant_b = models.Tenant(name="Import Replace Clinic B")
    async_db_session.add_all([tenant_a, tenant_b])
    await async_db_session.flush()

    patient_a = models.Patient(
        tenant_id=tenant_a.id,
        name="Replace Me",
        age=30,
        phone="01000000011",
        medical_history="None",
        notes="",
    )
    patient_b = models.Patient(
        tenant_id=tenant_b.id,
        name="Keep Me",
        age=31,
        phone="01000000012",
        medical_history="None",
        notes="",
    )
    async_db_session.add_all([patient_a, patient_b])
    await async_db_session.flush()

    item_a = models.ClinicalWorkItem(
        tenant_id=tenant_a.id,
        patient_id=patient_a.id,
        kind="procedure",
        code="PROS_CROWN",
    )
    item_b = models.ClinicalWorkItem(
        tenant_id=tenant_b.id,
        patient_id=patient_b.id,
        kind="procedure",
        code="PROS_CROWN",
    )
    async_db_session.add_all([item_a, item_b])
    await async_db_session.commit()

    patient_a_id = patient_a.id
    patient_b_id = patient_b.id
    item_b_id = item_b.id
    tenant_a_id = tenant_a.id
    tenant_b_id = tenant_b.id
    token = set_current_tenant_id(tenant_a_id)
    try:
        await delete_tenant_data(async_db_session, tenant_a_id)
        await async_db_session.commit()
    finally:
        clear_tenant_context(tenant_token=token)

    remaining_a = await async_db_session.execute(
        select(models.ClinicalWorkItem).where(
            models.ClinicalWorkItem.tenant_id == tenant_a_id
        )
    )
    remaining_b = await async_db_session.execute(
        select(models.ClinicalWorkItem).where(
            models.ClinicalWorkItem.tenant_id == tenant_b_id
        )
    )
    assert remaining_a.scalars().all() == []
    assert [item.id for item in remaining_b.scalars().all()] == [item_b_id]
    assert await async_db_session.get(models.Patient, patient_a_id) is None
    assert await async_db_session.get(models.Patient, patient_b_id) is not None


@pytest.mark.asyncio
async def test_permanent_delete_removes_only_matching_tenant_clinical_rows(
    async_db_session,
):
    tenant_a = models.Tenant(name="Hard Delete Clinic A")
    tenant_b = models.Tenant(name="Hard Delete Clinic B")
    async_db_session.add_all([tenant_a, tenant_b])
    await async_db_session.flush()

    patient_a = models.Patient(
        tenant_id=tenant_a.id,
        name="Delete Me",
        age=30,
        phone="01000000001",
        medical_history="None",
        notes="",
    )
    patient_b = models.Patient(
        tenant_id=tenant_b.id,
        name="Keep Me",
        age=31,
        phone="01000000002",
        medical_history="None",
        notes="",
    )
    async_db_session.add_all([patient_a, patient_b])
    await async_db_session.flush()

    work_item_a = models.ClinicalWorkItem(
        tenant_id=tenant_a.id,
        patient_id=patient_a.id,
        kind="procedure",
        code="CROWN",
    )
    work_item_b = models.ClinicalWorkItem(
        tenant_id=tenant_b.id,
        patient_id=patient_b.id,
        kind="procedure",
        code="CROWN",
    )
    coverage_a = models.ClinicalProjectionCoverage(
        tenant_id=tenant_a.id,
        patient_id=patient_a.id,
        domain="treatments",
        status="PARTIAL",
    )
    async_db_session.add_all([work_item_a, work_item_b, coverage_a])
    await async_db_session.commit()

    patient_a_id = patient_a.id
    patient_b_id = patient_b.id
    tenant_a_id = tenant_a.id
    tenant_b_id = tenant_b.id
    token = set_current_tenant_id(tenant_a_id)
    try:
        deleted = await delete_patient_permanently(
            async_db_session,
            patient_a_id,
            tenant_a_id,
        )
    finally:
        clear_tenant_context(tenant_token=token)

    assert deleted is not None
    assert await async_db_session.get(models.Patient, patient_a_id) is None
    assert await async_db_session.get(models.Patient, patient_b_id) is not None

    remaining_a = await async_db_session.execute(
        select(models.ClinicalWorkItem).where(
            models.ClinicalWorkItem.tenant_id == tenant_a_id,
            models.ClinicalWorkItem.patient_id == patient_a_id,
        )
    )
    assert remaining_a.scalars().all() == []

    remaining_b = await async_db_session.execute(
        select(models.ClinicalWorkItem).where(
            models.ClinicalWorkItem.tenant_id == tenant_b_id,
            models.ClinicalWorkItem.patient_id == patient_b_id,
        )
    )
    assert [item.id for item in remaining_b.scalars().all()] == [work_item_b.id]
