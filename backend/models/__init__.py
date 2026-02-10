from .base import Base

from .ai_audit import AILog  # Phase 0: Unified AI Logs

# from .audit_log import AuditLog <-- REMOVED
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
)
from .financial import Payment, Expense, SalaryPayment
from .price_list import PriceList, PriceListItem, InsuranceProvider, PriceListType
from .system import (
    AuditLog,  # <-- ADDED
    AIUsageLog,
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
    Material,
    Batch,
    StockItem,
    MaterialSession,
    StockMovement,
    ProcedureMaterialWeight,
)
