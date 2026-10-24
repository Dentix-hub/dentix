"""
Clinical Charges Router (Slice S33).

HTTP endpoints for:
- Patient clinical charges and work-item billing projection (G14-M03, G14-M12).
  Gated by clinical_vnext_finance_read.
- Reception actions: mark pending charge as invoiced or voided (D5).
  Gated by clinical_vnext_native_writes.
"""

from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.core.permissions import Permission, require_permission
from backend.core.response import StandardResponse, success_response
from backend.core.tenant_context import require_tenant_id
from backend.database import get_async_db
from backend.services.clinical_charge_service import ClinicalChargeService

router = APIRouter(tags=["Clinical Charges"])


@router.get(
    "/patients/{patient_id}/clinical-charges",
    response_model=StandardResponse[schemas.PatientClinicalChargesResponse],
    summary="Get patient clinical charges and billing projection",
    description="Retrieve clinical charges and work-item billing projection for a patient. Gated by clinical_vnext_finance_read.",
)
async def get_patient_clinical_charges(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.RECEIVABLE_READ)),
):
    tenant_id = require_tenant_id(current_user)
    service = ClinicalChargeService(db, tenant_id, current_user)
    charges, projection = await service.get_patient_clinical_charges(patient_id)
    return success_response(
        data=schemas.PatientClinicalChargesResponse(
            charges=[schemas.ClinicalChargeRead.model_validate(c) for c in charges],
            projection=[schemas.WorkItemBillingProjectionItem.model_validate(p) for p in projection],
        ),
        message="Patient clinical charges retrieved successfully",
    )


@router.post(
    "/clinical-charges/{charge_id}/invoice",
    response_model=StandardResponse[schemas.ClinicalChargeRead],
    summary="Mark clinical charge as invoiced",
    description="Reception marker moving charge status from pending to invoiced. Gated by clinical_vnext_native_writes.",
)
async def invoice_clinical_charge(
    charge_id: int,
    payload: Optional[schemas.ClinicalChargeActionRequest] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.PAYMENT_CREATE)),
):
    tenant_id = require_tenant_id(current_user)
    service = ClinicalChargeService(db, tenant_id, current_user)
    expected_version_id = payload.expected_version_id if payload else None
    notes = payload.notes if payload else None
    charge = await service.mark_charge_invoiced(
        charge_id, expected_version_id=expected_version_id, notes=notes
    )
    return success_response(
        data=schemas.ClinicalChargeRead.model_validate(charge),
        message="Clinical charge marked as invoiced successfully",
    )


@router.post(
    "/clinical-charges/{charge_id}/void",
    response_model=StandardResponse[schemas.ClinicalChargeRead],
    summary="Mark clinical charge as voided",
    description="Reception marker moving charge status from pending to voided. Gated by clinical_vnext_native_writes.",
)
async def void_clinical_charge(
    charge_id: int,
    payload: Optional[schemas.ClinicalChargeActionRequest] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.PAYMENT_VOID)),
):
    tenant_id = require_tenant_id(current_user)
    service = ClinicalChargeService(db, tenant_id, current_user)
    expected_version_id = payload.expected_version_id if payload else None
    notes = payload.notes if payload else None
    charge = await service.mark_charge_voided(
        charge_id, expected_version_id=expected_version_id, notes=notes
    )
    return success_response(
        data=schemas.ClinicalChargeRead.model_validate(charge),
        message="Clinical charge marked as voided successfully",
    )
