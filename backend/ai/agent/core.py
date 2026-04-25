"""
AI Agent Core
Orchestration layer for LLM interaction.
"""

from typing import Dict, List, Optional, Any
import os
import json
import logging
import httpx
from groq import AsyncGroq
from .limiter import rate_limiter
from .prompt import build_system_prompt
from .router import SmartModelRouter
from ...rag.store import knowledge_store
from .circuit_breaker import ai_circuit_breaker
from backend.ai.privacy.scrubber import scrubber

# Logger Setup
logger = logging.getLogger(__name__)


class AIAgent:
    def __init__(self):
        # Initialize Groq client
        api_key = os.getenv("GROQ_API_KEY")
        self.mock_mode = False

        if not api_key:
            logger.warning("WARNING: GROQ_API_KEY not found. Switching to MOCK MODE.")
            self.mock_mode = True
            self.client = None
        else:
            # Use httpx.AsyncClient with specific limits
            http_client = httpx.AsyncClient(
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                timeout=httpx.Timeout(60.0, connect=15.0)
            )
            self.client = AsyncGroq(api_key=api_key, http_client=http_client, max_retries=2)

        self.model = "llama-3.1-8b-instant"

    async def _call_llm_safe(self, model: str, messages: List[Dict]) -> Any:
        # Wrapper for circuit breaker
        if self.mock_mode:
            logger.info("MOCK MODE: Returning simulated AI response.")
            return self._generate_mock_response(messages)

        return await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )

    def _generate_mock_response(self, messages: List[Dict]) -> Any:
        """Generate a convincing mock response for UI testing"""
        # Simple mock structure to satisfy the parser
        mock_content = json.dumps(
            {
                "tool": "response",
                "message": "⚠️ **وضع المحاكاة (Demo Mode)**\n\nلم يتم العثور على مفتاح API، لذلك أنا أرد عليك برسالة تجريبية.\n\nلتفعيل الذكاء الاصطناعي الحقيقي، يرجى إضافة variable اسمه `GROQ_API_KEY` في ملف `.env`.\n\nبياناتك المالية تبدو جيدة، ولكن لا يمكنني تحليلها بدقة بدون الاتصال بالمخ.",
            }
        )

        # Mock object mimicking OpenAI/Groq response object
        class MockMessage:
            content = mock_content

        class MockChoice:
            message = MockMessage()

        class MockResponse:
            choices = [MockChoice()]

        return MockResponse()

    async def process(
        self,
        user_input: str,
        history: Optional[List[Dict[str, str]]] = None,
        last_entity: Optional[str] = None,
        tenant_id: int = 1,
        user_id: int = 1,
        scribe_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Process natural language input and return structured command.
        """
        # Session State
        from .state_manager import state_manager

        session = state_manager.get_session(tenant_id, user_id)

        # Override last_entity if session has one
        if session.active_patient_name:
            last_entity = session.active_patient_name
        # 0. Pre-processing Intent Detection (Bypass LLM for clear intents)
        try:
            from .intent_detector import get_intent_detector

            detector = get_intent_detector()
            detected = detector.detect(user_input)
            logger.info(f"Intent detection result: {detected}")

            if detected and detected.skip_llm:
                logger.info(
                    f"Bypassing LLM - handling detected intent: {detected.intent}"
                )
                return self._handle_detected_intent(detected, user_input)
        except Exception as e:
            logger.error(f"Intent detection failed: {e}", exc_info=True)

        # 0.5 Rate Limiting check
        if not rate_limiter.check_limit(tenant_id):
            return {
                "tool": "response",
                "message": "عذراً، لقد تجاوزت حد الاستخدام اليومي المسموح به للعيادة.",
                "error": "quota_exceeded",
            }

        # Record attempt
        rate_limiter.record_usage(tenant_id)

        # --- PII SCRUBBING ---
        safe_input, aliases = scrubber.scrub(user_input)

        # 1. RAG Search (Using Safe Input)
        rag_context = None
        if tenant_id:
            try:
                results = knowledge_store.search(
                    safe_input, tenant_id=tenant_id, n_results=2
                )
                if results:
                    rag_context = "\n".join([f"- {r['text']}" for r in results])
            except Exception as e:
                logger.error(f"RAG Search failed: {e}")
        else:
            logger.warning("RAG Search skipped: No tenant_id provided.")

        # 2. Select Model (Using Safe Input)
        model_name = SmartModelRouter.select_model(safe_input)

        # 3. Build System Prompt
        system_prompt = build_system_prompt(
            last_entity, rag_context, scribe_mode=scribe_mode
        )

        # 4. Construct Messages
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for msg in history[-5:]:
                if msg.get("role") and msg.get("content"):
                    messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": safe_input})

        # 5. Call LLM with Retry & Circuit Breaker
        try:
            response = await self._call_llm_safe(model_name, messages)
            ai_circuit_breaker.record_success()

            content = response.choices[0].message.content

            # --- PII RESTORATION ---
            # Restore any aliases in the LLM's raw response (e.g. if it echoes the phone)
            content_restored = scrubber.restore(content, aliases)

            result = self._parse_response(content_restored)

            # 6. SECURITY: Scribe Mode Enforcement (Block Write Operations)
            if scribe_mode and "tool" in result and result["tool"] != "response":
                blocked_result = self._enforce_scribe_mode(result)
                if blocked_result:
                    return blocked_result

            # 7. SECURITY: Validate Parameters
            if "tool" in result and result["tool"] != "response":
                try:
                    self._validate_tool_call(result)
                except Exception as ve:
                    # Soft Repair / Graceful Error
                    logger.warning(f"Validation Error: {ve}")
                    return {
                        "tool": "response",
                        "message": f"عذراً، البيانات غير مكتملة أو غير صحيحة لتنفيذ الأمر.\nالدليل: {str(ve)}",
                        "error": "validation_error",
                    }

            result["_model_used"] = model_name

            # --- SESSION STATE UPDATE ---
            if "parameters" in result and "patient_name" in result["parameters"]:
                p_name = result["parameters"]["patient_name"]
                if p_name:
                    state_manager.update_session(
                        tenant_id,
                        user_id,
                        {
                            "active_patient_name": p_name,
                            "last_intent": result.get("tool"),
                        },
                    )

            return result

        except Exception as e:
            msg = f"DEBUG ERROR: {str(e)}"
            logger.error(f"AI Failed: {e}", exc_info=True)

            if "429" in str(e):
                msg = "الخادم مشغول حالياً، يرجى المحاولة لاحقاً."
            else:
                # Use Smart Explainer
                from backend.ai.utils.error_explainer import error_explainer

                # Try to guess tool name from context if possible, or just pass None
                # We can't easily know tool name here unless we parse it from partial response,
                # but let's pass generic error.
                msg = error_explainer.explain(str(e))

            # Graceful Error Object
            return {
                "tool": "response",
                "message": msg,
                "error": str(e),
                "is_soft_error": True,
            }

    def _enforce_scribe_mode(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Enforce scribe mode restrictions.
        In scribe mode, only read operations and note recording are allowed.
        Write operations (treatments, payments, appointments) are BLOCKED.
        """
        SCRIBE_ALLOWED_TOOLS = [
            "record_medical_note",
            "response",
            "get_patient_file",
            "get_financial_record",
            "get_appointments",
            "get_dashboard_stats",
            "get_procedure_price",
            "search_patients",
        ]

        tool_name = result.get("tool")

        if tool_name not in SCRIBE_ALLOWED_TOOLS:
            logger.warning(
                f"Scribe Mode: Blocked tool '{tool_name}' - returning note recording suggestion"
            )

            # Extract useful info for a note
            params = result.get("parameters", {})
            _patient_name = params.get("patient_name", "")
            procedure = params.get("procedure", params.get("procedure_name", ""))
            cost = params.get("cost", "")
            paid = params.get("paid_amount", params.get("amount", ""))

            # Build a note summary
            note_parts = []
            if procedure:
                note_parts.append(f"الإجراء: {procedure}")
            if cost:
                note_parts.append(f"التكلفة: {cost}")
            if paid:
                note_parts.append(f"المدفوع: {paid}")

            note_text = " | ".join(note_parts) if note_parts else "ملاحظة طبية"

            return {
                "tool": "response",
                "message": f"📝 **وضع التوثيق:** تم تسجيل الملاحظة\n{note_text}\n\n💡 لتنفيذ العملية فعلياً، اخرج من وضع التوثيق أولاً.",
                "_scribe_blocked": True,
                "_original_tool": tool_name,
                "_note_recorded": note_text,
            }

        return None  # Tool is allowed

    def _validate_tool_call(self, result: Dict[str, Any]):
        """Validate tool parameters against Pydantic schema."""
        from backend.schemas.ai_tools import TOOL_SCHEMA_MAP
        from pydantic import ValidationError

        tool_name = result.get("tool")
        params = result.get("parameters", {})

        if tool_name not in TOOL_SCHEMA_MAP:
            # Allow unknown tools? Maybe generic ones.
            # For strict mode, we might warn.
            return

        schema_model = TOOL_SCHEMA_MAP[tool_name]
        try:
            # Validate and potentially coerce types
            validated = schema_model(**params)
            # Update params with validated (coerced) values
            result["parameters"] = validated.model_dump()
        except ValidationError as e:
            # Format friendly error message
            errors = []
            for err in e.errors():
                field = err["loc"][0]
                msg = err["msg"]
                errors.append(f"{field}: {msg}")
            raise ValueError(" / ".join(errors))

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and sanitize JSON response."""
        try:
            # Clean potential markdown wrapping
            cleaned_text = (
                response_text.replace("```json", "").replace("```", "").strip()
            )
            data = json.loads(cleaned_text)

            # Normalize structure
            if "tool" not in data and "response" in data:
                # Legacy format handling
                return {"tool": "response", "message": str(data)}

            return data

        except json.JSONDecodeError:
            # Fallback for plain text responses
            return {"tool": "response", "message": response_text}

    def _handle_detected_intent(self, detected, original_input: str) -> Dict[str, Any]:
        """
        Handle intents detected by the pre-processor (bypassing LLM).
        """

        if detected.intent == "patient_registration":
            data = detected.extracted_data
            name = data.get("patient_name")
            phone = data.get("phone")
            age = data.get("age")

            # Check what's missing
            missing = []
            if not name:
                missing.append("الاسم")
            if not phone:
                missing.append("رقم التليفون")
            if not age:
                missing.append("السن")

            if missing:
                # Ask for missing data (one at a time)
                first_missing = missing[0]
                if first_missing == "الاسم":
                    msg = "تمام 👍 إيه اسم المريض؟"
                elif first_missing == "رقم التليفون":
                    msg = f"تمام، {name}. رقم التليفون إيه؟"
                elif first_missing == "السن":
                    msg = f"تمام، {name}. عمره/عمرها كام سنة؟"
                else:
                    msg = f"محتاج {first_missing} علشان أكمل التسجيل."

                return {
                    "tool": "response",
                    "message": msg,
                    "_intent": "patient_registration",
                    "_collected": data,
                }

            # All data collected

            # Phase 1: Confidence Logic
            # If High Confidence (>= 0.85) -> Auto Execute (Return Tool Call)
            if detected.confidence >= 0.85:
                # Transform to tool call
                return {
                    "tool": "create_patient",
                    "parameters": {"patient_name": name, "phone": phone, "age": age},
                    "_intent": "patient_registration_auto",
                }

            # If Medium Confidence -> Ask Confirmation
            summary = "✅ البيانات:\n"
            summary += f"• الاسم: {name}\n"
            summary += f"• السن: {age}\n"
            summary += f"• التليفون: {phone}\n\n"
            summary += "أحفظ الملف بالبيانات دي؟"

            return {
                "tool": "response",
                "message": summary,
                "_intent": "patient_registration_confirm",
                "_collected": data,
            }

        # Unknown intent (shouldn't happen)
        return {"tool": "response", "message": "من فضلك وضّح طلبك."}

    def build_system_prompt(
        self, last_entity: Optional[str] = None, rag_context: Optional[str] = None
    ) -> str:
        """Wrapper to build system prompt using the standalone function."""
        return build_system_prompt(last_entity, rag_context)


# Singleton accessor
_agent_instance = None


def get_agent():
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = AIAgent()
    return _agent_instance
