from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import json
import logging
import re
import uuid
from typing import Optional, List, Dict, Any

from backend import models
from backend.schemas.ai import AIQueryResponse, Message
from backend.ai.agent.core import get_agent
from backend.ai.executor import ToolExecutor
from backend.ai.tools.security import get_tool_risk
from backend.ai.validation_layer import AIValidationLayer
from backend.ai.security.sanitizer import AISanitizer
from backend.ai.errors import AIException, AISystemError
from backend.ai.policy.execution_policy import policy_engine
from backend.ai.agent.state_manager import state_manager

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, db: Session, user: models.User):
        self.db = db
        self.user = user
        self.tenant = user.tenant
        self.agent = get_agent()
        self.executor = ToolExecutor(db, user)

    async def analyze_direct(self, prompt: str) -> AIQueryResponse:
        """
        Direct simplified analysis skipping the full agent loop.
        Optimized for dashboard widgets and reports.
        """
        # 1. Mock Mode Check
        if hasattr(self.agent, 'mock_mode') and self.agent.mock_mode:
            return AIQueryResponse(
                success=True,
                message="⚠️ **وضع المحاكاة (Demo Mode)**\n\nتحليل سريع (Mock):\n1. الإيرادات ممتازة.\n2. التكاليف تحت السيطرة.\n3. يرجى تفعيل مفتاح API للحصول على تحليل حقيقي.",
                tool="response"
            )

        # 2. Direct LLM Call
        try:
            messages = [
                {"role": "system", "content": "You are a senior financial advisor for a dental clinic in Egypt. Provide concise, actionable insights in Arabic. Format as a clean Markdown list. Keep it under 200 words."},
                {"role": "user", "content": f"{prompt}\n\nIMPORTANT: Respond in Arabic language only."}
            ]
            
            # Use the agent's safe call wrapper or client directly
            # Agent's _call_llm_safe handles mock check too, but we want to be explicit about model
            response = self.agent.client.chat.completions.create(
                model="llama-3.1-8b-instant", # Enforce fast model
                messages=messages,
                temperature=0.3,
            )
            
            content = response.choices[0].message.content
            
            return AIQueryResponse(
                success=True,
                message=content,
                tool="response",
                risk_level="SAFE"
            )
            
        except Exception as e:
            logger.error(f"Direct Analysis Failed: {e}")
            return AIQueryResponse(
                success=False, 
                error="analysis_failed", 
                message=f"فشل التحليل: {str(e)}"
            )

    async def process_query(self, text: str, context: Optional[List[Dict]] = None, last_patient_name: Optional[str] = None, trace_id: Optional[str] = None, scribe_mode: bool = False) -> AIQueryResponse:
        """
        Process user query through AI pipeline with structured error handling.
        """
        start_time = datetime.now()
        trace_id = trace_id or str(uuid.uuid4()) # Phase 0: Enforce Trace ID
        ai_result = {}
        final_response_data = {}
        tool_name = None

        try:
            # -1. Request Validation (Security Gate)
            AIValidationLayer.validate_request(text)

            # 0. Scrub Input
            safe_text, aliases = AIValidationLayer.scrub_input(text)

            # 1. Check Subscription & Quotas
            quota_error = self._check_subscription_quota()
            if quota_error:
                return quota_error

            # 2. Confirmation Detection
            confirmation_response = await self._detect_confirmation(safe_text, context)
            if confirmation_response:
                 return confirmation_response

            # 3. Intent Detection
            intent_response = self._detect_intent(safe_text)
            if intent_response:
                return intent_response

            # 4. Agent Processing
            ai_result = await self.agent.process(
                user_input=text, 
                history=context,
                last_entity=last_patient_name,
                tenant_id=self.user.tenant_id,
                scribe_mode=scribe_mode
            )

            # Handle Agent Errors (if agent logic returns error dict instead of raising)
            if "error" in ai_result:
                # Map to response directly
                tool_name = ai_result.get("tool", "unknown")
                final_response_data = {
                    "success": False,
                    "error": ai_result.get("error"),
                    "message": ai_result.get("message", "حدث خطأ في النظام الذكي.")
                }
            else:
                # 5. Execute Tool
                tool_name = ai_result.get("tool")
                
                if tool_name:
                    if tool_name in ["greeting", "response"]:
                         final_response_data = {
                            "success": True,
                            "message": ai_result.get("message"),
                            "tool": tool_name,
                            "risk_level": "SAFE",
                            "suggestions": ai_result.get("suggestions")
                        }
                    else:
                        # Governance Check: Confirmation
                        params = ai_result.get("parameters", {})
                        
                        if policy_engine.check_requires_confirmation(tool_name):
                            if not self.tenant:
                                return AIQueryResponse(success=False, error="tenant_required", message="عفواً، لا يمكن تنفيذ هذا الإجراء بدون عيادة مرتبطة.")

                            # Store pending action
                            state_manager.update_session(self.user.tenant_id, self.user.id, {
                                "pending_confirmation": {
                                    "tool": tool_name,
                                    "params": params
                                }
                            })
                            return AIQueryResponse(
                                success=True,
                                tool="response",
                                message=f"⚠️ هذا الإجراء ({tool_name}) يتطلب تأكيدك. هل أنت متأكد من التنفيذ؟",
                                data={"required_confirmation": True, "pending_tool": tool_name},
                                risk_level="CONFIRMATION_REQUIRED"
                            )

                        # Executor runs via Try/Except wrapper
                        tool_result = await self.executor.execute(tool_name, params)
                        
                        # Merge output
                        # Tool result already has 'success', 'error_code' etc from Executor refactor
                        if not tool_result.get("success"):
                            final_response_data = {
                                "success": False,
                                "error": tool_result.get("error_code", "execution_error"),
                                "message": tool_result.get("message", "فشل تنفيذ الأمر"),
                                "tool": tool_name,
                                "data": tool_result.get("debug_info")
                            }
                        else:
                            ai_result.update(tool_result)
                            risk_level = get_tool_risk(tool_name)
                            
                            final_response_data = {
                                "success": True,
                                "message": ai_result.get("message"),
                                "data": ai_result,
                                "tool": tool_name,
                                "risk_level": risk_level,
                                "suggestions": ai_result.get("suggestions")
                            }
                else:
                     final_response_data = {
                        "success": True, 
                        "message": ai_result.get("message", "لم أفهم الطلب."),
                        "data": ai_result
                    }

        except AIException as e:
            logger.warning(f"AI Service Exception: {e.message} ({e.code})")
            final_response_data = {
                "success": False,
                "error": e.code,
                "message": e.message,
                "data": e.debug_info
            }

        except Exception as e:
            logger.error(f"AI Service Critical Error: {e}", exc_info=True)
            final_response_data = {
                "success": False,
                "error": "internal_server_error",
                "message": f"حدث خطأ داخلي غير متوقع: {str(e)}"
            }

        finally:
            # 6. Logging
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            # Security: Sanitize Output before logging and returning
            if final_response_data.get("message"):
                final_response_data["message"] = AISanitizer.sanitize_html(final_response_data["message"])
                # Also mask sensitive data just in case
                final_response_data["message"] = AISanitizer.mask_sensitive_data(final_response_data["message"])
                
            self._log_usage(
                query=text,
                response_data=final_response_data,
                ai_result=ai_result,
                duration=duration,
                trace_id=trace_id,
                context=context,
                last_entity=last_patient_name,
                scribe_mode=scribe_mode
            )

        return AIQueryResponse(**final_response_data)

    def _check_subscription_quota(self) -> Optional[AIQueryResponse]:
        """Check if tenant has access and quota."""
        if not self.tenant or not self.tenant.subscription_plan:
            return None 

        plan = self.tenant.subscription_plan
        
        if not plan.is_ai_enabled:
             return AIQueryResponse(
                success=False,
                error="plan_restricted",
                message="عفواً، خدمة الذكاء الاصطناعي غير مفعلة في باقتك الحالية."
            )

        if plan.ai_daily_limit > 0:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            usage_count = self.db.query(func.count(models.AIUsageLog.id)).filter(
                models.AIUsageLog.tenant_id == self.tenant.id,
                models.AIUsageLog.created_at >= today_start
            ).scalar()
            
            if usage_count >= plan.ai_daily_limit:
                 return AIQueryResponse(
                    success=False,
                    error="limit_exceeded",
                    message=f"عفواً، استهلكت الحد اليومي ({plan.ai_daily_limit})."
                )
        return None

    async def _detect_confirmation(self, text: str, context: Optional[List[Dict]]) -> Optional[AIQueryResponse]:
        """Detect user confirmation for pending actions (Session-based or Context-based)."""
        CONFIRMATION_WORDS = ["اه", "نعم", "تمام", "اوكي", "ok", "yes", "ايوه", "ايوا", "احفظ", "سجل", "confirm"]
        REJECTION_WORDS = ["لا", "no", "cancel", "الغاء", "إلغاء", "رجوع"]
        
        user_text_lower = text.strip().lower()
        is_yes = any(word in user_text_lower for word in CONFIRMATION_WORDS)
        is_no = any(word in user_text_lower for word in REJECTION_WORDS)

        if not self.tenant or not self.user.tenant_id:
             return None

        # 1. Check Session State for Pending Confirmation
        session = state_manager.get_session(self.user.tenant_id, self.user.id)
        if session.pending_confirmation:
            if is_yes:
                pending = session.pending_confirmation
                tool_name = pending["tool"]
                params = pending["params"]
                
                # Clear pending *before* execution to prevent loops
                state_manager.update_session(self.user.tenant_id, self.user.id, {"pending_confirmation": None})
                
                # Execute
                try:
                    tool_result = await self.executor.execute(tool_name, params)
                    message = tool_result.get("message", "تم التنفيذ.")
                    
                    # If failed, append error
                    if not tool_result.get("success"):
                         return AIQueryResponse(
                            success=False,
                            error=tool_result.get("error_code", "execution_failed"),
                            message=message,
                            data=tool_result
                        )

                    return AIQueryResponse(
                        success=True,
                        tool=tool_name,
                        message=message,
                        data=tool_result,
                        risk_level="SAFE" 
                    )
                except Exception as e:
                    return AIQueryResponse(success=False, error="execution_error", message=str(e))
            
            elif is_no:
                state_manager.update_session(self.user.tenant_id, self.user.id, {"pending_confirmation": None})
                return AIQueryResponse(success=True, tool="response", message="تم إلغاء الأمر.")
        
        # 2. Legacy Regex Logic (Keep for intent detector fallback)
        if is_yes and context:
             # ... existing regex logic ...
             # Code omitted for brevity, keeping original logic if needed, but for now blocking it to rely on session?
             # Actually, let's keep the original logic for backward compatibility with the 'intent_detector' flow
             # which might not have set pending_confirmation properly if it returned early.
             # However, the IntentDetector logic in `_detect_confirmation` specifically matched regex.
             pass

        if any(word in user_text_lower for word in CONFIRMATION_WORDS):
            if context:
                for msg in reversed(context):
                    if msg.get("role") == "assistant" and "أحفظ الملف" in msg.get("content", ""):
                        content = msg.get("content", "")
                        
                        name_match = re.search(r"الاسم:\s*(.+?)[\n•]", content)
                        phone_match = re.search(r"التليفون:\s*(\d+)", content)
                        age_match = re.search(r"السن:\s*(\d+)", content)
                        
                        if name_match and phone_match and age_match:
                            try:
                                patient_params = {
                                    "patient_name": name_match.group(1).strip(),
                                    "phone": phone_match.group(1).strip(),
                                    "age": int(age_match.group(1))
                                }
                                # Executor handles try/except now, returning dict with success/error
                                result = await self.executor.execute("create_patient", patient_params)
                                
                                if not result.get("success"):
                                     return AIQueryResponse(
                                        success=False,
                                        error=result.get("error_code", "confirmation_failed"),
                                        message=result.get("message")
                                    )

                                return AIQueryResponse(
                                    success=True,
                                    tool="create_patient",
                                    message=result.get("message", "تم تسجيل المريض"),
                                    data=result
                                )
                            except Exception as e:
                                logger.error(f"Confirmation handler failed: {e}")
                                return AIQueryResponse(success=False, error="confirmation_failed", message=str(e))
                        break
        return None

    def _detect_intent(self, text: str) -> Optional[AIQueryResponse]:
        """Use lightweight intent detector to bypass LLM."""
        from backend.ai.agent.intent_detector import get_intent_detector
        try:
            detector = get_intent_detector()
            detected = detector.detect(text)
            
            if detected and detected.skip_llm:
                if detected.intent == "patient_registration":
                    data = detected.extracted_data
                    name = data.get("patient_name")
                    phone = data.get("phone")
                    age = data.get("age")
                    
                    missing = []
                    if not name: missing.append("الاسم")
                    if not phone: missing.append("رقم التليفون")
                    if not age: missing.append("السن")
                    
                    if missing:
                        first = missing[0]
                        if first == "الاسم": msg = "تمام 👍 إيه اسم المريض؟"
                        elif first == "رقم التليفون": msg = f"تمام، {name}. رقم التليفون كام؟"
                        elif first == "السن": msg = f"تمام، {name}. عمره كام سنة؟"
                        else: msg = f"محتاج {first}."
                        
                        return AIQueryResponse(
                            success=True,
                            tool="response",
                            message=msg,
                            data={"_intent": "patient_registration", "_collected": data}
                        )
                    
                    summary = f"✅ البيانات:\n• الاسم: {name}\n• السن: {age}\n• التليفون: {phone}\n\nأحفظ الملف بالبيانات دي؟"
                    return AIQueryResponse(
                        success=True,
                        tool="response",
                        message=summary,
                        data={"_intent": "patient_registration_confirm", "_collected": data}
                    )
        except Exception as e:
            logger.error(f"Intent detection error: {e}")
        return None

    def _log_usage(self, query, response_data, ai_result, duration, trace_id, context, last_entity, scribe_mode=False):
        """Log AI usage to DB."""
        try:
            trace_details = {
                "input_context": context,
                "last_entity": last_entity,
                "agent_response_raw": ai_result,
                "tool_executed": response_data.get("tool"),
                "tool_params": ai_result.get("parameters", {}) if ai_result else {},
                "final_response": response_data,
                "scribe_mode": scribe_mode
            }

            # GOVERNANCE: Unified AI Log (Rule 10 + Phase 0)
            from backend.models.ai_audit import AILog
            
            # Extract Metrics
            tokens_in = ai_result.get("usage", {}).get("prompt_tokens", 0)
            tokens_out = ai_result.get("usage", {}).get("completion_tokens", 0)
            model_used = ai_result.get("_model_used", "unknown")
            error_type = response_data.get("error") if not response_data.get("success") else None
            
            log_entry = AILog(
                trace_id=trace_id,
                tenant_id=self.user.tenant_id,
                user_id=self.user.id,
                
                # Context
                intent=ai_result.get("tool") or "chat", # TODO: Better intent tracking
                tool=response_data.get("tool"),
                model=model_used,
                
                # Payload
                input_text=query,
                output_text=response_data.get("message"),
                tool_params=json.dumps(ai_result.get("parameters", {}), default=str),
                tool_result=json.dumps(response_data.get("data", {}), default=str),
                
                # Metrics
                execution_time_ms=duration,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                confidence=1.0, # Placeholder for Phase 2
                
                # Status
                status="SUCCESS" if response_data.get("success") else "FAILURE",
                error_type=str(error_type) if error_type else None,
                
                # Governance
                policy_check=True,
                scribe_mode=scribe_mode
            )
            self.db.add(log_entry)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log AI usage: {e}")
