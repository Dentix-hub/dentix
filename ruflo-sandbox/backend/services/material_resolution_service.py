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
        import re
        # 1. Standardize all separators (dashes, underscores, multiple spaces) to a single space
        n = re.sub(r'[\s\-_–—]+', ' ', name).lower()
        # 2. Split into individual words/parts
        parts = [p.strip() for p in n.split()]
        # 3. Sort parts to handle "Arabic - English" vs "English - Arabic" or any other order
        parts.sort()
        # 4. Join back with no spaces for a canonical comparison string
        return "".join(parts)

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
            # LOG THE FAILURE
            try:
                with open("suggestion_debug.log", "a", encoding="utf-8") as f:
                    from datetime import datetime
                    f.write(f"[{datetime.now()}] !!! PROCEDURE NOT FOUND IN DB: ID={procedure_id}\n")
            except Exception:
                pass
            return suggestions

        proc_norm = self._normalize_name(proc.name)

        # DEBUG LOGGING
        try:
            with open("suggestion_debug.log", "a", encoding="utf-8") as f:
                import datetime
                f.write(f"[{datetime.datetime.now()}] RESOLVE: id={procedure_id} name='{proc.name}'\n")
                f.write(f"  -> Normalized Request: '{proc_norm}'\n")
        except Exception:
            pass

        # 2. Get all potential weights (Global + Tenant)
        # We fetch all global weights and tenant weights once
        # and then filter by normalized name in Python for maximum robustness
        all_potential_weights = (
            self.db.query(inv_models.ProcedureMaterialWeight)
            .options(
                joinedload(inv_models.ProcedureMaterialWeight.category),
                joinedload(inv_models.ProcedureMaterialWeight.procedure)
            )
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

        matches_found = 0
        for w in all_potential_weights:
            w_proc_name = w.procedure.name if w.procedure else ""
            w_norm = self._normalize_name(w_proc_name)

            if w.procedure_id == procedure_id or w_norm == proc_norm:
                matches_found += 1
                cat_id = w.category_id
                # Priority: Tenant-specific weight > Global weight
                if cat_id not in weights_by_cat or w.tenant_id is not None:
                    weights_by_cat[cat_id] = w

        try:
            with open("suggestion_debug.log", "a", encoding="utf-8") as f:
                f.write(f"  -> Matches Found: {matches_found}, Unique Categories: {len(weights_by_cat)}\n")
                if matches_found == 0 and all_potential_weights:
                    f.write("  -> NO MATCHES. Sample weights names:\n")
                    for w in all_potential_weights[:5]:
                        name = w.procedure.name if w.procedure else "N/A"
                        f.write(f"     - '{name}' -> '{self._normalize_name(name)}'\n")
        except Exception:
            pass

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
