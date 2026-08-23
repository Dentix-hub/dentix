"""Invoice service — assembles the authoritative printable invoice document.

The invoice is computed server-side from tenant-scoped data so printed
documents can never diverge from the patient's account, and clinic identity
always matches the requesting tenant. Clients render this DTO verbatim and
must not recompute financial figures.
"""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from ..core.money import as_decimal, quantize_money

# Platform currency for printed documents (Egyptian Pound).
INVOICE_CURRENCY = "EGP"


def build_invoice_number(tenant_id: int, patient_id: int) -> str:
    """Deterministic invoice number — identical on every reprint."""
    return f"INV-{tenant_id}-{patient_id}"


class InvoiceService:
    """Strictly initialized with (db, tenant_id) per project standards."""

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def get_patient_invoice(self, patient_id: int) -> dict | None:
        """Build the printable invoice DTO for one patient of this tenant."""
        patient_result = await self.db.execute(
            select(models.Patient).where(
                models.Patient.id == patient_id,
                models.Patient.tenant_id == self.tenant_id,
            )
        )
        patient = patient_result.scalars().first()
        if not patient:
            return None

        tenant = await self.db.get(models.Tenant, self.tenant_id)

        treatments_result = await self.db.execute(
            select(models.Treatment)
            .where(
                models.Treatment.patient_id == patient_id,
                models.Treatment.tenant_id == self.tenant_id,
                models.Treatment.is_deleted.is_(False),
            )
            .order_by(models.Treatment.date.asc(), models.Treatment.id.asc())
        )
        treatments = treatments_result.scalars().all()

        payments_result = await self.db.execute(
            select(models.Payment)
            .where(
                models.Payment.patient_id == patient_id,
                models.Payment.tenant_id == self.tenant_id,
            )
            .order_by(models.Payment.date.asc(), models.Payment.id.asc())
        )
        payments = payments_result.scalars().all()

        line_items: list[dict] = []
        gross_total = Decimal("0")
        net_total = Decimal("0")
        discount_total = Decimal("0")
        latest_activity: datetime | None = None

        for treatment in treatments:
            cost = quantize_money(as_decimal(treatment.cost))
            discount = quantize_money(as_decimal(treatment.discount))
            net = cost - discount
            gross_total += cost
            discount_total += discount
            net_total += net
            line_items.append(
                {
                    "id": treatment.id,
                    "date": treatment.date,
                    "procedure": treatment.procedure,
                    "diagnosis": treatment.diagnosis,
                    "tooth_number": treatment.tooth_number,
                    "status": treatment.status,
                    "cost": cost,
                    "discount": discount,
                    "net_amount": net,
                }
            )
            if treatment.date and (
                latest_activity is None or treatment.date > latest_activity
            ):
                latest_activity = treatment.date

        payment_items: list[dict] = []
        paid_total = Decimal("0")
        for payment in payments:
            amount = quantize_money(as_decimal(payment.amount))
            paid_total += amount
            payment_items.append(
                {
                    "id": payment.id,
                    "date": payment.date,
                    "amount": amount,
                    "notes": payment.notes,
                }
            )
            if payment.date and (
                latest_activity is None or payment.date > latest_activity
            ):
                latest_activity = payment.date

        return {
            "invoice_number": build_invoice_number(self.tenant_id, patient_id),
            "currency": INVOICE_CURRENCY,
            "clinic_name": (tenant.name if tenant else "") or "",
            "clinic_tagline": getattr(tenant, "doctor_name", None),
            "clinic_address": getattr(tenant, "clinic_address", None),
            "clinic_phone": getattr(tenant, "clinic_phone", None)
            or getattr(tenant, "contact_phone", None),
            "patient_id": patient.id,
            "patient_name": patient.name,
            "patient_phone": getattr(patient, "phone", None),
            # Immutable as-of stamp derived from data, not from wall clock,
            # so reprints carry the same date.
            "data_as_of": latest_activity,
            "line_items": line_items,
            "payments": payment_items,
            "totals": {
                "gross_total": gross_total,
                "discount_total": discount_total,
                "net_total": net_total,
                "paid_total": paid_total,
                "remaining_total": net_total - paid_total,
            },
        }
