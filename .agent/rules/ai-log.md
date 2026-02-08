---
trigger: always_on
---

🧠 AI LOGGING RULES

(Mandatory – No Exceptions)

🟥 RULE 1: Every Request Must Have One Trace ID

لا يوجد Log بدون trace

✅ Required
trace_id = uuid_v4()

❌ ممنوع

Logs منفصلة

Events من غير ربط

أي خطوة بدون trace_id = كأنها محصلتش

🟥 RULE 2: Log the AI Decision, Not Just the Result

النتيجة لوحدها ملهاش قيمة

لازم يتسجل:
{
  "intent": "ADD_APPOINTMENT",
  "confidence": 0.64,
  "decision_path": "LLM_CONFIRMATION → TOOL",
  "confirmation_used": true
}


لو مش عارف “ليه AI عمل كده” → عمرك ما هتصلحه

🟥 RULE 3: Every Model Call Must Explain Itself

الموديل يبرر اختياره

Required
{
  "model": "llama-3.1-8b-instant",
  "model_reason": "fast_path_simple_intent",
  "tokens_in": 51,
  "tokens_out": 22
}

❌ ممنوع

“model_used” فقط

من غير سبب

🟥 RULE 4: Tool Logs Are Atomic (Before & After)

أي Tool = عمليتين Log

BEFORE
{
  "tool": "get_patients_with_balance",
  "input_schema_version": "v1",
  "input": {
    "min_balance": 1
  }
}

AFTER
{
  "tool": "get_patients_with_balance",
  "status": "success",
  "rows_affected": 5,
  "execution_ms": 18
}


كده تفرق:

Tool غلط

Data غلط

AI غلط

🟥 RULE 5: Errors Must Be Classified (No Generic “Failed”)

❌ ممنوع كلمة:

فشل
Error
Unknown

Required Error Anatomy
{
  "error_type": "INTENT_MISMATCH | TOOL_ERROR | DB_ERROR | VALIDATION_ERROR | LLM_ERROR",
  "error_stage": "intent | model | tool | database",
  "message": "Missing appointment date",
  "recoverable": true
}

🟥 RULE 6: Conversation State Must Be Snapshotted (If Exists)

لو في سياق… لازم يتسجل

{
  "conversation_state": {
    "active_patient": "Ahmed Ali",
    "awaiting": "appointment_time"
  }
}


دي اللي بتكشف مشاكل
“هو فهم… بس نسي”

🟥 RULE 7: Logs Must Be Human-Readable + Machine-Readable

يعني:

JSON منظم

بس القيم واضحة

❌ ممنوع
{ "x1": "a", "x2": 4 }

✅ صح
{ "intent_confidence": 0.42 }

🟥 RULE 8: No Sensitive Data in Logs (Ever)

❌ ممنوع:

أرقام بطاقات

تشخيص طبي مفصل

ملاحظات خاصة

Allowed

IDs

Summary

Hash / Masked values

🟥 RULE 9: Log Levels Are Not Optional

كل Log لازم Level:

Level	يستخدم إمتى
INFO	Flow طبيعي
WARN	ثقة ضعيفة / تصحيح
ERROR	فشل
CRITICAL	كسر سيستم
🟥 RULE 10: Log Latency at Every Layer

لازم تعرف الوقت راح فين:

{
  "latency": {
    "intent_ms": 4,
    "llm_ms": 612,
    "tool_ms": 18,
    "total_ms": 698
  }
}


دي بتكشف bottleneck فورًا

🟥 RULE 11: Prompt Version Is Mandatory
{
  "prompt_version": "appointments_v1.3.2"
}


أي Bug بدون version = صداع مزمن

🟥 RULE 12: Never Log Only on Failure

❌ غلط:

نسجل لما يغلط بس

✅ صح:

Success + Failure

عشان تعرف الفرق

🧩 الشكل النهائي للـ Log (Golden Sample)
{
  "trace_id": "uuid",
  "timestamp": "...",
  "user_id": "...",
  "tenant_id": "...",
  "query": "احجزلي احمد بكرة",
  "intent": "ADD_APPOINTMENT",
  "confidence": 0.61,
  "decision_path": "LLM_CONFIRMATION → TOOL",
  "model": {
    "name": "llama-3.1-8b-instant",
    "reason": "date_missing",
    "tokens": { "in": 44, "out": 19 }
  },
  "tool": {
    "name": "add_appointment",
    "status": "success"
  },
  "latency_ms": 713,
  "prompt_version": "appointments_v1.3.2",
  "level": "INFO"
}
