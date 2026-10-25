from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm.attributes import flag_modified
from fastapi import HTTPException

from backend import models
from backend.services.feature_service import FeatureFlagService
from backend.utils.medical_alerts import derive_medical_alerts
from backend.core.permissions import Role


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


WHITELISTED_EVENTS = {
    "patient_file_opened",
    "daily_report_viewed",
    "appointment_rescheduled",
}


class OnboardingService:
    @staticmethod
    async def get_or_create_user_state(
        db: AsyncSession, tenant_id: int, user_id: int
    ) -> models.UserOnboardingState:
        stmt = select(models.UserOnboardingState).where(
            models.UserOnboardingState.tenant_id == tenant_id,
            models.UserOnboardingState.user_id == user_id,
        )
        state = (await db.execute(stmt)).scalar_one_or_none()
        if not state:
            state = models.UserOnboardingState(
                tenant_id=tenant_id,
                user_id=user_id,
                dismissed=False,
                seen_tips=[],
                events={},
                updated_at=utc_now_naive(),
            )
            db.add(state)
            await db.flush()
        return state

    @staticmethod
    async def set_dismissed(
        db: AsyncSession, tenant_id: int, user_id: int, dismissed: bool
    ) -> models.UserOnboardingState:
        state = await OnboardingService.get_or_create_user_state(db, tenant_id, user_id)
        state.dismissed = dismissed
        state.updated_at = utc_now_naive()
        await db.commit()
        await db.refresh(state)
        return state

    @staticmethod
    async def record_tip_seen(
        db: AsyncSession, tenant_id: int, user_id: int, tip_key: str
    ) -> models.UserOnboardingState:
        state = await OnboardingService.get_or_create_user_state(db, tenant_id, user_id)
        current_tips = list(state.seen_tips or [])
        if tip_key not in current_tips:
            current_tips.append(tip_key)
            state.seen_tips = current_tips
            flag_modified(state, "seen_tips")
            state.updated_at = utc_now_naive()
            await db.commit()
            await db.refresh(state)
        return state

    @staticmethod
    async def record_event(
        db: AsyncSession, tenant_id: int, user_id: int, event_key: str, auto_commit: bool = True
    ) -> models.UserOnboardingState:
        if event_key not in WHITELISTED_EVENTS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event key '{event_key}'. Whitelisted events: {sorted(WHITELISTED_EVENTS)}",
            )

        state = await OnboardingService.get_or_create_user_state(db, tenant_id, user_id)
        events_dict = dict(state.events or {})
        events_dict[event_key] = utc_now_naive().isoformat()
        state.events = events_dict
        flag_modified(state, "events")
        state.updated_at = utc_now_naive()
        if auto_commit:
            await db.commit()
            await db.refresh(state)
        else:
            await db.flush()
        return state

    @staticmethod
    async def get_status(
        db: AsyncSession, current_user: models.User
    ) -> Dict[str, Any]:
        tenant_id = current_user.tenant_id
        user_role = (current_user.role or "").lower()

        # Disallowed roles: nurse, assistant, patient, guest, super_admin, or missing tenant
        disallowed_roles = {
            Role.NURSE.value,
            Role.ASSISTANT.value,
            Role.PATIENT.value,
            Role.GUEST.value,
            Role.SUPER_ADMIN.value,
        }

        if not tenant_id or user_role in disallowed_roles:
            return {
                "enabled": False,
                "role": user_role,
                "dismissed": False,
                "seen_tips": [],
                "progress": {"total": 0, "completed": 0, "percentage": 0},
                "sections": [],
                "steps": [],
            }

        is_enabled = await FeatureFlagService.is_feature_enabled(
            db, "onboarding_checklist", tenant_id
        )
        if not is_enabled:
            return {
                "enabled": False,
                "role": user_role,
                "dismissed": False,
                "seen_tips": [],
                "progress": {"total": 0, "completed": 0, "percentage": 0},
                "sections": [],
                "steps": [],
            }

        user_state = await OnboardingService.get_or_create_user_state(
            db, tenant_id, current_user.id
        )
        user_events = dict(user_state.events or {})

        # Compute signals
        # M1 clinic data: Tenant.clinic_address OR clinic_phone not null
        stmt_tenant = select(models.Tenant).where(models.Tenant.id == tenant_id)
        tenant = (await db.execute(stmt_tenant)).scalar_one_or_none()
        m1_done = False
        m4_done = False
        if tenant:
            has_addr = bool(tenant.clinic_address and tenant.clinic_address.strip())
            has_phone = bool(tenant.clinic_phone and tenant.clinic_phone.strip())
            m1_done = has_addr or has_phone

            freq_active = bool(
                tenant.backup_frequency and tenant.backup_frequency.strip().lower() != "off"
            )
            has_google = bool(tenant.google_refresh_token)
            has_backup = bool(tenant.last_backup_at)
            m4_done = freq_active or has_google or has_backup

        # M2 procedures: COUNT(procedures WHERE tenant_id == :tenant_id) > 0
        stmt_m2 = select(func.count(models.Procedure.id)).where(
            models.Procedure.tenant_id == tenant_id
        )
        m2_count = (await db.execute(stmt_m2)).scalar() or 0
        m2_done = m2_count > 0

        # M3 team: COUNT(users, not deleted) > 1
        stmt_m3 = select(func.count(models.User.id)).where(
            models.User.tenant_id == tenant_id,
            or_(models.User.is_deleted == False, models.User.is_deleted.is_(None)),
        )
        m3_count = (await db.execute(stmt_m3)).scalar() or 0
        m3_done = m3_count > 1

        # Reception signals
        stmt_r1 = select(func.count(models.Patient.id)).where(
            models.Patient.tenant_id == tenant_id,
            models.Patient.is_deleted == False,
        )
        r1_count = (await db.execute(stmt_r1)).scalar() or 0
        r1_done = r1_count > 0

        stmt_r2 = select(func.count(models.Appointment.id)).where(
            models.Appointment.tenant_id == tenant_id,
            models.Appointment.is_deleted == False,
        )
        r2_count = (await db.execute(stmt_r2)).scalar() or 0
        r2_done = r2_count > 0

        r3_done = bool(user_events.get("appointment_rescheduled"))

        # R4 chronic/pregnancy: mirror derive_medical_alerts
        stmt_r4 = select(models.Patient.medical_history).where(
            models.Patient.tenant_id == tenant_id,
            models.Patient.is_deleted == False,
        )
        histories = (await db.execute(stmt_r4)).scalars().all()
        r4_done = any(
            bool(derive_medical_alerts(h).get("has_alert") or derive_medical_alerts(h).get("has_alerts"))
            for h in histories
            if h
        )

        # Doctor signals
        d1_done = bool(user_events.get("patient_file_opened"))

        # D2 odontogram: legacy tooth_status condition != 'Healthy' OR clinical work items finding
        stmt_d2_legacy = select(func.count(models.ToothStatus.id)).where(
            models.ToothStatus.tenant_id == tenant_id,
            models.ToothStatus.condition != "Healthy",
        )
        d2_legacy = (await db.execute(stmt_d2_legacy)).scalar() or 0

        stmt_d2_vnext = select(func.count(models.ClinicalWorkItem.id)).where(
            models.ClinicalWorkItem.tenant_id == tenant_id,
            models.ClinicalWorkItem.kind == "finding",
        )
        d2_vnext = (await db.execute(stmt_d2_vnext)).scalar() or 0
        d2_done = (d2_legacy > 0) or (d2_vnext > 0)

        # D3 procedure recorded: COUNT(treatments) > 0
        stmt_d3 = select(func.count(models.Treatment.id)).where(
            models.Treatment.tenant_id == tenant_id,
            models.Treatment.is_deleted == False,
        )
        d3_count = (await db.execute(stmt_d3)).scalar() or 0
        d3_done = d3_count > 0

        # D4 treatment plan: COUNT(clinical_treatment_plans) > 0 (Gated by clinical_treatment_plans)
        treatment_plans_enabled = await FeatureFlagService.is_feature_enabled(
            db, "clinical_treatment_plans", tenant_id
        )
        d4_done = False
        if treatment_plans_enabled:
            stmt_d4 = select(func.count(models.ClinicalTreatmentPlan.id)).where(
                models.ClinicalTreatmentPlan.tenant_id == tenant_id,
            )
            d4_count = (await db.execute(stmt_d4)).scalar() or 0
            d4_done = d4_count > 0

        # D5 lab: 3 sub-steps
        stmt_d5_labs = select(func.count(models.Laboratory.id)).where(
            models.Laboratory.tenant_id == tenant_id,
        )
        d5_labs_count = (await db.execute(stmt_d5_labs)).scalar() or 0
        d5_sub1 = d5_labs_count > 0

        stmt_d5_orders = select(func.count(models.LabOrder.id)).where(
            models.LabOrder.tenant_id == tenant_id,
        )
        d5_orders_count = (await db.execute(stmt_d5_orders)).scalar() or 0
        d5_sub2 = d5_orders_count > 0

        stmt_d5_recv = select(func.count(models.LabOrder.id)).where(
            models.LabOrder.tenant_id == tenant_id,
            or_(
                models.LabOrder.received_date.isnot(None),
                func.lower(models.LabOrder.status) == "completed",
            ),
        )
        d5_recv_count = (await db.execute(stmt_d5_recv)).scalar() or 0
        d5_sub3 = d5_recv_count > 0
        d5_done = d5_sub1 and d5_sub2 and d5_sub3

        # Accountant signals
        native_writes_enabled = await FeatureFlagService.is_feature_enabled(
            db, "clinical_vnext_native_writes", tenant_id
        )
        a1_done = False
        if native_writes_enabled:
            stmt_a1 = select(func.count(models.ClinicalCharge.id)).where(
                models.ClinicalCharge.tenant_id == tenant_id,
                models.ClinicalCharge.status == "invoiced",
            )
            a1_count = (await db.execute(stmt_a1)).scalar() or 0
            a1_done = a1_count > 0

        stmt_a2 = select(func.count(models.Payment.id)).where(
            models.Payment.tenant_id == tenant_id,
        )
        a2_count = (await db.execute(stmt_a2)).scalar() or 0
        a2_done = a2_count > 0

        a3_done = bool(user_events.get("daily_report_viewed"))

        # Step builders
        manager_steps = [
            {
                "id": "m1_clinic_data",
                "key": "M1",
                "title": "بيانات العيادة",
                "description": "أدخل عنوان العيادة أو رقم الهاتف للتواصل",
                "link": "/settings?tab=general",
                "done": m1_done,
                "highlight": False,
            },
            {
                "id": "m2_procedures",
                "key": "M2",
                "title": "قائمة الإجراءات والخدمات",
                "description": "حدد الاسم والسعر والشكل واللون لكل إجراء لتسهيل العمل على المخطط",
                "link": "/settings?tab=services",
                "done": m2_done,
                "highlight": True,
            },
            {
                "id": "m3_team",
                "key": "M3",
                "title": "فريق العمل",
                "description": "أضف أفراد الفريق وحدد أدوارهم وصلاحياتهم",
                "link": "/users",
                "done": m3_done,
                "highlight": False,
            },
            {
                "id": "m4_backup",
                "key": "M4",
                "title": "النسخ الاحتياطي",
                "description": "قم بتفعيل النسخ الاحتياطي لحماية بيانات العيادة",
                "link": "/settings?tab=backup",
                "done": m4_done,
                "highlight": False,
            },
        ]

        doctor_steps = [
            {
                "id": "d1_patient_file",
                "key": "D1",
                "title": "فتح ملف المريض",
                "description": "افتح الملف الطبي لأي مريض لاستعراض التاريخ والمخطط",
                "link": "/patients",
                "done": d1_done,
                "highlight": False,
            },
            {
                "id": "d2_odontogram",
                "key": "D2",
                "title": "تسجيل حالة على المخطط",
                "description": "حدد سناً وسجل حالته السريرية على المخطط السني",
                "link": "/patients",
                "done": d2_done,
                "highlight": False,
            },
            {
                "id": "d3_procedure",
                "key": "D3",
                "title": "تسجيل إجراء علاجي",
                "description": "سجل إجراءً علاجياً تم تنفيذه للمريض",
                "link": "/patients",
                "done": d3_done,
                "highlight": False,
            },
        ]

        if treatment_plans_enabled:
            doctor_steps.append({
                "id": "d4_treatment_plan",
                "key": "D4",
                "title": "إنشاء خطة علاجية",
                "description": "نظم الجلسات والمراحل في خطة علاجية متكاملة",
                "link": "/patients",
                "done": d4_done,
                "highlight": False,
            })

        doctor_steps.append({
            "id": "d5_lab_tour",
            "key": "D5",
            "title": "جولة المعامل والتركيبات",
            "description": "أضف معملاً، أنشئ طلب تركيبة، وسجل استلامها من المعمل",
            "link": "/labs",
            "done": d5_done,
            "highlight": False,
            "sub_steps": [
                {"key": "lab_added", "title": "إضافة معمل", "done": d5_sub1},
                {"key": "order_created", "title": "إنشاء طلب عمل", "done": d5_sub2},
                {"key": "order_received", "title": "استلام الطلب من المعمل", "done": d5_sub3},
            ],
        })

        reception_steps = [
            {
                "id": "r1_first_patient",
                "key": "R1",
                "title": "إضافة أول مريض",
                "description": "سجل بيانات مريض جديد في النظام",
                "link": "/patients",
                "done": r1_done,
                "highlight": False,
            },
            {
                "id": "r2_appointment",
                "key": "R2",
                "title": "حجز أول موعد",
                "description": "حدد موعداً للمريض مع الطبيب المعالج",
                "link": "/appointments",
                "done": r2_done,
                "highlight": False,
            },
            {
                "id": "r3_reschedule",
                "key": "R3",
                "title": "تعديل أو إعادة جدولة موعد",
                "description": "قم بتغيير توقيت أو تاريخ موعد محجوز",
                "link": "/appointments",
                "done": r3_done,
                "highlight": False,
            },
            {
                "id": "r4_chronic_pregnancy",
                "key": "R4",
                "title": "تسجيل تنبيه صحي أو حمل",
                "description": "سجل أمراضاً مزمنة أو حالة حمل في التاريخ الطبي للمريض",
                "link": "/patients",
                "done": r4_done,
                "highlight": False,
            },
        ]

        accountant_steps = []
        if native_writes_enabled:
            accountant_steps.append({
                "id": "a1_invoice",
                "key": "A1",
                "title": "إصدار فاتورة",
                "description": "قم بتحويل الإجراء المالي إلى فاتورة رسمية",
                "link": "/finance/overview",
                "done": a1_done,
                "highlight": False,
            })
        accountant_steps.extend([
            {
                "id": "a2_payment",
                "key": "A2",
                "title": "تسجيل دفعة نقدية",
                "description": "سجل استلام دفعة من المريض لحسابه",
                "link": "/finance/cash-movements/payments",
                "done": a2_done,
                "highlight": False,
            },
            {
                "id": "a3_daily_report",
                "key": "A3",
                "title": "الاطلاع على التقرير المالي اليومي",
                "description": "استعرض تقرير الحركة المالية والتحصيلات لليوم",
                "link": "/finance/reports",
                "done": a3_done,
                "highlight": False,
            },
        ])

        sections = []
        if user_role == Role.ADMIN.value:
            sections = [
                {"id": "manager", "title": "إعداد العيادة", "steps": manager_steps},
                {"id": "doctor", "title": "العمل السريري والمخطط", "steps": doctor_steps},
            ]
        elif user_role == Role.MANAGER.value:
            sections = [
                {"id": "manager", "title": "إعداد العيادة", "steps": manager_steps},
            ]
        elif user_role == Role.DOCTOR.value:
            sections = [
                {"id": "doctor", "title": "العمل السريري والمخطط", "steps": doctor_steps},
            ]
        elif user_role == Role.RECEPTIONIST.value:
            sections = [
                {"id": "reception", "title": "الاستقبال والحجوزات", "steps": reception_steps},
            ]
        elif user_role == Role.ACCOUNTANT.value:
            sections = [
                {"id": "accountant", "title": "المالية والحسابات", "steps": accountant_steps},
            ]
        else:
            return {
                "enabled": False,
                "role": user_role,
                "dismissed": False,
                "seen_tips": [],
                "progress": {"total": 0, "completed": 0, "percentage": 0},
                "sections": [],
                "steps": [],
            }

        # Flatten steps
        all_steps = []
        for sec in sections:
            all_steps.extend(sec["steps"])

        total_steps = len(all_steps)
        completed_steps = sum(1 for s in all_steps if s["done"])
        percentage = round((completed_steps / total_steps) * 100) if total_steps > 0 else 0

        return {
            "enabled": True,
            "role": user_role,
            "dismissed": bool(user_state.dismissed),
            "seen_tips": list(user_state.seen_tips or []),
            "progress": {
                "total": total_steps,
                "completed": completed_steps,
                "percentage": percentage,
            },
            "sections": sections,
            "steps": all_steps,
        }
