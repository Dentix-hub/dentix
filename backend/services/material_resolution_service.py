"""
Material Resolution Service

Resolves which materials should be used for a given procedure based on:
1. Global defaults from ProcedureMaterialWeight (category-level)
2. Clinic's specific materials in those categories
3. Active sessions for divisible materials
4. Doctor history/preferences
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func

from backend.models import inventory as inv_models
from backend.models import clinical as clinical_models


class MaterialResolutionService:
    """
    Resolves materials for a procedure using this priority:
    1. Active Session → auto-select if DIVISIBLE has open session
    2. Doctor History → what this doctor used before
    3. Clinic Default → first material in category
    4. Manual → user must pick
    """

    def __init__(self, db: Session):
        self.db = db

    def _normalize_name(self, name: str) -> str:
        if not name:
            return ""
        # 1. Standardize dashes (replace em-dash, en-dash, double-hyphen with single hyphen)
        import re
        n = re.sub(r'[–—]|--', '-', name)
        # 2. Split by dash and sort parts (to handle reversed "Arabic - English" vs "English - Arabic")
        parts = [p.strip().lower() for p in n.split('-')]
        parts.sort()
        # 3. Join back with a single space
        return " ".join(parts).strip()

    def resolve_materials_for_procedure(
        self,
        procedure_id: int,
        tenant_id: int,
    ) -> List[Dict]:
        """
        Returns list of suggested materials with confidence levels.
        """
        suggestions = []

        # 1. Resolve Procedure
        proc = self.db.query(clinical_models.Procedure).filter(clinical_models.Procedure.id == procedure_id).first()
        if not proc:
            return suggestions

        proc_norm = self._normalize_name(proc.name)

        # 2. Get all potential weights (Global + Tenant)
        # We fetch all global weights and tenant weights once
        # and then filter by normalized name in Python for maximum robustness
        all_potential_weights = (
            self.db.query(inv_models.ProcedureMaterialWeight)
            .options(joinedload(inv_models.ProcedureMaterialWeight.category))
            .join(clinical_models.Procedure)
            .filter(
                or_(
                    inv_models.ProcedureMaterialWeight.tenant_id == tenant_id,
                    inv_models.ProcedureMaterialWeight.tenant_id.is_(None)
                ),
                inv_models.ProcedureMaterialWeight.category_id.isnot(None),
            )
            .all()
        )

        # Filter and deduplicate (Tenant overrides Global)
        # weight_key = (category_id, normalized_proc_name)
        weights_by_cat = {}
        
        for w in all_potential_weights:
            w_proc_name = w.procedure.name if w.procedure else ""
            if w.procedure_id == procedure_id or self._normalize_name(w_proc_name) == proc_norm:
                cat_id = w.category_id
                # Priority: Tenant-specific weight > Global weight
                if cat_id not in weights_by_cat or w.tenant_id is not None:
                    weights_by_cat[cat_id] = w

        final_weights = list(weights_by_cat.values())

        if not final_weights:
            return suggestions

        # Fetch all active sessions for this tenant once to avoid N+1 queries
        active_sessions = (
            self.db.query(inv_models.MaterialSession)
            .join(inv_models.MaterialSession.stock_item)
            .filter(
                inv_models.StockItem.tenant_id == tenant_id,
                inv_models.MaterialSession.status == "ACTIVE"
            )
            .options(
                joinedload(inv_models.MaterialSession.stock_item)
                .joinedload(inv_models.StockItem.batch)
            )
            .all()
        )
        # Map material_id -> active_session
        session_map = {s.stock_item.batch.material_id: s for s in active_sessions}

        # 3. For each category weight, resolve actual materials
        for weight_record in final_weights:
            category = weight_record.category
            if not category:
                continue

            # Get clinic materials in this category
            clinic_materials = (
                self.db.query(inv_models.Material)
                .filter(
                    inv_models.Material.category_id == category.id,
                    inv_models.Material.tenant_id == tenant_id,
                )
                .all()
            )

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
                "confidence": confidence,
                "reason": reason,
            }
            suggestions.append(suggestion)

        return suggestions

    def get_doctor_preferred_material(
        self,
        doctor_id: int,
        category_id: int,
        tenant_id: int,
    ) -> Optional[inv_models.Material]:
        """
        Get the material this doctor used most frequently in this category.
        """

        # Query TreatmentMaterialUsage joined to Material to find most used
        result = (
            self.db.query(
                inv_models.TreatmentMaterialUsage.material_id,
                func.count(inv_models.TreatmentMaterialUsage.id).label("usage_count"),
            )
            .join(inv_models.Material)
            .filter(
                inv_models.Material.category_id == category_id,
                inv_models.Material.tenant_id == tenant_id,
                inv_models.TreatmentMaterialUsage.tenant_id == tenant_id,
            )
            .group_by(inv_models.TreatmentMaterialUsage.material_id)
            .order_by(func.count(inv_models.TreatmentMaterialUsage.id).desc())
            .first()
        )

        if result:
            material_id = result[0]
            return (
                self.db.query(inv_models.Material)
                .filter(inv_models.Material.id == material_id)
                .first()
            )
        return None
