"""Tenant-scoped read-only consistency audit for clinic backup and restore data.

Produces a safe, structured diagnostics report without mutating any business data
and without disclosing PII, raw IDs, credentials, or clinical payload contents.
"""
from typing import Any, Dict, List, Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models
from backend.services.tenant_archive_embedded_refs import (
    EVENT_IDS, NON_DATABASE_IDS, REFERENCE_PREFIXES,
)
from backend.services.tenant_archive_export import export_clinic_archive_data
from backend.services.tenant_archive_registry import (
    ARCHIVE_COLUMNS, STAFF_REFERENCE_COLUMNS, STAFF_REFERENCE_SECTION,
)
from backend.services.tenant_restore_coordinator import known_global_references


async def audit_tenant_consistency(db: AsyncSession, tenant_id: int) -> Dict[str, Any]:
    """Execute a read-only consistency audit for tenant business relationships.

    Classifies every relation issue into:
    - missing_targets: Target entity does not exist anywhere in database.
    - archive_omission: Target entity exists for this tenant in DB, but was omitted from archive.
    - sql_type_mismatch: Foreign reference has an invalid non-integer data type.
    - legitimate_global_reference: Target exists in recognized global catalog.
    - deleted_historical_entity: Target entity is soft-deleted or marked deleted.
    - forbidden_cross_tenant_reference: Target entity belongs to a different clinic.
    """
    tenant_exists = (
        await db.execute(select(models.Tenant.id).where(models.Tenant.id == tenant_id))
    ).scalar_one_or_none()
    if tenant_exists is None:
        raise ValueError(f"Tenant {tenant_id} does not exist")

    # 1. Export current clinic business data without preflight validation
    payload = await export_clinic_archive_data(db, tenant_id, validate_restore=False)
    data = payload.get("data", {})
    external_ids = await known_global_references(db)

    # Build local archive ID sets
    archive_ids = {name: {row["id"] for row in rows} for name, rows in data.items()}
    archive_ids["users"] = archive_ids.get(STAFF_REFERENCE_SECTION, set())
    archive_ids["tenants"] = {tenant_id}

    discrepancies: List[Dict[str, Any]] = []

    classes = {mapper.local_table.name: mapper.class_ for mapper in models.Base.registry.mappers}

    # Helper to inspect an ID against the database
    async def _inspect_db_id(table_name: str, target_id: int) -> str:
        model_cls = classes.get(table_name)
        if model_cls is None:
            return "missing_targets"

        # Check if row exists in DB
        target_row = (
            await db.execute(select(model_cls).where(model_cls.id == target_id))
        ).scalars().first()

        if target_row is None:
            return "missing_targets"

        # Check soft deletion
        if getattr(target_row, "is_deleted", False):
            return "deleted_historical_entity"

        # Check tenant scoping
        if hasattr(target_row, "tenant_id"):
            row_tenant = getattr(target_row, "tenant_id")
            if row_tenant is None:
                return "legitimate_global_reference"
            if row_tenant != tenant_id:
                return "forbidden_cross_tenant_reference"
            # It belongs to the same tenant, so why was it missing from the archive?
            return "archive_omission"

        # Global table without tenant_id (e.g. material_categories)
        return "legitimate_global_reference"

    # 2. Inspect declared SQL foreign keys
    for section_name, rows in data.items():
        if section_name == STAFF_REFERENCE_SECTION:
            continue
        table = models.Base.metadata.tables.get(section_name)
        if table is None:
            continue

        for column in table.columns:
            if column.name not in ARCHIVE_COLUMNS.get(section_name, set()):
                continue
            for foreign in column.foreign_keys:
                referenced = foreign.column.table.name
                allowed = archive_ids.get(referenced, set()) | set(external_ids.get(referenced, ()))

                for row in rows:
                    val = row.get(column.name)
                    if val is None:
                        continue

                    if not isinstance(val, int) or isinstance(val, bool):
                        discrepancies.append({
                            "section": section_name,
                            "field": column.name,
                            "referenced_section": referenced,
                            "category": "sql_type_mismatch",
                        })
                    elif val not in allowed:
                        category = await _inspect_db_id(referenced, val)
                        discrepancies.append({
                            "section": section_name,
                            "field": column.name,
                            "referenced_section": referenced,
                            "category": category,
                        })

    # 3. Inspect embedded references
    # a. Stock movements
    for row in data.get("stock_movements", []):
        ref_id = row.get("reference_id")
        if ref_id is None:
            continue
        if not isinstance(ref_id, str):
            discrepancies.append({
                "section": "stock_movements",
                "field": "reference_id",
                "referenced_section": None,
                "category": "sql_type_mismatch",
            })
            continue

        import re
        match = re.fullmatch(r'(REVERSE:)?(TREATMENT|TREATMENT_MATERIALS|CARE_SESSION):(\d+)', ref_id)
        if not match:
            discrepancies.append({
                "section": "stock_movements",
                "field": "reference_id",
                "referenced_section": None,
                "category": "missing_targets",
            })
            continue

        prefix, kind, old_id_str = match.groups()
        target_table = REFERENCE_PREFIXES[kind]
        old_id = int(old_id_str)
        if old_id not in archive_ids.get(target_table, set()):
            category = await _inspect_db_id(target_table, old_id)
            discrepancies.append({
                "section": "stock_movements",
                "field": "reference_id",
                "referenced_section": target_table,
                "category": category,
            })

    # b. Clinical events payload
    def _inspect_payload(value, prefix="payload"):
        if isinstance(value, list):
            for item in value:
                yield from _inspect_payload(item, prefix)
        elif isinstance(value, dict):
            for k, v in value.items():
                cur_field = f"{prefix}.{k}"
                if k in EVENT_IDS and v is not None:
                    target_table = EVENT_IDS[k]
                    if not isinstance(v, int) or isinstance(v, bool):
                        yield (cur_field, target_table, "sql_type_mismatch", v)
                    else:
                        yield (cur_field, target_table, None, v)
                elif k == "bulk_work_item_ids" and isinstance(v, list):
                    for item in v:
                        if not isinstance(item, int) or isinstance(item, bool):
                            yield (cur_field, "clinical_work_items", "sql_type_mismatch", item)
                        else:
                            yield (cur_field, "clinical_work_items", None, item)
                else:
                    yield from _inspect_payload(v, cur_field)

    for row in data.get("clinical_events", []):
        payload_obj = row.get("payload")
        if not isinstance(payload_obj, dict):
            continue
        for field_path, target_table, direct_cat, id_val in _inspect_payload(payload_obj):
            if direct_cat == "sql_type_mismatch":
                discrepancies.append({
                    "section": "clinical_events",
                    "field": field_path,
                    "referenced_section": target_table,
                    "category": "sql_type_mismatch",
                })
            elif id_val not in archive_ids.get(target_table, set()):
                category = await _inspect_db_id(target_table, id_val)
                discrepancies.append({
                    "section": "clinical_events",
                    "field": field_path,
                    "referenced_section": target_table,
                    "category": category,
                })

    # c. Treatments notes & price_snapshot
    import json
    for row in data.get("treatments", []):
        notes = row.get("notes")
        if notes and isinstance(notes, str):
            import re
            m = re.fullmatch(r"Link:LabOrder:(\d+)", notes)
            if m:
                order_id = int(m.group(1))
                if order_id not in archive_ids.get("lab_orders", set()):
                    category = await _inspect_db_id("lab_orders", order_id)
                    discrepancies.append({
                        "section": "treatments",
                        "field": "notes",
                        "referenced_section": "lab_orders",
                        "category": category,
                    })
        price_snap = row.get("price_snapshot")
        if price_snap and isinstance(price_snap, str):
            try:
                snap_dict = json.loads(price_snap)
                if isinstance(snap_dict, dict) and snap_dict.get("list_id") is not None:
                    lid = snap_dict["list_id"]
                    if not isinstance(lid, int) or isinstance(lid, bool):
                        discrepancies.append({
                            "section": "treatments",
                            "field": "price_snapshot.list_id",
                            "referenced_section": "price_lists",
                            "category": "sql_type_mismatch",
                        })
                    elif lid not in archive_ids.get("price_lists", set()):
                        category = await _inspect_db_id("price_lists", lid)
                        discrepancies.append({
                            "section": "treatments",
                            "field": "price_snapshot.list_id",
                            "referenced_section": "price_lists",
                            "category": category,
                        })
            except (ValueError, TypeError):
                discrepancies.append({
                    "section": "treatments",
                    "field": "price_snapshot",
                    "referenced_section": "price_lists",
                    "category": "sql_type_mismatch",
                })

    # Group discrepancies by category and canonical relation
    categories = {
        "missing_targets": [],
        "archive_omission": [],
        "sql_type_mismatch": [],
        "legitimate_global_reference": [],
        "deleted_historical_entity": [],
        "forbidden_cross_tenant_reference": [],
    }

    aggregated: Dict[str, Dict[str, int]] = {cat: {} for cat in categories}
    for item in discrepancies:
        cat = item["category"]
        if cat not in categories:
            cat = "missing_targets"
        rel_key = f"{item['section']}.{item['field']} -> {item.get('referenced_section') or 'unknown'}"
        aggregated[cat][rel_key] = aggregated[cat].get(rel_key, 0) + 1

    for cat, rel_dict in aggregated.items():
        for rel_key, count in sorted(rel_dict.items()):
            categories[cat].append({
                "relation": rel_key,
                "count": count,
            })

    summary = {f"{cat}_count": sum(aggregated[cat].values()) for cat in categories}

    return {
        "tenant_id": tenant_id,
        "total_sections_checked": len(ARCHIVE_COLUMNS) + 1,
        "consistent": len(discrepancies) == 0,
        "categories": categories,
        "summary": summary,
    }


def format_consistency_report(audit_result: Dict[str, Any]) -> str:
    """Format audit result into a clean, safe, human-readable report."""
    tenant_id = audit_result["tenant_id"]
    is_consistent = audit_result["consistent"]
    lines = [
        f"=== DENTIX Clinic Archive Consistency Report (Tenant {tenant_id}) ===",
        f"Overall Status: {'CONSISTENT (Ready for export & restore)' if is_consistent else 'INCONSISTENT (Action required)'}",
        f"Total Sections Checked: {audit_result['total_sections_checked']}",
        "",
        "Summary by Category:",
    ]
    for key, count in audit_result["summary"].items():
        label = key.replace("_count", "").replace("_", " ").title()
        lines.append(f"  - {label}: {count}")

    lines.append("")
    lines.append("Category Breakdown:")
    for cat_name, items in audit_result["categories"].items():
        label = cat_name.replace("_", " ").upper()
        if not items:
            lines.append(f"  [{label}]: None")
        else:
            lines.append(f"  [{label}]:")
            for entry in items:
                lines.append(f"    * {entry['relation']} (count={entry['count']})")

    return "\n".join(lines)
