"""
Schemas package for Smart Clinic Management System.

This module re-exports all schemas for backward compatibility.
Import from here: `from backend import schemas` or `from backend.schemas import User`
"""

# Patient
# Patient
from .patient import (
    PatientBase,
    PatientCreate,
    PatientUpdate,
    Patient,
    PatientSummary,
    AttachmentBase,
    AttachmentCreate,
    Attachment,
)

# Clinical
from .clinical import (
    AppointmentBase,
    AppointmentCreate,
    Appointment,
    ToothStatusBase,
    ToothStatusCreate,
    ToothStatus,
    TreatmentBase,
    TreatmentCreate,
    Treatment,
    ProcedureBase,
    ProcedureCreate,
    Procedure,
    PrescriptionBase,
    PrescriptionCreate,
    Prescription,
    SavedMedicationBase,
    SavedMedicationCreate,
    SavedMedication,
    TreatmentSessionBase,
    TreatmentSessionCreate,
    TreatmentSession,
)

# Billing
from .billing import (
    PaymentBase,
    PaymentCreate,
    Payment,
    ExpenseBase,
    ExpenseCreate,
    Expense,
    FinancialStats,
    DashboardStats,
)

# Auth
from .auth import (
    Token,
    TokenData,
    User,
    UserUpdate,
    UserAdminView,
    LoginHistory,
    BlockedIP,
)

# Tenant
from .tenant import (
    TenantBase,
    TenantCreate,
    TenantUpdate,
    Tenant,
    TenantWithStats,
    ClinicRegistration,
    SubscriptionPlanBase,
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
    SubscriptionPlan,
    SubscriptionPaymentBase,
    SubscriptionPaymentCreate,
    SubscriptionPayment,
)

# Laboratory
from .laboratory import (
    LaboratoryBase,
    LaboratoryCreate,
    LaboratoryUpdate,
    Laboratory,
    LabOrderBase,
    LabOrderCreate,
    LabOrderUpdate,
    LabOrder,
    LabPaymentBase,
    LabPaymentCreate,
    LabPayment,
)

# System
from .system import (
    AuditLog,
    SystemSetting,
    SupportMessageBase,
    SupportMessageCreate,
    SupportMessage,
    NotificationBase,
    NotificationCreate,
    Notification,
    FeatureFlag,
    FeatureFlagCreate,
    TenantFeature,
    AdminDashboardStats,
    DailySystemStats,
    BackgroundJob,
    SystemError,
)

# Inventory
from .inventory import (
    WarehouseBase,
    WarehouseCreate,
    WarehouseRead,
    MaterialBase,
    MaterialCreate,
    MaterialRead,
    MaterialUpdate,
    BatchBase,
    BatchCreate,
    BatchRead,
    StockItemBase,
    StockItemRead,
    MaterialSessionBase,
    MaterialSessionCreate,
    MaterialSessionRead,
    MaterialStockSummary,
    StockReceiveRequest,
    ConsumptionItem,
    WarehouseType,
    MaterialType,
)


# Rebuild User model for forward references
User.model_rebuild()

__all__ = [
    # Patient
    # Patient
    "PatientBase",
    "PatientCreate",
    "PatientUpdate",
    "Patient",
    "PatientSummary",
    "AttachmentBase",
    "AttachmentCreate",
    "Attachment",
    # Clinical
    "AppointmentBase",
    "AppointmentCreate",
    "Appointment",
    "ToothStatusBase",
    "ToothStatusCreate",
    "ToothStatus",
    "TreatmentBase",
    "TreatmentCreate",
    "Treatment",
    "ProcedureBase",
    "ProcedureCreate",
    "Procedure",
    "PrescriptionBase",
    "PrescriptionCreate",
    "Prescription",
    "SavedMedicationBase",
    "SavedMedicationCreate",
    "SavedMedication",
    # Billing
    "PaymentBase",
    "PaymentCreate",
    "Payment",
    "ExpenseBase",
    "ExpenseCreate",
    "Expense",
    "FinancialStats",
    "DashboardStats",
    # Auth
    "Token",
    "TokenData",
    "User",
    "UserUpdate",
    "UserAdminView",
    "LoginHistory",
    "BlockedIP",
    # Tenant
    "TenantBase",
    "TenantCreate",
    "TenantUpdate",
    "Tenant",
    "TenantWithStats",
    "ClinicRegistration",
    "SubscriptionPlanBase",
    "SubscriptionPlanCreate",
    "SubscriptionPlanUpdate",
    "SubscriptionPlan",
    "SubscriptionPaymentBase",
    "SubscriptionPaymentCreate",
    "SubscriptionPayment",
    # Laboratory
    "LaboratoryBase",
    "LaboratoryCreate",
    "LaboratoryUpdate",
    "Laboratory",
    "LabOrderBase",
    "LabOrderCreate",
    "LabOrderUpdate",
    "LabOrder",
    "LabPaymentBase",
    "LabPaymentCreate",
    "LabPayment",
    # System
    "AuditLog",
    "SystemSetting",
    "SupportMessageBase",
    "SupportMessageCreate",
    "SupportMessage",
    "NotificationBase",
    "NotificationCreate",
    "Notification",
    "FeatureFlag",
    "FeatureFlagCreate",
    "TenantFeature",
    "AdminDashboardStats",
    "DailySystemStats",
    "BackgroundJob",
    "SystemError",
    # Inventory
    "WarehouseBase",
    "WarehouseCreate",
    "WarehouseRead",
    "MaterialBase",
    "MaterialCreate",
    "MaterialRead",
    "MaterialUpdate",
    "BatchBase",
    "BatchCreate",
    "BatchRead",
    "StockItemBase",
    "StockItemRead",
    "MaterialSessionBase",
    "MaterialSessionCreate",
    "MaterialSessionRead",
    "MaterialStockSummary",
    "StockReceiveRequest",
    "ConsumptionItem",
    "WarehouseType",
    "MaterialType",
    # Treatment Sessions
    "TreatmentSessionBase",
    "TreatmentSessionCreate",
    "TreatmentSession",
]
