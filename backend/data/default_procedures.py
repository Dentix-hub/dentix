"""Single source of truth for default procedure catalog and chart styles.

Standard default dental procedures seeded into every new clinic tenant at price 0.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Sequence


VALID_PROCEDURE_CATEGORIES: tuple[str, ...] = (
    "Diagnosis & Prevention",
    "Restorative",
    "Endodontic",
    "Surgical",
    "Fixed Prosthodontics",
    "Removable Prosthodontics",
    "Maintenance/Follow-up",
)


@dataclass(frozen=True)
class DefaultProcedure:
    code: str
    category: str
    name: str  # Exact stored literal for legacy mapping allowlist compatibility
    name_ar: str
    name_en: str
    chart_template: str
    color_key: Optional[str] = None
    default_price: Decimal = Decimal("0.00")


DEFAULT_PROCEDURE_CATALOG: Sequence[DefaultProcedure] = (
    # --- Diagnosis & Prevention (2) ---
    DefaultProcedure(
        code="DIAG_EXAM",
        category="Diagnosis & Prevention",
        name="كشف – Examination",
        name_ar="كشف",
        name_en="Examination",
        chart_template="NONE",
        color_key=None,
    ),
    DefaultProcedure(
        code="PREV_SCALING",
        category="Diagnosis & Prevention",
        name="تنظيف جير – Scaling",
        name_ar="تنظيف جير",
        name_en="Scaling",
        chart_template="NONE",
        color_key=None,
    ),

    # --- Restorative (11) ---
    DefaultProcedure(
        code="REST_COMPOSITE_CLASS_1",
        category="Restorative",
        name="حشو كومبوزيت -- Composite Filling Class I",
        name_ar="حشو كومبوزيت صنف 1",
        name_en="Composite Filling Class I",
        chart_template="REST_COMPOSITE",
        color_key="blue",
    ),
    DefaultProcedure(
        code="REST_COMPOSITE_CLASS_2",
        category="Restorative",
        name="حشو كومبوزيت -- Composite Filling Class II",
        name_ar="حشو كومبوزيت صنف 2",
        name_en="Composite Filling Class II",
        chart_template="REST_COMPOSITE",
        color_key="blue",
    ),
    DefaultProcedure(
        code="REST_COMPOSITE_CLASS_3",
        category="Restorative",
        name="حشو كومبوزيت -- Composite Filling Class III",
        name_ar="حشو كومبوزيت صنف 3",
        name_en="Composite Filling Class III",
        chart_template="REST_COMPOSITE",
        color_key="blue",
    ),
    DefaultProcedure(
        code="REST_COMPOSITE_CLASS_4",
        category="Restorative",
        name="حشو كومبوزيت -- Composite Filling Class IV",
        name_ar="حشو كومبوزيت صنف 4",
        name_en="Composite Filling Class IV",
        chart_template="REST_COMPOSITE",
        color_key="blue",
    ),
    DefaultProcedure(
        code="REST_COMPOSITE_CLASS_5",
        category="Restorative",
        name="حشو كومبوزيت -- Composite Filling Class V",
        name_ar="حشو كومبوزيت صنف 5",
        name_en="Composite Filling Class V",
        chart_template="REST_COMPOSITE",
        color_key="blue",
    ),
    DefaultProcedure(
        code="REST_AMALGAM_CLASS_1",
        category="Restorative",
        name="حشو أملجم -- Amalgam Filling Class I",
        name_ar="حشو أملجم صنف 1",
        name_en="Amalgam Filling Class I",
        chart_template="NONE",
        color_key=None,
    ),
    DefaultProcedure(
        code="REST_AMALGAM_CLASS_2",
        category="Restorative",
        name="حشو أملجم -- Amalgam Filling Class II",
        name_ar="حشو أملجم صنف 2",
        name_en="Amalgam Filling Class II",
        chart_template="NONE",
        color_key=None,
    ),
    DefaultProcedure(
        code="REST_TEMP_FILLING",
        category="Restorative",
        name="حشو مؤقت – Temporary Filling",
        name_ar="حشو مؤقت",
        name_en="Temporary Filling",
        chart_template="NONE",
        color_key=None,
    ),
    DefaultProcedure(
        code="REST_REFILLING",
        category="Restorative",
        name="إعادة حشو – Re-filling",
        name_ar="إعادة حشو",
        name_en="Re-filling",
        chart_template="NONE",
        color_key=None,
    ),
    DefaultProcedure(
        code="REST_ANTERIOR_AESTHETIC",
        category="Restorative",
        name="حشو تجميلي أمامي – Anterior Aesthetic Filling",
        name_ar="حشو تجميلي أمامي",
        name_en="Anterior Aesthetic Filling",
        chart_template="NONE",
        color_key=None,
    ),
    DefaultProcedure(
        code="REST_POST_CORE",
        category="Restorative",
        name="بوست وبناء لب – Post and Core Buildup",
        name_ar="بوست وبناء لب",
        name_en="Post and Core Buildup",
        chart_template="NONE",
        color_key=None,
    ),

    # --- Endodontic (2) ---
    DefaultProcedure(
        code="ENDO_RCT",
        category="Endodontic",
        name="حشو عصب – Root Canal Treatment",
        name_ar="حشو عصب",
        name_en="Root Canal Treatment",
        chart_template="ENDO_RCT",
        color_key="purple",
    ),
    DefaultProcedure(
        code="ENDO_RETREATMENT",
        category="Endodontic",
        name="إعادة حشو عصب – Retreatment Root Canal",
        name_ar="إعادة حشو عصب",
        name_en="Retreatment Root Canal",
        chart_template="ENDO_RCT",
        color_key="purple",
    ),

    # --- Surgical (7) ---
    DefaultProcedure(
        code="SURG_SIMPLE_EXTRACTION",
        category="Surgical",
        name="خلع عادي – Simple Extraction",
        name_ar="خلع عادي",
        name_en="Simple Extraction",
        chart_template="SURG_EXTRACTION",
        color_key="amber",
    ),
    DefaultProcedure(
        code="SURG_SURGICAL_EXTRACTION",
        category="Surgical",
        name="خلع جراحي – Surgical Extraction",
        name_ar="خلع جراحي",
        name_en="Surgical Extraction",
        chart_template="SURG_EXTRACTION",
        color_key="amber",
    ),
    DefaultProcedure(
        code="SURG_WISDOM_EXTRACTION",
        category="Surgical",
        name="خلع ضرس عقل – Wisdom Tooth Extraction",
        name_ar="خلع ضرس عقل",
        name_en="Wisdom Tooth Extraction",
        chart_template="SURG_EXTRACTION",
        color_key="amber",
    ),
    DefaultProcedure(
        code="SURG_PARTIAL_IMPACTED_WISDOM",
        category="Surgical",
        name="خلع ضرس عقل مطمور جزئي – Partially Impacted Wisdom Tooth Extraction",
        name_ar="خلع ضرس عقل مطمور جزئي",
        name_en="Partially Impacted Wisdom Tooth Extraction",
        chart_template="SURG_EXTRACTION",
        color_key="amber",
    ),
    DefaultProcedure(
        code="SURG_FULL_IMPACTED_WISDOM",
        category="Surgical",
        name="خلع ضرس عقل مطمور كلي – Fully Impacted Wisdom Tooth Extraction",
        name_ar="خلع ضرس عقل مطمور كلي",
        name_en="Fully Impacted Wisdom Tooth Extraction",
        chart_template="SURG_EXTRACTION",
        color_key="amber",
    ),
    DefaultProcedure(
        code="SURG_PRIMARY_EXTRACTION",
        category="Surgical",
        name="خلع سن لبني – Primary Tooth Extraction",
        name_ar="خلع سن لبني",
        name_en="Primary Tooth Extraction",
        chart_template="SURG_EXTRACTION",
        color_key="amber",
    ),
    DefaultProcedure(
        code="SURG_ROOT_REMNANTS",
        category="Surgical",
        name="خلع بقايا جذور – Root Remnants Extraction",
        name_ar="خلع بقايا جذور",
        name_en="Root Remnants Extraction",
        chart_template="SURG_EXTRACTION",
        color_key="amber",
    ),

    # --- Fixed Prosthodontics (7) ---
    DefaultProcedure(
        code="PROS_CROWN_PORCELAIN",
        category="Fixed Prosthodontics",
        name="تاج بورسلين – Porcelain Crown",
        name_ar="تاج بورسلين",
        name_en="Porcelain Crown",
        chart_template="PROS_CROWN",
        color_key="teal",
    ),
    DefaultProcedure(
        code="PROS_CROWN_ZIRCONIA",
        category="Fixed Prosthodontics",
        name="تاج زيركون – Zirconia Crown",
        name_ar="تاج زيركون",
        name_en="Zirconia Crown",
        chart_template="PROS_CROWN",
        color_key="teal",
    ),
    DefaultProcedure(
        code="PROS_CROWN_EMAX",
        category="Fixed Prosthodontics",
        name="تاج -- E-max Crown",
        name_ar="تاج إيماكس",
        name_en="E-max Crown",
        chart_template="PROS_CROWN",
        color_key="teal",
    ),
    DefaultProcedure(
        code="PROS_CROWN_METAL",
        category="Fixed Prosthodontics",
        name="تاج معدن – Metal Crown",
        name_ar="تاج معدن",
        name_en="Metal Crown",
        chart_template="PROS_CROWN",
        color_key="teal",
    ),
    DefaultProcedure(
        code="PROS_CROWN_TEMP",
        category="Fixed Prosthodontics",
        name="تاج مؤقت – Temporary Crown",
        name_ar="تاج مؤقت",
        name_en="Temporary Crown",
        chart_template="PROS_CROWN",
        color_key="teal",
    ),
    DefaultProcedure(
        code="PROS_BRIDGE_FIXED",
        category="Fixed Prosthodontics",
        name="جسر ثابت – Fixed Bridge",
        name_ar="جسر ثابت",
        name_en="Fixed Bridge",
        chart_template="PROS_BRIDGE",
        color_key="teal",
    ),
    DefaultProcedure(
        code="PROS_CROWN_RECEMENT",
        category="Fixed Prosthodontics",
        name="إعادة تثبيت تاج – Crown Recementation",
        name_ar="إعادة تثبيت تاج",
        name_en="Crown Recementation",
        chart_template="NONE",
        color_key=None,
    ),

    # --- Removable Prosthodontics (4) ---
    DefaultProcedure(
        code="PROS_DENTURE_COMPLETE_ACRYLIC",
        category="Removable Prosthodontics",
        name="طقم كامل أكريليك – Complete Acrylic Denture",
        name_ar="طقم كامل أكريليك",
        name_en="Complete Acrylic Denture",
        chart_template="NONE",
        color_key=None,
    ),
    DefaultProcedure(
        code="PROS_DENTURE_PARTIAL_ACRYLIC",
        category="Removable Prosthodontics",
        name="طقم جزئي أكريليك – Partial Acrylic Denture",
        name_ar="طقم جزئي أكريليك",
        name_en="Partial Acrylic Denture",
        chart_template="NONE",
        color_key=None,
    ),
    DefaultProcedure(
        code="PROS_DENTURE_PARTIAL_METAL",
        category="Removable Prosthodontics",
        name="طقم جزئي معدني – Partial Metal Denture",
        name_ar="طقم جزئي معدني",
        name_en="Partial Metal Denture",
        chart_template="NONE",
        color_key=None,
    ),
    DefaultProcedure(
        code="PROS_DENTURE_FLEXIBLE",
        category="Removable Prosthodontics",
        name="طقم مرن – Flexible Denture",
        name_ar="طقم مرن",
        name_en="Flexible Denture",
        chart_template="NONE",
        color_key=None,
    ),

    # --- Maintenance/Follow-up (1) ---
    DefaultProcedure(
        code="MAINT_FOLLOWUP",
        category="Maintenance/Follow-up",
        name="جلسة متابعة – Follow-up Session",
        name_ar="جلسة متابعة",
        name_en="Follow-up Session",
        chart_template="NONE",
        color_key=None,
    ),
)

PROCEDURES_BY_CODE: dict[str, DefaultProcedure] = {
    p.code: p for p in DEFAULT_PROCEDURE_CATALOG
}

PROCEDURES_BY_NAME: dict[str, DefaultProcedure] = {
    p.name: p for p in DEFAULT_PROCEDURE_CATALOG
}
