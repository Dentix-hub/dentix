"""
Event Handlers — Domain Event Consumers

Each handler is registered via @register_handler("event_type") and is called
by the background event_processor when a matching DomainEvent is polled.

Handlers receive the DomainEvent ORM object and should be async functions.
"""

import logging
from backend.workers.event_processor import register_handler
from backend.models.domain_event import DomainEvent
from backend import models

logger = logging.getLogger("smart_clinic.events")


@register_handler("appointment.created")
async def on_appointment_created(event: DomainEvent):
    """
    Fires when a new appointment is saved.
    Future uses: push notification, CRM sync.
    For now: structured log so we can verify the pipeline works end-to-end.
    """
    payload = event.payload or {}
    logger.info(
        "[EVENT] appointment.created | tenant=%s | patient=%s | time=%s",
        event.tenant_id,
        payload.get("patient_id"),
        payload.get("time"),
    )


@register_handler("appointment.cancelled")
async def on_appointment_cancelled(event: DomainEvent):
    """Handle appointment cancellation events."""
    payload = event.payload or {}
    logger.info(
        "[EVENT] appointment.cancelled | tenant=%s | appointment=%s | reason=%s",
        event.tenant_id,
        event.aggregate_id,
        payload.get("reason", "N/A"),
    )


@register_handler("payment.created")
async def on_payment_created(event: DomainEvent):
    """
    Fires when a payment is recorded.
    Future uses: receipt generation, SMS confirmation, financial dashboard cache invalidation.
    """
    payload = event.payload or {}
    logger.info(
        "[EVENT] payment.created | tenant=%s | patient=%s | amount=%s",
        event.tenant_id,
        payload.get("patient_id"),
        payload.get("amount"),
    )


@register_handler("treatment.created")
async def on_treatment_created(event: DomainEvent):
    """Handle treatment creation events."""
    payload = event.payload or {}
    logger.info(
        "[EVENT] treatment.created | tenant=%s | patient=%s | procedure=%s",
        event.tenant_id,
        payload.get("patient_id"),
        payload.get("procedure"),
    )


