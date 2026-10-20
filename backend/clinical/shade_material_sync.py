"""
Shade and Material Synchronization Rules (Slice S29 / G12-M13).

Provides bidirectional synchronization of shade and material between
clinical work item observations (chairside care sessions) and active lab orders:
- G12-M10: Map lab order status per Decision D4.
- G12-M11: Reflect lab state in work item without mutation.
- G12-M12: Prevent auto-complete when lab is ready (D4 invariant).
- G12-M13: Sync shade/material updates between work item observations and open lab orders.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models


SHADE_OBSERVATION_CODES = frozenset({"color_shade", "shade", "tooth_shade"})
MATERIAL_OBSERVATION_CODES = frozenset({"material", "material_type", "prosthetic_material"})
COMBINED_OBSERVATION_CODES = frozenset({"shade_material", "shade_and_material"})


async def sync_observation_to_open_lab_orders(
    db: AsyncSession,
    tenant_id: int,
    work_item_id: Optional[int],
    observation_code: str,
    structured_value: Optional[dict[str, Any]] = None,
    notes: Optional[str] = None,
) -> Sequence[models.LabOrder]:
    """
    When a shade or material observation is recorded on a work item,
    sync the values to any open (status != 'completed' and status != 'cancelled')
    lab orders linked to that work item (G12-M13).
    """
    if not work_item_id:
        return ()

    code_lower = observation_code.strip().lower()
    if (
        code_lower not in SHADE_OBSERVATION_CODES
        and code_lower not in MATERIAL_OBSERVATION_CODES
        and code_lower not in COMBINED_OBSERVATION_CODES
    ):
        return ()

    structured = structured_value or {}
    extracted_shade: Optional[str] = None
    extracted_material: Optional[str] = None

    if code_lower in SHADE_OBSERVATION_CODES:
        extracted_shade = structured.get("shade") or structured.get("color_shade")
        if not extracted_shade and notes:
            extracted_shade = notes.strip()
    elif code_lower in MATERIAL_OBSERVATION_CODES:
        extracted_material = structured.get("material") or structured.get("material_type")
        if not extracted_material and notes:
            extracted_material = notes.strip()
    elif code_lower in COMBINED_OBSERVATION_CODES:
        extracted_shade = structured.get("shade") or structured.get("color_shade")
        extracted_material = structured.get("material") or structured.get("material_type")
        if not extracted_shade and notes and "shade:" in notes.lower():
            # naive extraction if provided in notes
            pass

    if not extracted_shade and not extracted_material:
        return ()

    # Query open lab orders linked to this work item
    stmt = (
        select(models.LabOrder)
        .where(
            models.LabOrder.tenant_id == tenant_id,
            models.LabOrder.work_item_id == work_item_id,
            models.LabOrder.status.not_in(["completed", "cancelled"]),
        )
    )
    result = await db.execute(stmt)
    open_orders = result.scalars().all()

    for order in open_orders:
        if extracted_shade:
            order.shade = extracted_shade
        if extracted_material:
            order.material = extracted_material

    return open_orders


async def sync_lab_order_to_active_care_session_observations(
    db: AsyncSession,
    tenant_id: int,
    order: models.LabOrder,
    actor_user_id: Optional[int] = None,
) -> Sequence[models.CareObservation]:
    """
    When an open lab order is updated with shade or material,
    sync to any in-progress care session for the patient that includes
    this work item (G12-M13).
    """
    if not order.work_item_id or (not order.shade and not order.material):
        return ()

    # Check for active in-progress care session for the patient
    cs_stmt = (
        select(models.CareSession)
        .where(
            models.CareSession.tenant_id == tenant_id,
            models.CareSession.patient_id == order.patient_id,
            models.CareSession.status == "in_progress",
        )
        .order_by(models.CareSession.id.desc())
    )
    cs_res = await db.execute(cs_stmt)
    active_session = cs_res.scalars().first()
    if not active_session:
        return ()

    synced_obs: list[models.CareObservation] = []
    now = datetime.now(timezone.utc)

    # 1. Sync shade observation
    if order.shade:
        obs_stmt = (
            select(models.CareObservation)
            .where(
                models.CareObservation.tenant_id == tenant_id,
                models.CareObservation.care_session_id == active_session.id,
                models.CareObservation.work_item_id == order.work_item_id,
                models.CareObservation.observation_code.in_(["color_shade", "shade"]),
            )
        )
        obs_res = await db.execute(obs_stmt)
        existing_obs = obs_res.scalars().first()

        if existing_obs:
            curr_struct = dict(existing_obs.structured_value or {})
            curr_struct["shade"] = order.shade
            existing_obs.structured_value = curr_struct
            synced_obs.append(existing_obs)
        else:
            new_obs = models.CareObservation(
                tenant_id=tenant_id,
                patient_id=order.patient_id,
                care_session_id=active_session.id,
                work_item_id=order.work_item_id,
                observation_code="color_shade",
                tooth_key=order.tooth_number,
                structured_value={"shade": order.shade},
                notes=order.shade,
                recorded_at=now,
                recorded_by_user_id=actor_user_id or order.doctor_id,
            )
            db.add(new_obs)
            synced_obs.append(new_obs)

    # 2. Sync material observation
    if order.material:
        mat_stmt = (
            select(models.CareObservation)
            .where(
                models.CareObservation.tenant_id == tenant_id,
                models.CareObservation.care_session_id == active_session.id,
                models.CareObservation.work_item_id == order.work_item_id,
                models.CareObservation.observation_code.in_(["material", "material_type"]),
            )
        )
        mat_res = await db.execute(mat_stmt)
        existing_mat_obs = mat_res.scalars().first()

        if existing_mat_obs:
            curr_struct = dict(existing_mat_obs.structured_value or {})
            curr_struct["material"] = order.material
            existing_mat_obs.structured_value = curr_struct
            synced_obs.append(existing_mat_obs)
        else:
            new_mat_obs = models.CareObservation(
                tenant_id=tenant_id,
                patient_id=order.patient_id,
                care_session_id=active_session.id,
                work_item_id=order.work_item_id,
                observation_code="material",
                tooth_key=order.tooth_number,
                structured_value={"material": order.material},
                notes=order.material,
                recorded_at=now,
                recorded_by_user_id=actor_user_id or order.doctor_id,
            )
            db.add(new_mat_obs)
            synced_obs.append(new_mat_obs)

    return synced_obs
