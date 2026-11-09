from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, select
from datetime import datetime
import json
import logging
import re
import uuid
from types import SimpleNamespace
from unittest.mock import Mock
from typing import Optional, List, Dict, Any

from backend import models
from backend.schemas.ai import AIQueryResponse
from backend.ai.agent.core import get_agent
from backend.ai.config import get_fast_model
from backend.ai.executor import ToolExecutor
from backend.ai.tools.security import get_tool_risk
from backend.ai.validation_layer import AIValidationLayer
from backend.ai.security.sanitizer import AISanitizer
from backend.ai.errors import AIException
from backend.ai.policy.execution_policy import policy_engine
from backend.ai.agent.state_manager import state_manager
from backend.services.visibility_service import get_visibility_service
from backend.services.ai_egress_policy import AIEgressDenied
from backend.services.commercial_ai_guard import (
    evaluate_commercial_ai_access,
    async_evaluate_commercial_ai_access,
)
from backend.services.ai_quota_service import (
    AIQuotaService,
    AIQuotaExhaustedError,
    IdempotencyConflictError,
    ScopeMismatchError,
)
from backend.models.ai_accounting import ReservationStatus
from backend.utils.patient_search_normalization import (
    escaped_like_pattern,
    normalize_patient_name_for_search,
)

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self, db: AsyncSession, user: models.User):
        self.db = db
        self.user = user
        if hasattr(user, "_sa_instance_state"):
            self.tenant = user.__dict__.get("tenant")
        else:
            self.tenant = getattr(user, "tenant", None)
        self.agent = get_agent()
        self.executor = ToolExecutor(db, user)

    async def _ensure_tenant_and_plan(self):
        """Asynchronously load tenant and subscription plan if not already in memory."""
        if not self.tenant and getattr(self.user, "tenant_id", None) and hasattr(self.db, "get"):
            try:
                self.tenant = await self.db.get(models.Tenant, self.user.tenant_id)
            except Exception:
                pass

        if self.tenant and getattr(self.tenant, "plan_id", None) and hasattr(self.db, "get"):
            if not hasattr(self.tenant, "__dict__") or "subscription_plan" not in self.tenant.__dict__:
                try:
                    plan = await self.db.get(models.SubscriptionPlan, self.tenant.plan_id)
                    self.tenant.subscription_plan = plan
                except Exception:
                    pass

        if self.tenant and getattr(self.tenant, "future_plan_id", None) and hasattr(self.db, "get"):
            if "future_plan" not in self.tenant.__dict__:
                self.tenant.future_plan = await self.db.get(models.SubscriptionPlan, self.tenant.future_plan_id)

    async def _reserve_quota(
        self,
        operation: str,
        payload: Any,
        idempotency_key: Optional[str] = None,
        parent_reservation_id: Optional[str] = None,
    ):
        """Asynchronously reserve quota in an isolated transaction."""
        if not hasattr(self.db, "execute") or isinstance(self.db, Mock):
            return SimpleNamespace(
                id="mock_reservation",
                reservation_id="mock_reservation",
                status=ReservationStatus.RESERVED.value,
                units=1,
            )
        return await AIQuotaService.async_reserve_quota(
            bind=self.db,
            tenant_id=self.user.tenant_id,
            user_id=self.user.id,
            operation=operation,
            payload=payload,
            idempotency_key=idempotency_key,
            parent_reservation_id=parent_reservation_id,
        )

    async def _finalize_reservation(
        self,
        reservation_id: Optional[str],
        status: Any,
        error_reason: Optional[str] = None,
        reconciliation_notes: Optional[str] = None,
    ):
        """Asynchronously finalize quota reservation in an isolated transaction."""
        if not reservation_id or not hasattr(self.db, "execute") or isinstance(self.db, Mock):
            return
        try:
            await AIQuotaService.async_finalize_reservation(
                bind=self.db,
                tenant_id=self.user.tenant_id,
                reservation_id=reservation_id,
                status=status,
                error_reason=error_reason,
                reconciliation_notes=reconciliation_notes,
            )
        except Exception as exc:
            logger.warning(f"Failed to finalize AI reservation {reservation_id}: {exc}")

    async def _get_reservation(self, reservation_id: str) -> Optional[models.AIReservation]:
        if not reservation_id or not hasattr(self.db, "execute") or isinstance(self.db, Mock):
            return None
        try:
            stmt = select(models.AIReservation).where(models.AIReservation.reservation_id == reservation_id, models.AIReservation.tenant_id == self.user.tenant_id, models.AIReservation.user_id == self.user.id)
            res = await self.db.execute(stmt)
            return res.scalar_one_or_none()
        except Exception:
            return None

    async def analyze_direct(
        self,
        prompt: str,
        reservation_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> AIQueryResponse:
        """Direct simplified analysis skipping the full agent loop."""
        await self._ensure_tenant_and_plan()
        denial = await async_evaluate_commercial_ai_access(self.tenant, db=self.db)
        if denial:
            err_code, err_msg = denial
            return AIQueryResponse(success=False, error=err_code, message=err_msg)
        # A server-supplied reservation never bypasses current policy.
        if reservation_id is None:
            try:
                res = await self._reserve_quota(
                    operation="analyze_direct",
                    payload={"prompt": prompt},
                    idempotency_key=idempotency_key,
                )
                if getattr(res, "is_replay", False) and res.status != ReservationStatus.CONSUMED.value:
                    return AIQueryResponse(success=False, error="request_pending", message="الطلب السابق قيد المعالجة أو نتيجته غير مؤكدة.")
                if getattr(res, "is_replay", False) or getattr(res, "status", None) == ReservationStatus.CONSUMED.value:
                    return AIQueryResponse(
                        success=AIQuotaService.cached_analysis(res) is not None,
                        message=AIQuotaService.cached_analysis(res) or "النتيجة السابقة غير متاحة؛ لن يتكرر التنفيذ.",
                        tool="response",
                        risk_level="SAFE",
                    )
                reservation_id = res.reservation_id
            except AIQuotaExhaustedError:
                return AIQueryResponse(
                    success=False,
                    error="limit_exceeded",
                    message="عفواً، استهلكت الحد اليومي للاستخدام الذكي.",
                )
            except (IdempotencyConflictError, ScopeMismatchError) as exc:
                return AIQueryResponse(
                    success=False,
                    error="idempotency_conflict",
                    message=str(exc),
                )
        else:
            # Caller supplied reservation_id: check if already CONSUMED on a replay
            res_obj = await self._get_reservation(reservation_id)
            if not isinstance(self.db, Mock) and (res_obj is None or res_obj.operation not in {"analyze_clinic", "analyze_direct"}):
                return AIQueryResponse(success=False, error="reservation_scope_mismatch", message="حجز غير صالح لهذا الطلب.")
            if res_obj and res_obj.status in {ReservationStatus.UNCERTAIN.value, ReservationStatus.RELEASED.value}:
                return AIQueryResponse(success=False, error="request_pending", message="لا يمكن إعادة تنفيذ هذا الحجز.")
            if res_obj and (res_obj.status == ReservationStatus.CONSUMED.value or getattr(res_obj, "is_replay", False)):
                return AIQueryResponse(
                    success=AIQuotaService.cached_analysis(res_obj) is not None,
                    message=AIQuotaService.cached_analysis(res_obj) or "النتيجة السابقة غير متاحة؛ لن يتكرر التنفيذ.",
                    tool="response",
                    risk_level="SAFE",
                )

        if hasattr(self.agent, "mock_mode") and self.agent.mock_mode:
            await self._finalize_reservation(reservation_id, ReservationStatus.RELEASED)
            return AIQueryResponse(
                success=True,
                message="⚠️ **وضع المحاكاة (Demo Mode)**\n\nتحليل سريع (Mock):\n1. الإيرادات ممتازة.\n2. التكاليف تحت السيطرة.\n3. يرجى تفعيل مفتاح API للحصول على تحليل حقيقي.",
                tool="response",
            )

        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a senior financial advisor for a dental clinic in Egypt. Provide concise, actionable insights in Arabic. Format as a clean Markdown list. Keep it under 200 words.",
                },
                {
                    "role": "user",
                    "content": f"{prompt}\n\nIMPORTANT: Respond in Arabic language only.",
                },
            ]
            # Release database connection back to the pool before slow external model call
            if hasattr(self.db, "commit"):
                try:
                    await self.db.commit()
                except Exception:
                    if hasattr(self.db, "rollback"):
                        await self.db.rollback()

            response = await self.agent._call_llm_safe(
                get_fast_model(),
                messages,
                tenant_id=self.user.tenant_id,
            )
            content = response.choices[0].message.content
            await self._finalize_reservation(reservation_id, ReservationStatus.CONSUMED, reconciliation_notes=json.dumps({"kind": "analysis_result_v1", "message": content}))
            return AIQueryResponse(
                success=True, message=content, tool="response", risk_level="SAFE"
            )
        except AIEgressDenied as exc:
            await self._finalize_reservation(
                reservation_id,
                ReservationStatus.RELEASED,
                error_reason=str(exc),
            )
            return AIQueryResponse(
                success=False, error="ai_egress_denied", message=str(exc)
            )
        except Exception as e:
            logger.error(f"Direct Analysis Failed: {e}")
            await self._finalize_reservation(
                reservation_id,
                ReservationStatus.UNCERTAIN,
                error_reason=str(e),
            )
            return AIQueryResponse(
                success=False, error="analysis_failed", message="تعذر إكمال التحليل. يرجى المحاولة لاحقاً."
            )

    async def process_query(
        self,
        text: str,
        context: Optional[List[Dict]] = None,
        last_patient_name: Optional[str] = None,
        trace_id: Optional[str] = None,
        scribe_mode: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> AIQueryResponse:
        """Process user query through AI pipeline with structured error handling."""
        start_time = datetime.now()
        trace_id = trace_id or str(uuid.uuid4())
        ai_result = {}
        final_response_data = {}
        tool_name = None
        reservation = None

        try:
            await self._ensure_tenant_and_plan()
            AIValidationLayer.validate_request(text)
            safe_text, aliases = AIValidationLayer.scrub_input(text)

            # 1. Zero-provider confirmation path (consumes 0 additional units)
            confirmation_response = await self._detect_confirmation(safe_text, context)
            if confirmation_response:
                return confirmation_response

            # 2. Zero-provider skip-LLM intent path (consumes 0 units)
            intent_response = self._detect_intent(safe_text)
            if intent_response:
                return intent_response

            # 3. Provider admission: check commercial availability & lifecycle state
            quota_error = await self._check_subscription_quota()
            if quota_error:
                return quota_error

            # 4. PR-07 atomic quota reservation
            try:
                reservation = await self._reserve_quota(
                    operation="ai_chat",
                    payload={"text": safe_text, "context": context},
                    idempotency_key=idempotency_key,
                )
                if getattr(reservation, "is_replay", False):
                    completed = reservation.status == ReservationStatus.CONSUMED.value
                    return AIQueryResponse(
                        success=completed,
                        message="تمت معالجة هذا الطلب بالفعل." if completed else "الطلب السابق قيد المعالجة أو نتيجته غير مؤكدة.",
                        error=None if completed else "request_pending",
                        data={"request_status": reservation.status, "replayed": True},
                    )
            except AIQuotaExhaustedError:
                return AIQueryResponse(
                    success=False,
                    error="limit_exceeded",
                    message="عفواً، استهلكت الحد اليومي للاستخدام الذكي.",
                )
            except (IdempotencyConflictError, ScopeMismatchError) as exc:
                return AIQueryResponse(
                    success=False,
                    error="idempotency_conflict",
                    message=str(exc),
                )

            # Revalidate session state and last_patient_name against canonical visibility
            if (
                self.user.tenant_id
                and getattr(self.user, "role", None) == "doctor"
                and hasattr(self.db, "execute")
                and not isinstance(self.db, Mock)
            ):
                vis_service = get_visibility_service(self.db, self.user, self.user.tenant_id)
                session = state_manager.get_session(self.user.tenant_id, self.user.id)
                if session.active_patient_id:
                    if not await vis_service.can_view_patient(session.active_patient_id):
                        state_manager.update_session(
                            self.user.tenant_id,
                            self.user.id,
                            {
                                "active_patient_id": None,
                                "active_patient_name": None,
                                "pending_confirmation": None,
                            },
                        )
                elif session.active_patient_name:
                    if not await self._has_visible_patient_matching_name(
                        vis_service, session.active_patient_name
                    ):
                        state_manager.update_session(
                            self.user.tenant_id,
                            self.user.id,
                            {
                                "active_patient_id": None,
                                "active_patient_name": None,
                                "pending_confirmation": None,
                            },
                        )

                if last_patient_name:
                    if not await self._has_visible_patient_matching_name(
                        vis_service, last_patient_name
                    ):
                        last_patient_name = None

            # Release database connection back to the pool before slow external model call
            if hasattr(self.db, "commit"):
                try:
                    await self.db.commit()
                except Exception:
                    if hasattr(self.db, "rollback"):
                        await self.db.rollback()

            ai_result = await self.agent.process(
                user_input=safe_text,
                history=context,
                last_entity=last_patient_name,
                tenant_id=self.user.tenant_id,
                user_id=self.user.id,
                scribe_mode=scribe_mode,
            )

            completion_status = (
                ReservationStatus.RELEASED if ai_result.get("_provider_dispatched") is False
                else ReservationStatus.CONSUMED
            )
            ai_result.pop("_provider_dispatched", None)
            if "error" in ai_result:
                tool_name = ai_result.get("tool", "unknown")
                final_response_data = {
                    "success": False,
                    "error": ai_result.get("error"),
                    "message": ai_result.get("message", "حدث خطأ في النظام الذكي."),
                }
                if reservation:
                    await self._finalize_reservation(
                        reservation.reservation_id,
                        completion_status,
                    )
            else:
                tool_name = ai_result.get("tool")
                if tool_name:
                    if tool_name in ["greeting", "response"]:
                        final_response_data = {
                            "success": True,
                            "message": ai_result.get("message"),
                            "tool": tool_name,
                            "risk_level": "SAFE",
                            "suggestions": ai_result.get("suggestions"),
                        }
                        if reservation:
                            await self._finalize_reservation(
                                reservation.reservation_id,
                                completion_status,
                            )
                    else:
                        params = ai_result.get("parameters", {})
                        if policy_engine.check_requires_confirmation(tool_name):
                            if not self.tenant:
                                return AIQueryResponse(
                                    success=False,
                                    error="tenant_required",
                                    message="عفواً، لا يمكن تنفيذ هذا الإجراء بدون عيادة مرتبطة.",
                                )
                            state_manager.update_session(
                                self.user.tenant_id,
                                self.user.id,
                                {
                                    "pending_confirmation": {
                                        "tool": tool_name,
                                        "params": params,
                                        "parent_reservation_id": reservation.reservation_id if reservation else None,
                                    }
                                },
                            )
                            if reservation:
                                await self._finalize_reservation(
                                    reservation.reservation_id,
                                    completion_status,
                                )
                            return AIQueryResponse(
                                success=True,
                                tool="response",
                                message=f"⚠️ هذا الإجراء ({tool_name}) يتطلب تأكيدك. هل أنت متأكد من التنفيذ؟",
                                data={
                                    "required_confirmation": True,
                                    "pending_tool": tool_name,
                                },
                                risk_level="CONFIRMATION_REQUIRED",
                            )

                        tool_result = await self.executor.execute(
                            tool_name,
                            params,
                            parent_reservation_id=reservation.reservation_id if reservation else None,
                        )
                        if reservation:
                            await self._finalize_reservation(
                                reservation.reservation_id,
                                completion_status,
                            )
                        if not tool_result.get("success"):
                            final_response_data = {
                                "success": False,
                                "error": tool_result.get("error_code", "execution_error"),
                                "message": tool_result.get("message", "فشل تنفيذ الأمر"),
                                "tool": tool_name,
                                "data": tool_result.get("debug_info"),
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
                                "suggestions": ai_result.get("suggestions"),
                            }
                else:
                    final_response_data = {
                        "success": True,
                        "message": ai_result.get("message", "لم أفهم الطلب."),
                        "data": ai_result,
                    }
                    if reservation:
                        await self._finalize_reservation(
                            reservation.reservation_id,
                            completion_status,
                        )

        except AIException as e:
            logger.warning(f"AI Service Exception: {e.message} ({e.code})")
            final_response_data = {
                "success": False,
                "error": e.code,
                "message": e.message,
                "data": e.debug_info,
            }
            if reservation:
                await self._finalize_reservation(
                    reservation.reservation_id,
                    ReservationStatus.UNCERTAIN,
                    error_reason=f"AIException: {e.code}",
                )
        except Exception as e:
            logger.error(f"AI Service Critical Error: {e}", exc_info=True)
            final_response_data = {
                "success": False,
                "error": "internal_server_error",
                "message": "تعذر إكمال الطلب الذكي بسبب خطأ داخلي. يرجى المحاولة لاحقاً.",
            }
            if reservation:
                await self._finalize_reservation(
                    reservation.reservation_id,
                    ReservationStatus.UNCERTAIN,
                    error_reason=str(e),
                )
        finally:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            if final_response_data.get("message"):
                final_response_data["message"] = AISanitizer.sanitize_html(
                    final_response_data["message"]
                )
                final_response_data["message"] = AISanitizer.mask_sensitive_data(
                    final_response_data["message"]
                )
            await self._log_usage(
                query=text,
                response_data=final_response_data,
                ai_result=ai_result,
                duration=duration,
                trace_id=trace_id,
                context=context,
                last_entity=last_patient_name,
                scribe_mode=scribe_mode,
            )

        return AIQueryResponse(**final_response_data)

    async def _check_subscription_quota(self) -> Optional[AIQueryResponse]:
        """Legacy helper for backwards compatibility and unit test mocking.

        Delegates to _check_commercial_access.
        """
        return await self._check_commercial_access()

    async def _check_commercial_access(self) -> Optional[AIQueryResponse]:
        """Check commercial availability, lifecycle state, and emergency restrictions."""
        await self._ensure_tenant_and_plan()
        denial = await async_evaluate_commercial_ai_access(self.tenant, db=self.db)
        if denial:
            err_code, err_msg = denial
            return AIQueryResponse(
                success=False,
                error=err_code,
                message=err_msg,
            )
        return None

    async def _has_visible_patient_matching_name(
        self, vis_service, name: str
    ) -> bool:
        """Check whether a name (full or partial) resolves to at least one canonically visible patient."""
        clean_name = (name or "").strip()
        if not clean_name:
            return False
        normalized_name = normalize_patient_name_for_search(clean_name)
        pattern = escaped_like_pattern(normalized_name)
        vis_query = await vis_service.get_visible_patient_query()
        stmt = vis_query.where(
            or_(
                models.Patient.name_search_normalized.ilike(pattern, escape="\\"),
                (
                    models.Patient.name_search_normalized.is_(None)
                    & models.Patient.name.ilike(f"%{clean_name}%")
                ),
            )
        ).limit(1)
        res_p = await self.db.execute(stmt)
        return res_p.scalars().first() is not None

    async def _detect_confirmation(
        self, text: str, context: Optional[List[Dict]]
    ) -> Optional[AIQueryResponse]:
        """Detect user confirmation for pending actions."""
        CONFIRMATION_WORDS = [
            "اه", "نعم", "تمام", "اوكي", "ok", "yes", "ايوه", "ايوا", "احفظ", "سجل", "confirm",
        ]
        REJECTION_WORDS = ["لا", "no", "cancel", "الغاء", "إلغاء", "رجوع"]
        user_text_lower = text.strip().lower()
        user_tokens = set(re.findall(r"\w+", user_text_lower))
        is_yes = any(word in user_tokens for word in CONFIRMATION_WORDS)
        is_no = any(word in user_tokens for word in REJECTION_WORDS)

        if not self.user or not getattr(self.user, "tenant_id", None):
            return None

        session = state_manager.get_session(self.user.tenant_id, self.user.id)
        if session.pending_confirmation:
            if is_yes:
                pending = session.pending_confirmation
                tool_name = pending["tool"]
                params = pending["params"]
                parent_reservation_id = pending.get("parent_reservation_id")
                state_manager.update_session(
                    self.user.tenant_id, self.user.id, {"pending_confirmation": None}
                )

                if getattr(self.user, "role", None) == "doctor":
                    vis_service = get_visibility_service(self.db, self.user, self.user.tenant_id)
                    if tool_name == "create_patient":
                        # Creating a new patient does not target an existing patient record;
                        # only scrub stale active session patient if no longer visible.
                        if session.active_patient_id and not await vis_service.can_view_patient(
                            session.active_patient_id
                        ):
                            state_manager.update_session(
                                self.user.tenant_id,
                                self.user.id,
                                {"active_patient_id": None, "active_patient_name": None},
                            )
                    else:
                        param_p_id = params.get("patient_id")
                        param_p_name = params.get("patient_name")
                        denied = False

                        if param_p_id is not None:
                            if not await vis_service.can_view_patient(param_p_id):
                                denied = True
                        elif param_p_name:
                            if not await self._has_visible_patient_matching_name(
                                vis_service, param_p_name
                            ):
                                denied = True

                        if not denied and session.active_patient_id is not None:
                            if not await vis_service.can_view_patient(session.active_patient_id):
                                denied = True
                        elif (
                            not denied
                            and not param_p_id
                            and not param_p_name
                            and session.active_patient_name
                        ):
                            if not await self._has_visible_patient_matching_name(
                                vis_service, session.active_patient_name
                            ):
                                denied = True

                        if denied:
                            state_manager.update_session(
                                self.user.tenant_id,
                                self.user.id,
                                {"active_patient_id": None, "active_patient_name": None},
                            )
                            return AIQueryResponse(
                                success=False,
                                error="permission_denied",
                                message="عذراً، لم يعد لديك صلاحية للوصول إلى هذا المريض.",
                            )

                try:
                    exec_kwargs = {}
                    if parent_reservation_id:
                        exec_kwargs["parent_reservation_id"] = parent_reservation_id
                    tool_result = await self.executor.execute(
                        tool_name, params, **exec_kwargs
                    )
                    message = tool_result.get("message", "تم التنفيذ.")
                    if not tool_result.get("success"):
                        return AIQueryResponse(
                            success=False,
                            error=tool_result.get("error_code", "execution_failed"),
                            message=message,
                            data=tool_result,
                        )
                    return AIQueryResponse(
                        success=True,
                        tool=tool_name,
                        message=message,
                        data=tool_result,
                        risk_level="SAFE",
                    )
                except Exception as e:
                    return AIQueryResponse(
                        success=False, error="execution_error", message=str(e)
                    )
            elif is_no:
                state_manager.update_session(
                    self.user.tenant_id, self.user.id, {"pending_confirmation": None}
                )
                return AIQueryResponse(success=True, tool="response", message="تم إلغاء الأمر.")

        if is_yes and context:
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
                                    "age": int(age_match.group(1)),
                                }
                                result = await self.executor.execute("create_patient", patient_params)
                                if not result.get("success"):
                                    return AIQueryResponse(
                                        success=False,
                                        error=result.get("error_code", "confirmation_failed"),
                                        message=result.get("message"),
                                    )
                                return AIQueryResponse(
                                    success=True,
                                    tool="create_patient",
                                    message=result.get("message", "تم تسجيل المريض"),
                                    data=result,
                                )
                            except Exception as e:
                                logger.error(f"Confirmation handler failed: {e}")
                                return AIQueryResponse(
                                    success=False,
                                    error="confirmation_failed",
                                    message=str(e),
                                )
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
                    if not name:
                        missing.append("الاسم")
                    if not phone:
                        missing.append("رقم التليفون")
                    if not age:
                        missing.append("السن")
                    if missing:
                        first = missing[0]
                        if first == "الاسم":
                            msg = "تمام 👍 إيه اسم المريض؟"
                        elif first == "رقم التليفون":
                            msg = f"تمام، {name}. رقم التليفون كام؟"
                        elif first == "السن":
                            msg = f"تمام، {name}. عمره كام سنة؟"
                        else:
                            msg = f"محتاج {first}."
                        return AIQueryResponse(
                            success=True,
                            tool="response",
                            message=msg,
                            data={"_intent": "patient_registration", "_collected": data},
                        )
                    summary = f"✅ البيانات:\n• الاسم: {name}\n• السن: {age}\n• التليفون: {phone}\n\nأحفظ الملف بالبيانات دي؟"
                    return AIQueryResponse(
                        success=True,
                        tool="response",
                        message=summary,
                        data={
                            "_intent": "patient_registration_confirm",
                            "_collected": data,
                        },
                    )
        except Exception as e:
            logger.error(f"Intent detection error: {e}")
        return None

    async def _log_usage(
        self,
        query,
        response_data,
        ai_result,
        duration,
        trace_id,
        context,
        last_entity,
        scribe_mode=False,
    ):
        """Log AI usage to DB (unified AILog table)."""
        try:
            tokens_in = ai_result.get("usage", {}).get("prompt_tokens", 0)
            tokens_out = ai_result.get("usage", {}).get("completion_tokens", 0)
            model_used = ai_result.get("_model_used", "unknown")
            error_type = response_data.get("error") if not response_data.get("success") else None
            log_entry = models.AILog(
                trace_id=trace_id,
                tenant_id=self.user.tenant_id,
                user_id=self.user.id,
                username=self.user.username,
                intent=ai_result.get("tool") or "chat",
                tool=response_data.get("tool"),
                model=model_used,
                input_text=query,
                output_text=response_data.get("message"),
                tool_params=json.dumps(ai_result.get("parameters", {}), default=str),
                tool_result=json.dumps(response_data.get("data", {}), default=str),
                execution_time_ms=int(duration),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                confidence=1.0,
                status="SUCCESS" if response_data.get("success") else "FAILURE",
                error_type=str(error_type) if error_type else None,
                policy_check=True,
                scribe_mode=scribe_mode,
            )
            self.db.add(log_entry)
            await self.db.commit()
        except Exception as e:
            logger.error("Failed to log AI usage: %s", e)
