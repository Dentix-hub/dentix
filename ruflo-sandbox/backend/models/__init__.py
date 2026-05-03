from .base import Base

# Phase 0: Unified AI Logs — AILog is the canonical model
from .ai_audit import AILog

# A2.4: AIUsageLog is now a type alias for AILog.
# All legacy code using models.AIUsageLog continues to work unchanged.
# AIAuditLog is also aliased for backward compat.
# New code should use models.AILog directly.
AIUsageLog = AILog
AIAuditLog = AILog

from .security_event import SecurityEvent  # Phase 3: Security Hardening
from .tenant import Tenant, SubscriptionPlan, SubscriptionPayment
from .user import User, PasswordResetToken, LoginHistory, UserSession
from .medication import SavedMedication
from .patient import Patient, Attachment
from .clinical import (
    Appointment,
    ToothStatus,
    Treatment,
    Prescription,
    Laboratory,
    LabOrder,
    Procedure,
    TreatmentSession,
)
from .financial import Payment, Expense, SalaryPayment, LabPayment
from .price_list import PriceList, PriceListItem, InsuranceProvider, PriceListType
from .system import (
    AuditLog,
    SystemError,
    SupportMessage,
    Notification,
    NotificationRead,
    SystemSetting,
    BlockedIP,
    FeatureFlag,
    TenantFeature,
    DailySystemStats,
    BackgroundJob,
)
from .inventory import (
    Warehouse,
    MaterialCategory,
    Material,
    Batch,
    StockItem,
    MaterialSession,
    StockMovement,
    ProcedureMaterialWeight,
    TreatmentMaterialUsage,
)
