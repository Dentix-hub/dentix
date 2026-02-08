
import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(os.getcwd())

from backend.ai.agent.core import AIAgent

TEST_CASES = [
    # Schema: (Expected Tool, Query, Optional[List[str]] Allowed Alternatives)
    ("get_patient_file", "هاتي ملف المريض أحمد محمد", []),
    ("get_financial_record", "ايه الوضع المالي لمحمد علي؟", []),
    ("get_patients_with_balance", "مين المرضى اللي عليهم فلوس؟", ["search_patients"]),
    ("get_patients_with_balance", "هاتي قائمة المديونيات الحالية", []),
    ("create_patient", "سجلي مريض جديد اسمه محمود حسن سنه 30 سنة وتليفه 0100000000", ["response"]),
    ("get_appointments", "ايه مواعيد النهاردة؟", []),
    ("find_available_slots", "ايه المواعيد الفاضية بكرة؟", []),
    ("smart_book_appointment", "احجزي ميعاد لمنى زكي الثلاثاء الجاي الساعة 5", ["create_appointment"]),
    ("create_appointment", "حجز لمريض اسمه علي محمود يوم 2025-10-01 الساعة 10 صباحا", []),
    ("record_medical_note", "اكتبي ملاحظة لاحمد محمد: تشخيص تسوس في الضرس رقم 6", []),
    ("add_treatment_voice", "عملنا حشو عصب لابراهيم عادل بـ 1500 ودفع 500", []),
    ("parse_medical_dictation", "المريض بيشتكي من ألم في الجهة اليمنى، تم عمل أشعة وتبين وجود خراج", []),
    ("get_procedure_price", "سعر حشو العصب كام؟", []),
    ("create_payment", "المريض أحمد دفع 200 جنيه تحت الحساب", []),
    ("get_dashboard_stats", "ايه ملخص شغل النهاردة؟", []),
    ("get_today_payments", "جمعنا كام النهاردة؟", []),
    ("get_clinic_info", "ايه مواعيد العمل في العيادة؟", []),
    ("learn_clinic_info", "احفظي المعلومة دي: سعر الكشف بقى 300 جنيه", []),
    ("list_my_knowledge", "ايه المعلومات اللي انتي عارفاها عن العيادة؟", []),
    ("forget_info", "انسي معلومة سعر الكشف", []),
    ("get_doctor_ranking", "مين اكتر دكتور اشتغل الشهر ده؟", []),
    ("compare_periods", "قارني دخل الشهر ده بالشهر اللي فات", []),
    ("get_top_procedures", "ايه اكتر شغل بنعمله الفترة دي؟", []),
    ("get_revenue_trend", "ايه أخبار الدخل في آخر 3 شهور؟", []),
    ("send_appointment_reminders", "ابعتي رسايل تذكير لمواعيد بكرة", []),
    ("send_whatsapp_message", "ابعتي رسالة لمحمد قولي له التحاليل طلعت", []),
    ("get_users_list", "مين المستخدمين اللي عندهم حسابات على السيستم؟", []),
    ("get_expenses", "صرفنا كام الشهر ده؟", []),
    ("get_lab_orders", "ايه اخبار طلبات المعمل؟", []),
    ("get_recent_treatments", "ايه اخر حالات اشتغلناها؟", []),
    ("get_ai_stats", "انت جاوبت على كام سؤال النهاردة؟", []),
    ("summarize_patient", "لخصي لي حالة المريض كريم عبد العزيز", [])
]

async def run_tests():
    print(f"🚀 Starting AI Tools Verification (Total: {len(TEST_CASES)} tests)...\n")
    
    agent = AIAgent()
    passed = 0
    failed = 0
    
    for expected_tool, query, allowed_alternatives in TEST_CASES:
        print(f"🔹 Testing: [{expected_tool}] -> '{query}'")
        try:
            # We assume tenant_id=1 for testing
            result = await agent.process(user_input=query, tenant_id=1, user_id=1)
            actual_tool = result.get("tool")
            
            # Special handling for create_patient which might return "response" if intent detector asks for confirmation
            # But in this specific test query, I provided all info (Name, Age, Phone), so it should ideally trigger create_patient
            # OR return response with _intent="patient_registration_confirm"
            
            is_success = (actual_tool == expected_tool) or (actual_tool in allowed_alternatives)
            
            # Allow 'response' if it's asking for confirmation but correctly identified parameters
            if not is_success and expected_tool == "create_patient" and actual_tool == "response":
                 if result.get("_intent") in ["patient_registration", "patient_registration_confirm"]:
                     is_success = True
                     actual_tool = f"response ({result.get('_intent')})"

            if is_success:
                print(f"   ✅ PASS")
                passed += 1
            else:
                print(f"   ❌ FAIL (Got: {actual_tool})")
                print(f"      Response: {result.get('message')}")
                failed += 1
                
        except Exception as e:
            print(f"   ⚠️ ERROR: {e}")
            failed += 1
        
        print("-" * 50)

    print(f"\n🏁 Finished.\n✅ Passed: {passed}\n❌ Failed: {failed}")

if __name__ == "__main__":
    asyncio.run(run_tests())
