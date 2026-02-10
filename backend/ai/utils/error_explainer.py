from typing import Optional


class AIErrorExplainer:
    """
    Translates technical errors into human-readable advice for the doctor.
    """

    @staticmethod
    def explain(error: str, tool_name: Optional[str] = None) -> str:
        error_str = str(error).lower()

        # 1. Quota / Limits
        if "quota" in error_str or "limit" in error_str:
            return "⚠️ استنفدت الحد اليومي المسموح به للذكاء الاصطناعي. يرجى المحاولة غداً أو ترقية الباقة."

        # 2. Database Integrity (Duplicates)
        if "integrityerror" in error_str or "unique constraint" in error_str:
            if tool_name == "create_patient":
                return "⚠️ يبدو أن هذا المريض مسجل بالفعل بنفس رقم التليفون أو الاسم."
            if tool_name == "create_appointment":
                return "⚠️ هذا الموعد محجوز بالفعل. جرب وقتاً آخر."

        # 3. Connection Errors
        if "connection" in error_str or "timeout" in error_str:
            return "⚠️ في مشكلة في الاتصال بالسيرفر. جرب تاني بعد شوية."

        # 4. Authentication / Permission
        if "401" in error_str or "403" in error_str or "permission" in error_str:
            return "⛔ ليس لديك صلاحية للقيام بهذا الإجراء. راجع مدير العيادة."

        # 5. Validation (Pydantic calls this usually)
        if "validation" in error_str:
            return f"⚠️ البيانات ناقصة أو غير صحيحة ({error_str})"

        # Default Fallback
        return f"حدث خطأ غير متوقع: {str(error)}"


# Singleton
error_explainer = AIErrorExplainer()
