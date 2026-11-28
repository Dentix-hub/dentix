"""
Material Resolution Service

Resolves which materials should be used for a given procedure based on:
1. Global defaults from ProcedureMaterialWeight (category-level)
2. Clinic's specific materials in those categories
3. Active sessions for divisible materials
4. Doctor history/preferences
"""

import logging
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, func, select

from backend.models import inventory as inv_models
from backend.models import clinical as clinical_models

logger = logging.getLogger(__name__)


class MaterialResolutionService:
    """
    Resolves materials for a procedure using this priority:
    1. Active Session → auto-select if DIVISIBLE has open session
    2. Doctor History → what this doctor used before
    3. Clinic Default → first material in category
    4. Manual → user must pick
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _normalize_name(self, name: str) -> str:
        if not name:
            return ""
        import re
        # 1. Standardize all separators (dashes, underscores, multiple spaces) to a single space
        n = re.sub(r'[\s\-_–—]+', ' ', name).lower()
        # 2. Split into individual words/parts
        parts = [p.strip() for p in n.split()]
        # 3. Sort parts to handle "Arabic - English" vs "English - Arabic" or any other order
        parts.sort()
        # 4. Join back with no spaces for a canonical comparison string
        return "".join(parts)

    async def resolve_materials_for_procedure(
        self,
        procedure_id: int,
        tenant_id: int,
    ) -> List[Dict]:
        """
        Returns list of suggested materials with confidence levels.
        """
        suggestions = []

        # 1. Resolve Procedure scoped strictly to current tenant or global catalog
        proc_result = await self.db.execute(
            select(clinical_models.Procedure).filter(
                clinical_models.Procedure.id == procedure_id,
                or_(
                    clinical_models.Procedure.tenant_id == tenant_id,
                    clinical_models.Procedure.tenant_id.is_(None),
                ),
            )
        )
        proc = proc_result.scalars().first()
        if not proc:
            logger.debug("Procedure %s not found for tenant %s", procedure_id, tenant_id)
            return suggestions

        proc_norm = self._normalize_name(proc.name)
        logger.debug("Resolving materials for procedure_id=%s (%r -> %r)", procedure_id, proc.name, proc_norm)

        # 2. Get all potential weights (Global + Tenant), including category-level and material-level rules
        stmt_weights = (
            select(inv_models.ProcedureMaterialWeight)
            .options(
                joinedload(inv_models.ProcedureMaterialWeight.category),
                joinedload(inv_models.ProcedureMaterialWeight.procedure),
                joinedload(inv_models.ProcedureMaterialWeight.material).joinedload(
                    inv_models.Material.category
                ),
            )
            .filter(
                or_(
                    inv_models.ProcedureMaterialWeight.tenant_id == tenant_id,
                    inv_models.ProcedureMaterialWeight.tenant_id.is_(None),
                ),
                or_(
                    inv_models.ProcedureMaterialWeight.category_id.isnot(None),
                    inv_models.ProcedureMaterialWeight.material_id.isnot(None),
                ),
            )
        )
        result_weights = await self.db.execute(stmt_weights)
        all_potential_weights = result_weights.scalars().all()

        # Filter and deduplicate (Tenant overrides Global)
        weights_by_cat = {}
        weights_by_material = {}

        matches_found = 0
        for w in all_potential_weights:
            w_proc_name = w.procedure.name if w.procedure else ""
            w_norm = self._normalize_name(w_proc_name)

            if w.procedure_id == procedure_id or w_norm == proc_norm:
                matches_found += 1
                if w.category_id is not None:
                    cat_id = w.category_id
                    # Priority: Tenant-specific weight > Global weight
                    if cat_id not in weights_by_cat or w.tenant_id is not None:
                        weights_by_cat[cat_id] = w
                elif w.material_id is not None:
                    mat = w.material
                    if mat and mat.tenant_id == tenant_id and not mat.is_deleted:
                        if mat.id not in weights_by_material or w.tenant_id is not None:
                            weights_by_material[mat.id] = w

        tenant_material_cat_ids = {
            w.material.category_id
            for w in weights_by_material.values()
            if w.tenant_id is not None and w.material and w.material.category_id is not None
        }
        final_weights = [
            w
            for cat_id, w in weights_by_cat.items()
            if w.tenant_id is not None or cat_id not in tenant_material_cat_ids
        ]

        logger.debug(
            "Material resolution matches=%s categories=%s direct_materials=%s",
            matches_found,
            len(final_weights),
            len(weights_by_material),
        )

        if not final_weights and not weights_by_material:
            return suggestions

        # Fetch all active sessions for this tenant once to avoid N+1 queries
        stmt_sessions = (
            select(inv_models.MaterialSession)
            .join(inv_models.MaterialSession.stock_item)
            .filter(
                inv_models.StockItem.tenant_id == tenant_id,
                inv_models.MaterialSession.status == "ACTIVE"
            )
            .options(
                joinedload(inv_models.MaterialSession.stock_item)
                .joinedload(inv_models.StockItem.batch)
            )
        )
        result_sessions = await self.db.execute(stmt_sessions)
        active_sessions = result_sessions.scalars().all()
        # Map material_id -> active_session
        session_map = {s.stock_item.batch.material_id: s for s in active_sessions}

        emitted_material_ids = set()

        # 3. For each category weight, resolve actual materials
        for weight_record in final_weights:
            category = weight_record.category
            if not category:
                continue

            # Get clinic materials in this category
            stmt_materials = (
                select(inv_models.Material)
                .filter(
                    inv_models.Material.category_id == category.id,
                    inv_models.Material.tenant_id == tenant_id,
                    inv_models.Material.is_deleted == False,  # noqa: E712
                )
            )
            result_materials = await self.db.execute(stmt_materials)
            clinic_materials = result_materials.scalars().all()

            # Check for active sessions (for DIVISIBLE materials)
            active_session = None
            session_material = None

            if category.default_type == "DIVISIBLE" and clinic_materials:
                # Look for active sessions in pre-fetched map
                for material in clinic_materials:
                    session = session_map.get(material.id)
                    if session:
                        active_session = session
                        session_material = material
                        break

            # Build suggestion
            if clinic_materials:
                # Primary: first material (or one with active session)
                primary = session_material or clinic_materials[0]
                alternatives = [m for m in clinic_materials if m.id != primary.id]

                confidence = 0.9 if active_session else 0.7
                reason = (
                    "جلسة مفتوحة (استهلاك افتراضي)"
                    if active_session
                    else f"مادة العيادة في فئة {category.name_ar}"
                )
            else:
                # No clinic materials in this category
                primary = None
                alternatives = []
                confidence = 0.3
                reason = f"لا توجد مواد في فئة {category.name_ar} — يجب إضافة مادة"

            if primary:
                emitted_material_ids.add(primary.id)

            suggestion = {
                "category_id": category.id,
                "category_name_en": category.name_en,
                "category_name_ar": category.name_ar,
                "material_type": category.default_type,
                "base_unit": category.default_unit,
                "weight": weight_record.weight,
                "material_id": primary.id if primary else None,
                "material_name": primary.name if primary else None,
                "brand": primary.brand if primary else None,
                "alternatives": [
                    {"id": m.id, "name": m.name, "brand": m.brand}
                    for m in alternatives
                ],
                "has_active_session": active_session is not None,
                "session_id": active_session.id if active_session else None,
                "current_uses": active_session.current_uses if active_session else 0,
                "max_uses": primary.max_uses if (primary and hasattr(primary, 'max_uses')) else 0,
                "confidence": confidence,
                "reason": reason,
                "is_direct_material": False,
            }
            suggestions.append(suggestion)

        # 4. Append explicit material-specific weights (e.g. linked via Settings -> Procedures)
        for weight_record in weights_by_material.values():
            mat = weight_record.material
            if not mat or mat.id in emitted_material_ids:
                continue
            emitted_material_ids.add(mat.id)
            active_session = session_map.get(mat.id)
            mat_type = mat.type or (mat.category.default_type if mat.category else "NON_DIVISIBLE")
            cat_name_ar = mat.category.name_ar if mat.category else mat.name
            cat_name_en = mat.category.name_en if mat.category else mat.name
            suggestions.append({
                "category_id": mat.category_id,
                "category_name_en": cat_name_en,
                "category_name_ar": cat_name_ar,
                "material_type": mat_type,
                "base_unit": mat.base_unit,
                "weight": weight_record.weight,
                "material_id": mat.id,
                "material_name": mat.name,
                "brand": mat.brand,
                "alternatives": [],
                "has_active_session": active_session is not None,
                "session_id": active_session.id if active_session else None,
                "current_uses": active_session.current_uses if active_session else 0,
                "max_uses": getattr(mat, "max_uses", 0) or 0,
                "confidence": 0.95 if active_session else 0.85,
                "reason": (
                    "جلسة مفتوحة (استهلاك افتراضي)"
                    if active_session
                    else f"مادة مرتبطة بالإجراء: {mat.name}"
                ),
                "is_direct_material": True,
            })

        return suggestions

    async def get_doctor_preferred_material(
        self,
        doctor_id: int,
        category_id: int,
        tenant_id: int,
    ) -> Optional[inv_models.Material]:
        """
        Get the material this doctor used most frequently in this category.
        """

        # Query TreatmentMaterialUsage joined to Material to find most used
        stmt_usage = (
            select(
                inv_models.TreatmentMaterialUsage.material_id,
                func.count(inv_models.TreatmentMaterialUsage.id).label("usage_count"),
            )
            .join(inv_models.Material)
            .filter(
                inv_models.Material.category_id == category_id,
                inv_models.Material.tenant_id == tenant_id,
                inv_models.Material.is_deleted == False,  # noqa: E712
                inv_models.TreatmentMaterialUsage.tenant_id == tenant_id,
            )
            .group_by(inv_models.TreatmentMaterialUsage.material_id)
            .order_by(func.count(inv_models.TreatmentMaterialUsage.id).desc())
        )
        result_usage = await self.db.execute(stmt_usage)
        result = result_usage.first()

        if result:
            material_id = result[0]
            stmt_material = select(inv_models.Material).filter(inv_models.Material.id == material_id)
            result_material = await self.db.execute(stmt_material)
            return result_material.scalars().first()
        return None
