from typing import Optional, Literal, Union, Annotated, Any
from pydantic import BaseModel, ConfigDict, Field, BeforeValidator
import re

def parse_float_safely(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (float, int)):
        return float(v)
    # Handle string inputs
    s = str(v).strip()
    # Remove currency symbols and Arabic text
    clean = re.sub(r'[^\d\.,-]', '', s)
    
    # Handle thousands and decimal separators
    if len(clean) > 0:
        # Check if there's a separator followed by 1-2 digits at end (likely decimal)
        decimal_sep = None
        if clean.endswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')):
            # Look for possible decimal separators
            if '.' in clean:
                parts = clean.split('.')
                if len(parts[-1]) <= 2:
                    decimal_sep = '.'
            if ',' in clean and decimal_sep is None:
                parts = clean.split(',')
                if len(parts[-1]) <= 2:
                    decimal_sep = ','
        
        if decimal_sep == '.':
            # Remove all commas (thousands separators)
            clean = clean.replace(',', '')
        elif decimal_sep == ',':
            # Remove all dots (thousands separators), replace decimal comma with point
            clean = clean.replace('.', '').replace(',', '.')
        else:
            # No decimal separator, remove all separators
            clean = clean.replace(',', '').replace('.', '')
    
    if not clean:
        return None
    try:
        return float(clean)
    except ValueError:
        return None

FlexibleFloat = Annotated[Optional[float], BeforeValidator(parse_float_safely)]

# ============================================================
# 1. PATIENT MANAGEMENT
# ============================================================
class GetPatientFileInput(BaseModel):
    patient_name: str = Field(..., description="اسم المريض الثلاثي أو الثنائي")

class GetFinancialRecordInput(BaseModel):
    patient_name: str = Field(..., description="اسم المريض")

class SearchPatientsInput(BaseModel):
    query: str = Field(..., description="مثل: المرضى اللي عليهم فلوس، مرضى العصب، جدد اليوم")

class GetPatientsWithBalanceInput(BaseModel):
    pass

class CreatePatientInput(BaseModel):
    patient_name: str = Field(..., description="اسم المريض الكامل")
    phone: str = Field(..., description="رقم التليفون")
    age: int = Field(..., description="السن بالسنوات")
    gender: Optional[Literal["male", "female"]] = Field(None, description="الجنس")
    chief_complaint: Optional[str] = Field(None, description="الشكوى الرئيسية")
    medical_history: Optional[str] = Field(None, description="التاريخ المرضي")
    notes: Optional[str] = Field(None, description="ملاحظات إضافية")

# ============================================================
# 2. APPOINTMENTS & SCHEDULING
# ============================================================
class GetAppointmentsInput(BaseModel):
    date: str = Field(..., description="التاريخ (today, tomorrow, YYYY-MM-DD)")

class FindAvailableSlotsInput(BaseModel):
    date: str = Field(..., description="التاريخ المطلوب")

class SmartBookAppointmentInput(BaseModel):
    patient_name: str = Field(..., description="اسم المريض")
    date: str = Field(..., description="التاريخ المفضل")
    time: str = Field(..., description="الوقت المفضل")
    reason: Optional[str] = Field(None, description="سبب الزيارة")
    duration: int = Field(30, description="المدة بالدقائق")

class CreateAppointmentInput(BaseModel):
    patient_name: str = Field(..., description="اسم المريض")
    date: str = Field(..., description="YYYY-MM-DD")
    time: str = Field(..., description="HH:MM")
    duration: int = Field(..., description="المدة بالدقائق")
    notes: Optional[str] = Field(None, description="ملاحظات")

# ============================================================
# 3. MEDICAL SCRIBE
# ============================================================
class RecordMedicalNoteInput(BaseModel):
    patient_name: str = Field(..., description="اسم المريض")
    note_type: str = Field(..., description="diagnosis/procedure/prescription/general")
    content: str = Field(..., description="نص الملاحظة")

class AddTreatmentVoiceInput(BaseModel):
    patient_name: str = Field(..., description="اسم المريض")
    procedure: str = Field(..., description="اسم الإجراء")
    tooth_number: Optional[str] = Field(None, description="رقم السن")
    diagnosis: Optional[str] = Field(None, description="التشخيص")
    notes: Optional[str] = Field(None, description="ملاحظات إضافية")
    cost: FlexibleFloat = Field(None, description="التكلفة")
    paid_amount: FlexibleFloat = Field(None, description="المبلغ المدفوع")

class ParseMedicalDictationInput(BaseModel):
    patient_name: Optional[str] = Field(None, description="اسم المريض")
    dictation: str = Field(..., description="النص الكامل للإملاء الطبي")

# ============================================================
# 4. CLINIC MANAGEMENT & STATS
# ============================================================
class GetProcedurePriceInput(BaseModel):
    procedure_name: str = Field(..., description="اسم الإجراء")
    patient_name: Optional[str] = Field(None, description="اسم المريض")

class GetDashboardStatsInput(BaseModel):
    period: str = Field("today", description="today/week/month/year")

class GetTodayPaymentsInput(BaseModel):
    pass

class GetClinicInfoInput(BaseModel):
    pass

class CreatePaymentInput(BaseModel):
    patient_name: str = Field(..., description="اسم المريض")
    amount: FlexibleFloat = Field(..., description="المبلغ المدفوع")

# ============================================================
# 5. RAG KNOWLEDGE BASE
# ============================================================
class LearnClinicInfoInput(BaseModel):
    info_text: str = Field(..., description="المعلومة المراد حفظها")
    category: Optional[str] = Field(None, description="Category")

class ListMyKnowledgeInput(BaseModel):
    pass

class ForgetInfoInput(BaseModel):
    item_id: str = Field(..., description="رقم المعلومة")

# ============================================================
# 6. ANALYTICS
# ============================================================
class GetDoctorRankingInput(BaseModel):
    period: str = Field(..., description="month/year")

class ComparePeriodsInput(BaseModel):
    metric: str = Field(..., description="revenue/patients/appointments")
    period1: str = Field(..., description="this_week/this_month/this_year")
    period2: str = Field(..., description="last_week/last_month/last_year")

class GetTopProceduresInput(BaseModel):
    period: str = Field(..., description="week/month/year")
    limit: int = Field(5, description="العدد")

class GetRevenueTrendInput(BaseModel):
    period: str = Field(..., description="week/month/quarter/year")

# ============================================================
# 7. NOTIFICATIONS
# ============================================================
class SendAppointmentRemindersInput(BaseModel):
    date: str = Field(..., description="today/tomorrow/YYYY-MM-DD")

class SendWhatsappMessageInput(BaseModel):
    patient_name: str = Field(..., description="اسم المريض")
    message: str = Field(..., description="نص الرسالة")

# ============================================================
# 8. ADDITIONAL TOOLS
# ============================================================
class GetUsersListInput(BaseModel):
    pass

class GetExpensesInput(BaseModel):
    period: Optional[str] = Field(None, description="today/week/month")

class GetLabOrdersInput(BaseModel):
    status: Optional[str] = Field(None, description="pending/completed/all")

class GetRecentTreatmentsInput(BaseModel):
    pass

class GetAiStatsInput(BaseModel):
    period: str = Field(..., description="today/week/month")

class SummarizePatientInput(BaseModel):
    patient_name: str = Field(..., description="اسم المريض")

# Tool Name to Schema Mapping
TOOL_SCHEMA_MAP = {
    "get_patient_file": GetPatientFileInput,
    "get_financial_record": GetFinancialRecordInput,
    "search_patients": SearchPatientsInput,
    "get_patients_with_balance": GetPatientsWithBalanceInput,
    "create_patient": CreatePatientInput,
    "get_appointments": GetAppointmentsInput,
    "find_available_slots": FindAvailableSlotsInput,
    "smart_book_appointment": SmartBookAppointmentInput,
    "create_appointment": CreateAppointmentInput,
    "record_medical_note": RecordMedicalNoteInput,
    "add_treatment_voice": AddTreatmentVoiceInput,
    "parse_medical_dictation": ParseMedicalDictationInput,
    "get_procedure_price": GetProcedurePriceInput,
    "get_dashboard_stats": GetDashboardStatsInput,
    "get_today_payments": GetTodayPaymentsInput,
    "get_clinic_info": GetClinicInfoInput,
    "create_payment": CreatePaymentInput,
    "learn_clinic_info": LearnClinicInfoInput,
    "list_my_knowledge": ListMyKnowledgeInput,
    "forget_info": ForgetInfoInput,
    "get_doctor_ranking": GetDoctorRankingInput,
    "compare_periods": ComparePeriodsInput,
    "get_top_procedures": GetTopProceduresInput,
    "get_revenue_trend": GetRevenueTrendInput,
    "send_appointment_reminders": SendAppointmentRemindersInput,
    "send_whatsapp_message": SendWhatsappMessageInput,
    "get_users_list": GetUsersListInput,
    "get_expenses": GetExpensesInput,
    "get_lab_orders": GetLabOrdersInput,
    "get_recent_treatments": GetRecentTreatmentsInput,
    "get_ai_stats": GetAiStatsInput,
    "summarize_patient": SummarizePatientInput
}
