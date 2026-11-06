import logging
import os
import json
from typing import Dict, Any, List
from groq import Groq
from backend import models
from backend.services.ai_egress_policy import prepare_ai_messages
from backend.services.commercial_ai_guard import evaluate_commercial_ai_access
from backend.services.ai_quota_service import (
    AIQuotaService,
    isolated_accounting_session,
)
from backend.models.ai_accounting import ReservationStatus

logger = logging.getLogger(__name__)


class ScribeService:
    """
    Handles Medical Dictation Analysis using LLMs (Groq).
    """

    SYSTEM_PROMPT = """You are an expert AI Dental Scribe for "Smart Dent Clinic". Your task is to extract dental procedures and diagnoses from unstructured natural language and convert them into a strict JSON format.

OUTPUT FORMAT:
Return a SINGLE JSON object containing a list called "procedures".
{
  "procedures": [
    {
      "tooth_fdi": integer,        // ISO 3950 (FDI).
      "diagnosis": string,         // e.g., "Caries".
      "treatment": string,         // e.g., "Restoration".
      "surfaces": string,          // e.g., "MOD".
      "status": string             // "planned" or "completed".
    }
  ]
}

RULES:
1. Parse Arabic/English/Franco.
2. Convert Universal/Quadrants to FDI.
3. Default status is "completed".
"""

    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY")
        self.client = Groq(api_key=self.api_key) if self.api_key else None

    def analyze_dictation(
        self,
        text: str,
        *,
        tenant_id: int | None = None,
        user_id: int | None = None,
        parent_reservation_id: str | None = None,
        idempotency_key: str | None = None,
        session: Any = None,
    ) -> List[Dict[str, Any]]:
        """Parse text into structured dental procedures with commercial admission and accounting."""
        # 1. AI Egress & PHI protection check
        messages = prepare_ai_messages(
            [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            tenant_id=tenant_id,
        )

        reservation = None
        if tenant_id is not None:
            if session is not None:
                tenant = session.get(models.Tenant, tenant_id)
                denial = evaluate_commercial_ai_access(tenant, db_session=session)
                if denial:
                    raise ValueError(f"commercial_denied: {denial[0]}")
                reservation = AIQuotaService.reserve_quota(
                    session,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    operation="scribe",
                    payload=text,
                    idempotency_key=idempotency_key,
                    parent_reservation_id=parent_reservation_id,
                )
            else:
                with isolated_accounting_session(tenant_id=tenant_id) as acct_session:
                    tenant = acct_session.get(models.Tenant, tenant_id)
                    denial = evaluate_commercial_ai_access(tenant, db_session=acct_session)
                    if denial:
                        raise ValueError(f"commercial_denied: {denial[0]}")
                    reservation = AIQuotaService.reserve_quota(
                        acct_session,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        operation="scribe",
                        payload=text,
                        idempotency_key=idempotency_key,
                        parent_reservation_id=parent_reservation_id,
                    )

        if reservation is not None and getattr(reservation, "is_replay", False):
            if reservation.status == ReservationStatus.CONSUMED.value:
                try:
                    cached = json.loads(reservation.reconciliation_notes or "null")
                    if isinstance(cached, dict) and cached.get("kind") == "scribe_result_v1" and isinstance(cached.get("procedures"), list):
                        return cached["procedures"]
                except (ValueError, TypeError):
                    pass
            # Re-execution is unsafe even when a previous provider result was lost.
            raise ValueError("request_already_processed" if reservation.status == ReservationStatus.CONSUMED.value else "request_pending")

        if not self.client:
            if reservation:
                if session is not None:
                    AIQuotaService.finalize_reservation(session, reservation.reservation_id,
                        ReservationStatus.RELEASED, error_reason="Provider client unavailable before dispatch")
                else:
                    with isolated_accounting_session(tenant_id=tenant_id) as acct_session:
                        AIQuotaService.finalize_reservation(acct_session, reservation.reservation_id,
                            ReservationStatus.RELEASED, error_reason="Provider client unavailable before dispatch")
            raise ValueError("Groq API Key not configured")

        try:
            completion = self.client.chat.completions.create(
                messages=messages,
                model="llama3-70b-8192",
                temperature=0,
                response_format={"type": "json_object"},
            )

            result_json = completion.choices[0].message.content
            parsed = json.loads(result_json)
            procedures = parsed.get("procedures", [])

            if reservation:
                if session is not None:
                    AIQuotaService.finalize_reservation(
                        session,
                        reservation_id=reservation.reservation_id,
                        status=ReservationStatus.CONSUMED,
                        reconciliation_notes=json.dumps({"kind": "scribe_result_v1", "procedures": procedures}),
                    )
                else:
                    with isolated_accounting_session(tenant_id=tenant_id) as acct_session:
                        AIQuotaService.finalize_reservation(
                            acct_session,
                            reservation_id=reservation.reservation_id,
                            status=ReservationStatus.CONSUMED,
                        reconciliation_notes=json.dumps({"kind": "scribe_result_v1", "procedures": procedures}),
                        )

            return procedures

        except Exception as e:
            logger.error("Scribe LLM Error: %s", e, exc_info=True)
            if reservation:
                try:
                    if session is not None:
                        AIQuotaService.finalize_reservation(
                            session,
                            reservation_id=reservation.reservation_id,
                            status=ReservationStatus.UNCERTAIN,
                            error_reason=str(e),
                        )
                    else:
                        with isolated_accounting_session(tenant_id=tenant_id) as acct_session:
                            AIQuotaService.finalize_reservation(
                                acct_session,
                                reservation_id=reservation.reservation_id,
                                status=ReservationStatus.UNCERTAIN,
                                error_reason=str(e),
                            )
                except Exception:
                    pass
            raise e
