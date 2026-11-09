"""
DENTIX Commercial Capability Registry & Plan Specifications.

Defines the authoritative catalog of system capabilities, operation classes,
and owner-approved commercial launch plan specifications.

Authoritative product policies:
- Essential: 200 EGP / calendar month; 2 active login seats; 2 AI requests / clinic-local day
- Professional: 400 EGP / calendar month; 5 active login seats; 10 AI requests / clinic-local day
- Business: 1000 EGP / calendar month; 15 active login seats; 30 AI requests / clinic-local day
- Initial feature division: The same verified capabilities across all three plans.
- Trial: Professional, 14 days, no card required.
- Clinical-history read invariant: Permanently permitted across all subscription states.
- Non-sellable / unproven capabilities: patient_portal, telehealth, multi_branch, custom_branding.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Set


class CapabilityKey(str, Enum):
    # Implemented / Sellable Capabilities for Launch
    CLINICAL = "clinical"
    BILLING = "billing"
    LABORATORIES = "laboratories"
    INVENTORY = "inventory"
    EXPORT_REPORTS = "export_reports"
    AI_INSIGHTS = "ai_insights"
    TENANT_BACKUPS = "tenant_backups"

    # Unproven / Non-Sellable Capabilities (Excluded from launch)
    PATIENT_PORTAL = "patient_portal"
    TELEHEALTH = "telehealth"
    MULTI_BRANCH = "multi_branch"
    CUSTOM_BRANDING = "custom_branding"


class OperationClass(str, Enum):
    """
    Operation classes govern how an action intersects with subscription state:
    - READ_HISTORY: Reading existing clinical records. Permanent invariant (never blocked by commercial state).
    - WRITE_BUSINESS: Creating or mutating patients, appointments, treatments, billing, etc.
    - EXPORT_DATA: Exporting financial, analytical, or backup reports.
    - EXECUTE_AI: Provider-backed AI interactions subject to daily capacity limits.
    - CAPACITY_ADMISSION: Consuming finite capacity (seats, AI requests).
    """
    READ_HISTORY = "read_history"
    WRITE_BUSINESS = "write_business"
    EXPORT_DATA = "export_data"
    EXECUTE_AI = "execute_ai"
    CAPACITY_ADMISSION = "capacity_admission"


@dataclass(frozen=True)
class CapabilityDefinition:
    key: str
    display_name_en: str
    display_name_ar: str
    is_sellable: bool
    default_enabled_launch: bool
    allowed_operations: List[str]
    associated_routes: List[str]
    associated_tools: List[str]
    associated_roles: List[str]
    rollout_flag_key: Optional[str] = None
    description_en: str = ""
    description_ar: str = ""


# Authoritative capability definitions
CAPABILITY_REGISTRY: Dict[str, CapabilityDefinition] = {
    CapabilityKey.CLINICAL.value: CapabilityDefinition(
        key=CapabilityKey.CLINICAL.value,
        display_name_en="Clinical Records & Appointments",
        display_name_ar="السجلات الطبية والمواعيد",
        is_sellable=True,
        default_enabled_launch=True,
        allowed_operations=[
            OperationClass.READ_HISTORY.value,
            OperationClass.WRITE_BUSINESS.value,
        ],
        associated_routes=[
            "/patients",
            "/appointments",
            "/treatments",
            "/treatment-plans",
            "/care-sessions",
            "/clinical-commands",
            "/prescriptions",
            "/medications",
            "/procedures",
            "/procedure-chart-styles",
        ],
        associated_tools=[
            "get_patient_file",
            "search_patients",
            "create_patient",
            "summarize_patient",
            "get_appointments",
            "find_available_slots",
            "smart_book_appointment",
            "create_appointment",
            "record_medical_note",
            "add_treatment_voice",
            "parse_medical_dictation",
            "get_recent_treatments",
        ],
        associated_roles=["doctor", "receptionist", "admin", "super_admin", "clinic_owner"],
        rollout_flag_key="clinical_vnext_native_writes",
        description_en="Patient files, dental chart, treatment plans, prescriptions, and appointment management.",
        description_ar="ملفات المرضى، مخطط الأسنان، خطط العلاج، الروشتات، وإدارة المواعيد.",
    ),
    CapabilityKey.BILLING.value: CapabilityDefinition(
        key=CapabilityKey.BILLING.value,
        display_name_en="Billing, Payments & Accounting",
        display_name_ar="الفواتير والمدفوعات والمحاسبة",
        is_sellable=True,
        default_enabled_launch=True,
        allowed_operations=[
            OperationClass.READ_HISTORY.value,
            OperationClass.WRITE_BUSINESS.value,
            OperationClass.EXPORT_DATA.value,
        ],
        associated_routes=[
            "/payments",
            "/expenses",
            "/accounting",
            "/financials",
            "/clinical-charges",
            "/price-lists",
            "/insurance",
        ],
        associated_tools=[
            "get_financial_record",
            "get_patients_with_balance",
            "get_procedure_price",
            "get_dashboard_stats",
            "get_today_payments",
            "create_payment",
            "get_expenses",
        ],
        associated_roles=["accountant", "clinic_owner", "admin", "super_admin"],
        description_en="Invoicing, patient balances, expense tracking, ledger entries, and price lists.",
        description_ar="الفواتير، مديونيات المرضى، تتبع المصروفات، القيود المحاسبية، وقوائم الأسعار.",
    ),
    CapabilityKey.LABORATORIES.value: CapabilityDefinition(
        key=CapabilityKey.LABORATORIES.value,
        display_name_en="Laboratory Management",
        display_name_ar="إدارة المعامل",
        is_sellable=True,
        default_enabled_launch=True,
        allowed_operations=[
            OperationClass.READ_HISTORY.value,
            OperationClass.WRITE_BUSINESS.value,
        ],
        associated_routes=["/laboratories"],
        associated_tools=["get_lab_orders"],
        associated_roles=["doctor", "admin", "clinic_owner", "receptionist", "super_admin"],
        description_en="External lab orders, prosthetic work item tracking, and lab settlements.",
        description_ar="أوامر المعامل الخارجية، تتبع التركيبات، وتسويات حسابات المعامل.",
    ),
    CapabilityKey.INVENTORY.value: CapabilityDefinition(
        key=CapabilityKey.INVENTORY.value,
        display_name_en="Inventory & Materials",
        display_name_ar="المخزون والمواد الطبية",
        is_sellable=True,
        default_enabled_launch=True,
        allowed_operations=[
            OperationClass.READ_HISTORY.value,
            OperationClass.WRITE_BUSINESS.value,
        ],
        associated_routes=["/inventory", "/inventory-smart"],
        associated_tools=[],
        associated_roles=["admin", "clinic_owner", "doctor", "super_admin"],
        description_en="Warehouses, material batches, stock tracking, and clinical consumption.",
        description_ar="المستودعات، دفعات المواد، تتبع المخزون، والاستهلاك العيادي.",
    ),
    CapabilityKey.EXPORT_REPORTS.value: CapabilityDefinition(
        key=CapabilityKey.EXPORT_REPORTS.value,
        display_name_en="Reports & Data Export",
        display_name_ar="التقارير المتقدمة وتصدير البيانات",
        is_sellable=True,
        default_enabled_launch=True,
        allowed_operations=[
            OperationClass.READ_HISTORY.value,
            OperationClass.EXPORT_DATA.value,
        ],
        associated_routes=["/dashboard", "/finance-exports", "/metrics"],
        associated_tools=[
            "get_doctor_ranking",
            "compare_periods",
            "get_top_procedures",
            "get_revenue_trend",
        ],
        associated_roles=["clinic_owner", "admin", "accountant", "super_admin"],
        description_en="Advanced analytics, KPI dashboards, and structured financial/clinical exports.",
        description_ar="التحليلات المتقدمة، لوحات مؤشرات الأداء، وتصدير التقارير المالية والطبية.",
    ),
    CapabilityKey.AI_INSIGHTS.value: CapabilityDefinition(
        key=CapabilityKey.AI_INSIGHTS.value,
        display_name_en="AI Assistant & Clinical Insights",
        display_name_ar="مساعد الذكاء الاصطناعي والتحليلات الذكية",
        is_sellable=True,
        default_enabled_launch=True,
        allowed_operations=[
            OperationClass.EXECUTE_AI.value,
            OperationClass.CAPACITY_ADMISSION.value,
        ],
        associated_routes=["/ai", "/ai-assist", "/analytics-ai-v2", "/ai-admin"],
        associated_tools=[
            "get_patient_file",
            "search_patients",
            "create_patient",
            "summarize_patient",
            "get_appointments",
            "find_available_slots",
            "smart_book_appointment",
            "create_appointment",
            "record_medical_note",
            "add_treatment_voice",
            "parse_medical_dictation",
            "get_procedure_price",
            "get_dashboard_stats",
            "get_today_payments",
            "create_payment",
            "get_expenses",
            "get_lab_orders",
            "get_recent_treatments",
        ],
        associated_roles=["doctor", "admin", "clinic_owner", "accountant", "receptionist", "super_admin"],
        description_en="Provider-backed conversational assistant, clinical dictation, and intelligent suggestions.",
        description_ar="المساعد الذكي المدعوم بمزودي الذكاء الاصطناعي، الإملاء الصوتي، والاقتراحات الذكية.",
    ),
    CapabilityKey.TENANT_BACKUPS.value: CapabilityDefinition(
        key=CapabilityKey.TENANT_BACKUPS.value,
        display_name_en="Clinic Data Backups & Archive",
        display_name_ar="النسخ الاحتياطي وأرشفة بيانات العيادة",
        is_sellable=True,
        default_enabled_launch=True,
        allowed_operations=[
            OperationClass.READ_HISTORY.value,
            OperationClass.EXPORT_DATA.value,
        ],
        associated_routes=["/tenant-backups", "/clinic-google"],
        associated_tools=[],
        associated_roles=["clinic_owner", "super_admin"],
        description_en="Automated Google Drive integration, full clinic snapshot, and archival export.",
        description_ar="الربط التلقائي مع Google Drive، لقطات النسخ الاحتياطي الكاملة، وتصدير الأرشيف.",
    ),

    # -------------------------------------------------------------
    # Unproven / Non-sellable capabilities (Explicitly excluded)
    # -------------------------------------------------------------
    CapabilityKey.PATIENT_PORTAL.value: CapabilityDefinition(
        key=CapabilityKey.PATIENT_PORTAL.value,
        display_name_en="Patient Portal",
        display_name_ar="بوابة المريض الإلكترونية",
        is_sellable=False,
        default_enabled_launch=False,
        allowed_operations=[],
        associated_routes=[],
        associated_tools=[],
        associated_roles=[],
        description_en="Deferred feature: Unauthenticated/authenticated patient self-service portal.",
        description_ar="ميزة مؤجلة: بوابة خدمة المرضى الذاتية.",
    ),
    CapabilityKey.TELEHEALTH.value: CapabilityDefinition(
        key=CapabilityKey.TELEHEALTH.value,
        display_name_en="Telehealth Consultations",
        display_name_ar="الاستشارات الطبية عن بعد",
        is_sellable=False,
        default_enabled_launch=False,
        allowed_operations=[],
        associated_routes=[],
        associated_tools=[],
        associated_roles=[],
        description_en="Deferred feature: Integrated video/audio consultations.",
        description_ar="ميزة مؤجلة: الاستشارات الطبية بالفيديو والصوت.",
    ),
    CapabilityKey.MULTI_BRANCH.value: CapabilityDefinition(
        key=CapabilityKey.MULTI_BRANCH.value,
        display_name_en="Multi-Branch Management",
        display_name_ar="إدارة الفروع المتعددة",
        is_sellable=False,
        default_enabled_launch=False,
        allowed_operations=[],
        associated_routes=[],
        associated_tools=[],
        associated_roles=[],
        description_en="Deferred feature: Multi-location tenant synchronization and aggregate reporting.",
        description_ar="ميزة مؤجلة: إدارة ومزامنة الفروع المتعددة للعيادة.",
    ),
    CapabilityKey.CUSTOM_BRANDING.value: CapabilityDefinition(
        key=CapabilityKey.CUSTOM_BRANDING.value,
        display_name_en="Custom Branding & Domain",
        display_name_ar="هوية مخصصة ودومين خاص",
        is_sellable=False,
        default_enabled_launch=False,
        allowed_operations=[],
        associated_routes=[],
        associated_tools=[],
        associated_roles=[],
        description_en="Deferred feature: White-labeling, custom DNS domains, and dedicated SSL.",
        description_ar="ميزة مؤجلة: العلامة التجارية المخصصة والدومين الخاص.",
    ),
}

# Known aliases mapping to canonical capability keys
CAPABILITY_ALIASES: Dict[str, str] = {
    # Clinical
    "clinical": CapabilityKey.CLINICAL.value,
    "core_clinical": CapabilityKey.CLINICAL.value,
    "patients": CapabilityKey.CLINICAL.value,
    "patient": CapabilityKey.CLINICAL.value,
    "appointments": CapabilityKey.CLINICAL.value,
    "appointment": CapabilityKey.CLINICAL.value,
    "treatments": CapabilityKey.CLINICAL.value,
    "treatment": CapabilityKey.CLINICAL.value,
    "prescriptions": CapabilityKey.CLINICAL.value,
    "odontogram": CapabilityKey.CLINICAL.value,
    "dashboard": CapabilityKey.CLINICAL.value,
    "multi_user": CapabilityKey.CLINICAL.value,
    "trial": CapabilityKey.CLINICAL.value,

    # Billing
    "billing": CapabilityKey.BILLING.value,
    "payments": CapabilityKey.BILLING.value,
    "payment": CapabilityKey.BILLING.value,
    "expenses": CapabilityKey.BILLING.value,
    "expense": CapabilityKey.BILLING.value,
    "accounting": CapabilityKey.BILLING.value,
    "financials": CapabilityKey.BILLING.value,
    "invoices": CapabilityKey.BILLING.value,
    "receivables": CapabilityKey.BILLING.value,

    # Laboratories
    "laboratories": CapabilityKey.LABORATORIES.value,
    "lab": CapabilityKey.LABORATORIES.value,
    "labs": CapabilityKey.LABORATORIES.value,
    "lab_orders": CapabilityKey.LABORATORIES.value,
    "lab_integration": CapabilityKey.LABORATORIES.value,

    # Inventory
    "inventory": CapabilityKey.INVENTORY.value,
    "materials": CapabilityKey.INVENTORY.value,
    "stock": CapabilityKey.INVENTORY.value,
    "stock_items": CapabilityKey.INVENTORY.value,

    # Export & Reports
    "export_reports": CapabilityKey.EXPORT_REPORTS.value,
    "reports_advanced": CapabilityKey.EXPORT_REPORTS.value,
    "advanced_reports": CapabilityKey.EXPORT_REPORTS.value,
    "reports_basic": CapabilityKey.EXPORT_REPORTS.value,
    "basic_reporting": CapabilityKey.EXPORT_REPORTS.value,
    "reporting": CapabilityKey.EXPORT_REPORTS.value,
    "analytics": CapabilityKey.EXPORT_REPORTS.value,
    "exports": CapabilityKey.EXPORT_REPORTS.value,
    "finance_exports": CapabilityKey.EXPORT_REPORTS.value,

    # AI Insights
    "ai_insights": CapabilityKey.AI_INSIGHTS.value,
    "ai_assistant": CapabilityKey.AI_INSIGHTS.value,
    "ai": CapabilityKey.AI_INSIGHTS.value,
    "ai_chat": CapabilityKey.AI_INSIGHTS.value,
    "ai_analysis": CapabilityKey.AI_INSIGHTS.value,
    "scribe": CapabilityKey.AI_INSIGHTS.value,

    # Backups
    "tenant_backups": CapabilityKey.TENANT_BACKUPS.value,
    "backups": CapabilityKey.TENANT_BACKUPS.value,
    "backup": CapabilityKey.TENANT_BACKUPS.value,
    "google_backup": CapabilityKey.TENANT_BACKUPS.value,

    # Non-sellable
    "patient_portal": CapabilityKey.PATIENT_PORTAL.value,
    "portal": CapabilityKey.PATIENT_PORTAL.value,
    "telehealth": CapabilityKey.TELEHEALTH.value,
    "multi_branch": CapabilityKey.MULTI_BRANCH.value,
    "custom_branding": CapabilityKey.CUSTOM_BRANDING.value,
    "branding": CapabilityKey.CUSTOM_BRANDING.value,
}


@dataclass(frozen=True)
class PlanSpecification:
    name: str
    display_name_en: str
    display_name_ar: str
    price_egp: Decimal
    max_active_users: int
    ai_daily_limit: int
    is_ai_enabled: bool
    is_trial_eligible: bool
    trial_duration_days: Optional[int] = None
    enabled_capabilities: Set[str] = field(default_factory=set)


# Authoritative launch plan specifications approved by owner
LAUNCH_PLAN_SPECS: Dict[str, PlanSpecification] = {
    "essential": PlanSpecification(
        name="essential",
        display_name_en="Essential",
        display_name_ar="الباقة الأساسية",
        price_egp=Decimal("200.00"),
        max_active_users=2,
        ai_daily_limit=2,
        is_ai_enabled=True,
        is_trial_eligible=False,
        enabled_capabilities={
            CapabilityKey.CLINICAL.value,
            CapabilityKey.BILLING.value,
            CapabilityKey.LABORATORIES.value,
            CapabilityKey.INVENTORY.value,
            CapabilityKey.EXPORT_REPORTS.value,
            CapabilityKey.AI_INSIGHTS.value,
            CapabilityKey.TENANT_BACKUPS.value,
        },
    ),
    "professional": PlanSpecification(
        name="professional",
        display_name_en="Professional",
        display_name_ar="الباقة الاحترافية",
        price_egp=Decimal("400.00"),
        max_active_users=5,
        ai_daily_limit=10,
        is_ai_enabled=True,
        is_trial_eligible=True,
        trial_duration_days=14,
        enabled_capabilities={
            CapabilityKey.CLINICAL.value,
            CapabilityKey.BILLING.value,
            CapabilityKey.LABORATORIES.value,
            CapabilityKey.INVENTORY.value,
            CapabilityKey.EXPORT_REPORTS.value,
            CapabilityKey.AI_INSIGHTS.value,
            CapabilityKey.TENANT_BACKUPS.value,
        },
    ),
    "business": PlanSpecification(
        name="business",
        display_name_en="Business",
        display_name_ar="باقة الأعمال",
        price_egp=Decimal("1000.00"),
        max_active_users=15,
        ai_daily_limit=30,
        is_ai_enabled=True,
        is_trial_eligible=False,
        enabled_capabilities={
            CapabilityKey.CLINICAL.value,
            CapabilityKey.BILLING.value,
            CapabilityKey.LABORATORIES.value,
            CapabilityKey.INVENTORY.value,
            CapabilityKey.EXPORT_REPORTS.value,
            CapabilityKey.AI_INSIGHTS.value,
            CapabilityKey.TENANT_BACKUPS.value,
        },
    ),
}

# Known aliases for plan names
PLAN_NAME_ALIASES: Dict[str, str] = {
    "essential": "essential",
    "basic": "essential",
    "starter": "essential",
    "الأساسية": "essential",
    "الباقة الأساسية": "essential",

    "professional": "professional",
    "pro": "professional",
    "trial": "professional",  # Trial canonical tier is Professional
    "الاحترافية": "professional",
    "الباقة الاحترافية": "professional",

    "business": "business",
    "enterprise": "business",
    "premium": "business",
    "الأعمال": "business",
    "باقة الأعمال": "business",
}


def canonicalize_capability_key(key: str) -> Optional[str]:
    """Resolve a raw or legacy capability string to its canonical key."""
    if not key or not isinstance(key, str):
        return None
    normalized = key.strip().lower()
    return CAPABILITY_ALIASES.get(normalized)


def canonicalize_plan_name(name: Optional[str]) -> Optional[str]:
    """Resolve a raw plan name or display name to canonical plan key."""
    if not name or not isinstance(name, str):
        return None
    normalized = name.strip().lower()
    return PLAN_NAME_ALIASES.get(normalized)


def resolve_plan_spec(name: Optional[str]) -> Optional[PlanSpecification]:
    """Resolve a raw plan name, alias, or display name to authoritative PlanSpecification."""
    canon = canonicalize_plan_name(name)
    if canon:
        return LAUNCH_PLAN_SPECS.get(canon)
    return None


def is_sellable_capability(key: str) -> bool:
    """Return True if capability is registered and sellable in launch plans."""
    canon = canonicalize_capability_key(key)
    if not canon or canon not in CAPABILITY_REGISTRY:
        return False
    return CAPABILITY_REGISTRY[canon].is_sellable
