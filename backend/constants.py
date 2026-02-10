"""
Constants module for Smart Clinic Management System.

Centralizes magic strings and values for maintainability.
"""


class ROLES:
    """User role constants."""

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    DOCTOR = "doctor"
    MANAGER = "manager"
    RECEPTIONIST = "receptionist"
    ASSISTANT = "assistant"
    NURSE = "nurse"

    # Role groups
    DOCTOR_ROLES = ["doctor", "admin", "super_admin"]
    STAFF_ROLES = ["receptionist", "assistant", "nurse"]
    ADMIN_ROLES = ["admin", "super_admin"]


class MESSAGES:
    """User-facing message constants (Arabic)."""

    # Salary
    SALARY_ALREADY_PAID = "الراتب مدفوع بالفعل لهذا الشهر"
    PAYMENT_RECORDED = "تم تسجيل الدفع بنجاح"
    PAYMENT_DELETED = "تم حذف سجل الدفع"
    HIRE_DATE_UPDATED = "تم تحديث تاريخ بداية العمل"

    # Errors
    USER_NOT_FOUND = "الموظف غير موجود"
    PAYMENT_NOT_FOUND = "لم يتم العثور على سجل الدفع"
    INVALID_DATE = "تاريخ غير صالح. استخدم الصيغة: YYYY-MM-DD"
    INVALID_MONTH = "Invalid month format. Use YYYY-MM"

    # Success
    COMPENSATION_UPDATED = "Compensation updated"
