"""
Default AI Tool Definitions
Contains the built-in clinical tools.
"""

from typing import TYPE_CHECKING
from .base import Tool

if TYPE_CHECKING:
    from .registry import ToolRegistry


def register_default_tools(registry: "ToolRegistry"):
    """Register all default clinic tools."""

    # ============================================================
    # 1. PATIENT MANAGEMENT
    # ============================================================
    registry.register(
        Tool(
            name="get_patient_file",
            description="استرجاع الملف الطبي للمريض (التفاصيل، آخر العلاجات، التاريخ الطبي).",
            parameters={"patient_name": "اسم المريض الثلاثي أو الثنائي"},
            allowed_roles=["doctor", "receptionist", "admin", "super_admin"],
        )
    )

    registry.register(
        Tool(
            name="get_financial_record",
            description="⚠️ حسابات مريض محدد فقط (ليس العيادة). يعرض الديون والمدفوعات لمريض معين.",
            parameters={"patient_name": "اسم المريض"},
            allowed_roles=["doctor", "accountant", "admin", "super_admin"],
        )
    )

    registry.register(
        Tool(
            name="search_patients",
            description="البحث عن مرضى معينين بمواصفات محددة.",
            parameters={"query": "مثل: المرضى اللي عليهم فلوس، مرضى العصب، جدد اليوم"},
            allowed_roles=["doctor", "receptionist", "admin", "super_admin"],
        )
    )

    registry.register(
        Tool(
            name="get_patients_with_balance",
            description="قائمة المرضى الذين عليهم مبالغ مستحقة.",
            parameters={},
            allowed_roles=["doctor", "accountant", "admin", "super_admin"],
        )
    )

    registry.register(
        Tool(
            name="create_patient",
            description="""⭐ تسجيل مريض جديد / فتح ملف جديد.
        استخدم هذه الأداة عندما يقول المستخدم: "سجل مريض"، "ضيف مريض"، "مريض جديد"، "افتح ملف"، "أضف مريض".
        ⚠️ لا تستدعي الأداة إذا كانت البيانات ناقصة (الاسم، السن، التليفون) - اسأل المستخدم أولاً باستخدام response.""",
            parameters={
                "patient_name": "اسم المريض الكامل (مطلوب)",
                "phone": "رقم التليفون (مطلوب)",
                "age": "السن بالسنوات (مطلوب)",
                "gender": "الجنس (اختياري - male/female)",
                "chief_complaint": "الشكوى الرئيسية (اختياري)",
                "medical_history": "التاريخ المرضي (اختياري)",
                "notes": "ملاحظات إضافية (اختياري)",
            },
            complexity="complex",
            allowed_roles=["doctor", "receptionist", "admin", "super_admin"],
        )
    )

    # ============================================================
    # 2. APPOINTMENTS & SCHEDULING
    # ============================================================
    registry.register(
        Tool(
            name="get_appointments",
            description="عرض قائمة المواعيد والحجوزات المسجلة ليوم محدد. استخدم للإجابة على: مين حاجز، مين جاي، جدول اليوم، المواعيد النهاردة.",
            parameters={"date": "التاريخ (today, tomorrow, YYYY-MM-DD)"},
            allowed_roles=[
                "doctor",
                "receptionist",
                "assistant",
                "admin",
                "super_admin",
            ],
        )
    )

    registry.register(
        Tool(
            name="find_available_slots",
            description="البحث عن مواعيد فارغة فقط (بدون حجز).",
            parameters={"date": "التاريخ المطلوب"},
            allowed_roles=[
                "doctor",
                "receptionist",
                "assistant",
                "admin",
                "super_admin",
            ],
        )
    )

    registry.register(
        Tool(
            name="smart_book_appointment",
            description="تسجيل حجز جديد لمريض. لا تستخدم هذه الأداة للاستعلام عن المواعيد.",
            parameters={
                "patient_name": "اسم المريض",
                "date": "التاريخ المفضل",
                "time": "الوقت المفضل (صباح/مساء أو ساعة محددة)",
                "reason": "سبب الزيارة (اختياري)",
                "duration": "المدة بالدقائق (افتراضي 30)",
            },
            complexity="complex",
            allowed_roles=[
                "doctor",
                "receptionist",
                "assistant",
                "admin",
                "super_admin",
            ],
        )
    )

    registry.register(
        Tool(
            name="create_appointment",
            description="حجز موعد جديد مباشرة (يتطلب تاريخ ووقت دقيق).",
            parameters={
                "patient_name": "اسم المريض",
                "date": "YYYY-MM-DD",
                "time": "HH:MM",
                "duration": "المدة بالدقائق",
                "notes": "ملاحظات",
            },
            allowed_roles=[
                "doctor",
                "receptionist",
                "assistant",
                "admin",
                "super_admin",
            ],
        )
    )

    # ============================================================
    # 3. MEDICAL SCRIBE & VOICE NOTES (Advanced)
    # ============================================================
    registry.register(
        Tool(
            name="record_medical_note",
            description="تسجيل ملاحظة طبية نصية أو صوتية في ملف المريض.",
            parameters={
                "patient_name": "اسم المريض",
                "note_type": "نوع الملاحظة (diagnosis/procedure/prescription/general)",
                "content": "نص الملاحظة",
            },
            complexity="complex",
            allowed_roles=["doctor"],
        )
    )

    registry.register(
        Tool(
            name="add_treatment_voice",
            description="""إضافة علاج للمريض بالصوت. استخدم عندما يذكر الدكتور إجراء محدد مع تفاصيل.
        أمثلة: "عملنا حشو كومبوزيت للضرس 6"، "خلعنا ضرس العقل"، "عملنا تنظيف جير"
        """,
            parameters={
                "patient_name": "اسم المريض",
                "procedure": "اسم الإجراء",
                "tooth_number": "رقم السن (اختياري)",
                "diagnosis": "التشخيص (اختياري)",
                "notes": "ملاحظات إضافية (اختياري)",
                "cost": "التكلفة (رقم فقط)",
                "paid_amount": "المبلغ المدفوع (رقم فقط)",
            },
            complexity="complex",
            allowed_roles=["doctor"],
        )
    )

    registry.register(
        Tool(
            name="parse_medical_dictation",
            description="""تحليل إملاء طبي كامل واستخراج المعلومات. استخدم للجمل الطويلة التي تحتوي على تفاصيل متعددة.
        مثال: "المريض أحمد عنده تسوس Class 2 في الضرس 6 Upper Right، عملنا تنظيف وحشو Composite A2، المطلوب متابعة بعد أسبوع"
        """,
            parameters={
                "patient_name": "اسم المريض (إذا ذُكر)",
                "dictation": "النص الكامل للإملاء الطبي",
            },
            complexity="complex",
            allowed_roles=["doctor"],
        )
    )

    # ============================================================
    # 4. CLINIC MANAGEMENT & STATS
    # ============================================================
    registry.register(
        Tool(
            name="get_procedure_price",
            description="الاستعلام عن سعر إجراء طبي معين (حشو، خلع، زراعة...).",
            parameters={
                "procedure_name": "اسم الإجراء (مثل: حشو عصب، خلع ضرس)",
                "patient_name": "اسم المريض (اختياري - لتحديد السعر الدقيق)",
            },
            allowed_roles=["admin", "super_admin", "doctor", "receptionist"],
        )
    )

    registry.register(
        Tool(
            name="get_dashboard_stats",
            description="عرض إحصائيات عامة للعيادة (الإيرادات، المواعيد، المرضى الجدد). استخدم للأسئلة: حسابات الشهر، إيرادات الأسبوع، تقرير اليوم.",
            parameters={"period": "الفترة: today/week/month/year (افتراضي: today)"},
            allowed_roles=["admin", "super_admin", "doctor"],
        )
    )

    registry.register(
        Tool(
            name="get_today_payments",
            description="عرض مدفوعات اليوم.",
            parameters={},
            allowed_roles=["admin", "super_admin", "doctor", "accountant"],
        )
    )

    registry.register(
        Tool(
            name="get_clinic_info",
            description="عرض معلومات العيادة الأساسية.",
            parameters={},
            allowed_roles=["admin", "super_admin", "doctor", "receptionist"],
        )
    )

    registry.register(
        Tool(
            name="create_payment",
            description="تسجيل دفعة مالية جديدة للمريض.",
            parameters={"patient_name": "اسم المريض", "amount": "المبلغ المدفوع"},
            allowed_roles=[
                "doctor",
                "receptionist",
                "accountant",
                "admin",
                "super_admin",
            ],
        )
    )

    # ============================================================
    # 5. RAG KNOWLEDGE BASE
    # ============================================================
    registry.register(
        Tool(
            name="learn_clinic_info",
            description="حفظ معلومة جديدة عن العيادة في الذاكرة. استخدم للأسئلة: احفظ المواعيد، سجل سعر الكشف، خد بالك من كذا",
            parameters={
                "info_text": "المعلومة المراد حفظها",
                "category": "تصنيف (pricing/hours/policy/general) - اختياري",
            },
            allowed_roles=["doctor", "admin", "super_admin"],
        )
    )

    registry.register(
        Tool(
            name="list_my_knowledge",
            description="عرض كل المعلومات التي حفظتها.",
            parameters={},
            allowed_roles=["doctor", "admin", "super_admin"],
        )
    )

    registry.register(
        Tool(
            name="forget_info",
            description="حذف معلومة من الذاكرة.",
            parameters={"item_id": "رقم المعلومة (ID)"},
            allowed_roles=["doctor", "admin", "super_admin"],
        )
    )

    # ============================================================
    # 6. ANALYTICS (New)
    # ============================================================
    registry.register(
        Tool(
            name="get_doctor_ranking",
            description="ترتيب الأطباء حسب الدخل.",
            parameters={"period": "الفترة (month/year)"},
            allowed_roles=["admin", "super_admin"],
        )
    )

    registry.register(
        Tool(
            name="compare_periods",
            description="مقارنة فترتين من حيث الإيرادات أو المرضى أو المواعيد. استخدم للأسئلة: قارن الشهر ده بالشهر اللي فات، مقارنة",
            parameters={
                "metric": "المعيار (revenue/patients/appointments)",
                "period1": "الفترة الأولى (this_week/this_month/this_year)",
                "period2": "الفترة الثانية (last_week/last_month/last_year)",
            },
            complexity="complex",
            allowed_roles=["doctor", "admin", "super_admin"],
        )
    )

    registry.register(
        Tool(
            name="get_top_procedures",
            description="أكثر الإجراءات طلباً وإيراداً. استخدم للأسئلة: أكتر إجراء، أكتر علاج، أكثر الخدمات",
            parameters={
                "period": "الفترة (week/month/year)",
                "limit": "العدد (5/10/20)",
            },
            complexity="complex",
            allowed_roles=["doctor", "admin", "super_admin"],
        )
    )

    registry.register(
        Tool(
            name="get_revenue_trend",
            description="اتجاه الإيرادات على مدار فترة. استخدم للأسئلة: منحنى الإيرادات، تطور الدخل، الإيرادات شهر بشهر",
            parameters={"period": "الفترة (week/month/quarter/year)"},
            complexity="complex",
            allowed_roles=["doctor", "admin", "super_admin"],
        )
    )

    # ============================================================
    # 7. NOTIFICATIONS & COMMUNICATION (WhatsApp)
    # ============================================================
    registry.register(
        Tool(
            name="send_appointment_reminders",
            description="إرسال تذكيرات المواعيد عبر واتساب. استخدم للأسئلة: ابعت تذكير، رسائل التذكير، فكر المرضى",
            parameters={"date": "تاريخ المواعيد (today/tomorrow/YYYY-MM-DD)"},
            allowed_roles=["doctor", "admin", "super_admin", "receptionist"],
        )
    )

    registry.register(
        Tool(
            name="send_whatsapp_message",
            description="إرسال رسالة واتساب لمريض معين. استخدم للأسئلة: ابعت رسالة، كلم المريض",
            parameters={"patient_name": "اسم المريض", "message": "نص الرسالة"},
            allowed_roles=["doctor", "admin", "super_admin", "receptionist"],
        )
    )

    # ============================================================
    # 8. ADDITIONAL TOOLS
    # ============================================================
    registry.register(
        Tool(
            name="get_users_list",
            description="قائمة المستخدمين والدكاترة والموظفين",
            parameters={},
            allowed_roles=["admin", "super_admin"],
        )
    )

    registry.register(
        Tool(
            name="get_expenses",
            description="المصروفات، صرفنا كام",
            parameters={"period": "الفترة: today/week/month (اختياري)"},
            allowed_roles=["doctor", "admin", "super_admin"],
        )
    )

    registry.register(
        Tool(
            name="get_lab_orders",
            description="طلبات المعمل، شغل المعمل",
            parameters={"status": "الحالة: pending/completed/all (اختياري)"},
            allowed_roles=["doctor", "admin", "super_admin"],
        )
    )

    registry.register(
        Tool(
            name="get_recent_treatments",
            description="آخر العلاجات، علاجات اليوم",
            parameters={},
            allowed_roles=["doctor", "admin", "super_admin"],
        )
    )

    registry.register(
        Tool(
            name="get_ai_stats",
            description="إحصائيات استخدام المساعد الذكي",
            parameters={"period": "الفترة (today/week/month)"},
            allowed_roles=["super_admin"],
        )
    )

    registry.register(
        Tool(
            name="summarize_patient",
            description="تلخيص حالة المريض وتاريخه الطبي. استخدم للأسئلة: لخص حالة، ملخص المريض",
            parameters={"patient_name": "اسم المريض"},
            complexity="complex",
        )
    )
