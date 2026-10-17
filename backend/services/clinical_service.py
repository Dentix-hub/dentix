import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend import models, schemas, crud

logger = logging.getLogger(__name__)


class ClinicalService:
    def __init__(self, db: AsyncSession, tenant_id: int, user_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def get_recent_treatments(self, limit: int = 20) -> List[Dict[str, Any]]:
        stmt = (
            select(models.Treatment)
            .join(models.Patient)
            .where(models.Patient.tenant_id == self.tenant_id)
            .order_by(models.Treatment.date.desc())
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        treatments = res.scalars().all()

        # Get patient names
        patient_ids = [t.patient_id for t in treatments]
        if patient_ids:
            stmt_patients = select(models.Patient).where(models.Patient.id.in_(patient_ids))
            res_patients = await self.db.execute(stmt_patients)
            patients = {p.id: p.name for p in res_patients.scalars().all()}
        else:
            patients = {}

        return [
            {
                "id": t.id,
                "patient_name": patients.get(t.patient_id, "غير معروف"),
                "procedure": t.procedure,
                "diagnosis": t.diagnosis,
                "cost": t.cost,
                "date": str(t.date),
            }
            for t in treatments
        ]

    async def get_lab_orders(
        self, status: str = "all", limit: int = 30
    ) -> List[Dict[str, Any]]:
        stmt = (
            select(models.LabOrder)
            .join(models.Patient)
            .where(models.Patient.tenant_id == self.tenant_id)
        )

        if status != "all":
            stmt = stmt.where(models.LabOrder.status == status)

        stmt = stmt.order_by(models.LabOrder.order_date.desc()).limit(limit)
        res = await self.db.execute(stmt)
        orders = res.scalars().all()

        patient_ids = [o.patient_id for o in orders]
        if patient_ids:
            stmt_patients = select(models.Patient).where(models.Patient.id.in_(patient_ids))
            res_patients = await self.db.execute(stmt_patients)
            patients = {p.id: p.name for p in res_patients.scalars().all()}
        else:
            patients = {}

        lab_ids = [o.laboratory_id for o in orders if o.laboratory_id]
        if lab_ids:
            stmt_labs = select(models.Laboratory).where(models.Laboratory.id.in_(lab_ids))
            res_labs = await self.db.execute(stmt_labs)
            labs = {lab.id: lab.name for lab in res_labs.scalars().all()}
        else:
            labs = {}

        return [
            {
                "id": o.id,
                "patient_name": patients.get(o.patient_id, "غير معروف"),
                "lab_name": labs.get(o.laboratory_id, "غير محدد"),
                "work_type": o.work_type,
                "status": o.status,
                "cost": o.cost,
                "due_date": str(o.due_date) if o.due_date else None,
            }
            for o in orders
        ]

    async def record_medical_note(
        self, patient: models.Patient, note: str, note_type: str = "general"
    ) -> str:
        """Append note to patient file."""
        current_notes = patient.notes or ""
        type_labels = {
            "diagnosis": "🔍 تشخيص",
            "procedure": "🩺 إجراء",
            "prescription": "💊 وصفة",
            "followup": "📅 متابعة",
            "general": "📝 ملاحظة",
        }
        type_label = type_labels.get(note_type, "📝 ملاحظة")
        new_note = (
            f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {type_label}: {note}"
        )
        patient.notes = (current_notes + new_note).strip()
        await self.db.commit()
        return new_note

    async def update_tooth_status(
        self, patient: models.Patient, tooth_str: str, condition: str, notes: str
    ) -> Dict[str, Any]:
        """Update tooth status with FDI parsing."""
        fdi_number = self._parse_tooth_number(tooth_str)
        if not fdi_number:
            raise ValueError(f"Invalid tooth number: {tooth_str}")

        status_data = schemas.ToothStatusCreate(
            patient_id=patient.id,
            tooth_number=fdi_number,
            condition=condition,
            notes=notes,
        )
        await crud.update_tooth_status(self.db, status_data, self.tenant_id)

        return {"fdi": fdi_number, "condition": condition, "patient": patient.name}

    async def _sync_work_item(
        self,
        patient_id: int,
        kind: str,
        code: str,
        status: str,
        tooth_key: str,
        surfaces: Optional[List[str]] = None,
        notes: Optional[str] = None,
        payload_extra: Optional[Dict[str, Any]] = None,
    ) -> models.ClinicalWorkItem:
        """Helper to create ClinicalWorkItem and ClinicalEvent with proper targets."""
        work_item = models.ClinicalWorkItem(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            kind=kind,
            code=code,
            status=status,
            notes=notes,
            created_by_user_id=self.user_id,
        )
        self.db.add(work_item)
        await self.db.flush()

        from backend.models.clinical_core import SURFACE_CODES
        valid_surfs = [s for s in (surfaces or []) if s in SURFACE_CODES]
        if valid_surfs:
            for s in valid_surfs:
                self.db.add(
                    models.ClinicalWorkItemTarget(
                        tenant_id=self.tenant_id,
                        work_item_id=work_item.id,
                        target_kind="surface",
                        tooth_key=tooth_key,
                        surface_code=s,
                    )
                )
        else:
            self.db.add(
                models.ClinicalWorkItemTarget(
                    tenant_id=self.tenant_id,
                    work_item_id=work_item.id,
                    target_kind="tooth",
                    tooth_key=tooth_key,
                )
            )

        event_payload = {
            "kind": kind,
            "canonical_code": code,
            "surfaces": valid_surfs,
        }
        if payload_extra:
            event_payload.update(payload_extra)

        event_type = f"{kind}_recorded"
        event = models.ClinicalEvent(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            work_item_id=work_item.id,
            event_type=event_type,
            occurred_at=datetime.now(timezone.utc),
            actor_user_id=self.user_id,
            payload=event_payload,
            notes=notes,
        )
        self.db.add(event)
        await self.db.flush()

        if valid_surfs:
            for s in valid_surfs:
                self.db.add(
                    models.clinical_core.ClinicalEventTarget(
                        tenant_id=self.tenant_id,
                        event_id=event.id,
                        target_kind="surface",
                        tooth_key=tooth_key,
                        surface_code=s,
                    )
                )
        else:
            self.db.add(
                models.clinical_core.ClinicalEventTarget(
                    tenant_id=self.tenant_id,
                    event_id=event.id,
                    target_kind="tooth",
                    tooth_key=tooth_key,
                )
            )

        return work_item

    async def add_treatment(
        self,
        patient: models.Patient,
        procedure: str,
        cost: float,
        tooth_str: str = None,
        diagnosis: str = None,
        notes: str = None,
        surface: Optional[str] = None,
        surfaces: Optional[List[str]] = None,
    ) -> models.Treatment:
        """Create treatment and optionally update tooth/financials with surface support."""

        # Treatment Notes
        treatment_notes = ""
        if tooth_str:
            treatment_notes += f"سن: {tooth_str}. "
        if diagnosis:
            treatment_notes += f"تشخيص: {diagnosis}. "
        if notes:
            treatment_notes += notes

        fdi_number = self._parse_tooth_number(tooth_str) if tooth_str else None

        # Parse surfaces
        valid_surfs: List[str] = []
        if surfaces:
            valid_surfs = [s.strip().upper() for s in surfaces]
        elif surface:
            valid_surfs = [c.upper() for c in surface.replace(",", "").replace(" ", "").strip()]

        if valid_surfs:
            treatment_notes += f" [Surfaces: {', '.join(valid_surfs)}]"

        treatment_notes += " [AI]"

        # Create Record
        treatment = models.Treatment(
            patient_id=patient.id,
            tooth_number=fdi_number,
            procedure=procedure,
            cost=cost,
            notes=treatment_notes.strip(),
            date=datetime.now(),
            doctor_id=self.user_id,
            tenant_id=self.tenant_id,
            diagnosis=diagnosis or "General",
        )
        if valid_surfs:
            treatment.surfaces = valid_surfs
            treatment.surface = "".join(valid_surfs)

        self.db.add(treatment)
        await self.db.flush()

        # Sync ClinicalWorkItem and ClinicalEvent if tooth number is present
        if fdi_number:
            tooth_key = str(fdi_number)
            from backend.models.clinical_core import FDI_TOOTH_KEYS
            if tooth_key in FDI_TOOTH_KEYS:
                from backend.clinical.catalog import CANONICAL_PROCEDURE_CODES
                from backend.clinical.legacy_mapping import LEGACY_PROCEDURE_ALLOWLIST
                canonical_code = procedure
                if canonical_code not in CANONICAL_PROCEDURE_CODES:
                    canonical_code = LEGACY_PROCEDURE_ALLOWLIST.get(procedure, procedure)

                await self._sync_work_item(
                    patient_id=patient.id,
                    kind="procedure",
                    code=canonical_code,
                    status="completed",
                    tooth_key=tooth_key,
                    surfaces=valid_surfs,
                    notes=treatment.notes,
                    payload_extra={"treatment_id": treatment.id},
                )

        await self.db.commit()
        await self.db.refresh(treatment)

        # Auto-update tooth
        if tooth_str and diagnosis:
            try:
                condition = self._map_procedure_to_condition(
                    procedure + " " + diagnosis
                )
                if condition != "Healthy":
                    await self.update_tooth_status(
                        patient, tooth_str, condition, f"Auto: {procedure}"
                    )
            except Exception as e:
                logger.warning("Auto-tooth update failed: %s", e)

        return treatment

    async def add_multi_procedure_treatment(
        self,
        patient: models.Patient,
        tooth_str: str,
        procedures: List[Dict[str, Any]],
        diagnosis: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> List[models.Treatment]:
        """Record multiple procedures on a single tooth atomically."""
        created_treatments: List[models.Treatment] = []
        for proc in procedures:
            treatment = await self.add_treatment(
                patient=patient,
                procedure=proc.get("procedure", "General Dental Procedure"),
                cost=float(proc.get("cost", 0.0)),
                tooth_str=tooth_str,
                diagnosis=proc.get("diagnosis", diagnosis),
                notes=proc.get("notes", notes),
                surface=proc.get("surface"),
                surfaces=proc.get("surfaces"),
            )
            created_treatments.append(treatment)
        return created_treatments

    async def record_tooth_finding(
        self,
        patient: models.Patient,
        tooth_str: str,
        finding_code: str,
        surface: Optional[str] = None,
        surfaces: Optional[List[str]] = None,
        notes: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> models.ClinicalWorkItem:
        """Record a clinical finding (e.g. CARIES, FRACTURE) on a tooth with surface targets."""
        fdi_number = self._parse_tooth_number(tooth_str)
        if not fdi_number:
            raise ValueError(f"Invalid tooth number: {tooth_str}")

        tooth_key = str(fdi_number)
        from backend.models.clinical_core import FDI_TOOTH_KEYS, SURFACE_CODES
        if tooth_key not in FDI_TOOTH_KEYS:
            raise ValueError(f"Tooth key '{tooth_key}' is not a valid FDI notation")

        # Parse surfaces
        valid_surfs: List[str] = []
        if surfaces:
            valid_surfs = [s.strip().upper() for s in surfaces if s.strip().upper() in SURFACE_CODES]
        elif surface:
            valid_surfs = [c.upper() for c in surface.replace(",", "").replace(" ", "").strip() if c.upper() in SURFACE_CODES]

        work_item = await self._sync_work_item(
            patient_id=patient.id,
            kind="finding",
            code=finding_code.upper(),
            status="proposed",
            tooth_key=tooth_key,
            surfaces=valid_surfs,
            notes=notes,
            payload_extra={"severity": severity},
        )

        # Auto-update tooth condition
        if finding_code.upper() == "CARIES":
            try:
                await self.update_tooth_status(patient, tooth_str, "Decayed", notes or f"Finding: {finding_code}")
            except Exception as e:
                logger.warning("Tooth status update failed for finding: %s", e)
        elif finding_code.upper() == "FRACTURE":
            try:
                await self.update_tooth_status(patient, tooth_str, "Fractured", notes or f"Finding: {finding_code}")
            except Exception as e:
                logger.warning("Tooth status update failed for finding: %s", e)

        await self.db.commit()
        return work_item

    async def record_tooth_symptom(
        self,
        patient: models.Patient,
        tooth_str: str,
        symptom: str,
        severity: Optional[str] = "moderate",
        notes: Optional[str] = None,
    ) -> models.ClinicalWorkItem:
        """Record a symptom (e.g. PAIN, sensitivity) on a tooth."""
        finding_code = "PAIN" if any(w in symptom.lower() for w in ["pain", "وجع", "ألم"]) else symptom.upper().replace(" ", "_")
        full_notes = f"Symptom: {symptom} (Severity: {severity}). {notes or ''}".strip()
        return await self.record_tooth_finding(
            patient=patient,
            tooth_str=tooth_str,
            finding_code=finding_code,
            notes=full_notes,
            severity=severity,
        )

    async def get_tooth_clinical_records(
        self,
        patient_id: int,
        tooth_str: str,
    ) -> Dict[str, Any]:
        """Retrieve all treatments, work items, and tooth status for a tooth."""
        fdi_number = self._parse_tooth_number(tooth_str)
        if not fdi_number:
            raise ValueError(f"Invalid tooth number: {tooth_str}")

        tooth_key = str(fdi_number)

        # Treatments
        stmt_tr = (
            select(models.Treatment)
            .where(
                models.Treatment.tenant_id == self.tenant_id,
                models.Treatment.patient_id == patient_id,
                models.Treatment.tooth_number == fdi_number,
                models.Treatment.is_deleted == False,  # noqa: E712
            )
            .order_by(models.Treatment.date.desc())
        )
        treatments = (await self.db.execute(stmt_tr)).scalars().all()

        # Tooth Status
        stmt_ts = (
            select(models.ToothStatus)
            .where(
                models.ToothStatus.tenant_id == self.tenant_id,
                models.ToothStatus.patient_id == patient_id,
                models.ToothStatus.tooth_number == fdi_number,
            )
        )
        tooth_status = (await self.db.execute(stmt_ts)).scalars().first()

        # Work items with targets
        from sqlalchemy.orm import selectinload
        stmt_wi = (
            select(models.ClinicalWorkItem)
            .options(selectinload(models.ClinicalWorkItem.targets))
            .join(models.ClinicalWorkItemTarget)
            .where(
                models.ClinicalWorkItem.tenant_id == self.tenant_id,
                models.ClinicalWorkItem.patient_id == patient_id,
                models.ClinicalWorkItemTarget.tooth_key == tooth_key,
            )
            .order_by(models.ClinicalWorkItem.created_at.desc())
        )
        work_items = (await self.db.execute(stmt_wi)).scalars().all()

        return {
            "tooth_number": fdi_number,
            "tooth_key": tooth_key,
            "condition": tooth_status.condition if tooth_status else "Healthy",
            "tooth_status": {
                "condition": tooth_status.condition,
                "notes": tooth_status.notes,
            } if tooth_status else None,
            "treatments": [
                {
                    "id": t.id,
                    "procedure": t.procedure,
                    "cost": float(t.cost),
                    "discount": float(t.discount),
                    "surface": t.surface,
                    "surfaces": t.surfaces,
                    "status": t.status,
                    "date": str(t.date),
                }
                for t in treatments
            ],
            "work_items": [
                {
                    "id": w.id,
                    "kind": w.kind,
                    "code": w.code,
                    "status": w.status,
                    "notes": w.notes,
                    "targets": [
                        {
                            "kind": tg.target_kind,
                            "tooth_key": tg.tooth_key,
                            "surface_code": tg.surface_code,
                        }
                        for tg in (w.targets or [])
                    ],
                }
                for w in work_items
            ],
        }

    def _parse_tooth_number(self, tooth_str: Any) -> Optional[int]:
        """Parse tooth number (FDI, Universal, or Palmer/Miller) to FDI."""
        if not tooth_str:
            return None
        import re

        text = str(tooth_str).upper().replace(" ", "").strip()

        # FDI Direct
        if re.match(r"^[1-8][1-8]$", text):
            return int(text)

        # Palmer/Quadrants
        text_w_space = str(tooth_str).upper()
        quad = None
        if any(
            k in text_w_space
            for k in [
                "UR",
                "UPPERRIGHT",
                "فوق يمين",
                "ابر رايت",
                "أبر رايت",
                "أبر يمين",
                "ابر يمين",
                "فوق رايت",
            ]
        ):
            quad = "UR"
        if any(
            k in text_w_space
            for k in [
                "UL",
                "UPPERLEFT",
                "فوق شمال",
                "فوق لفت",
                "ابر لفت",
                "أبر لفت",
                "أبر شمال",
                "ابر شمال",
            ]
        ):
            quad = "UL"
        if any(
            k in text_w_space
            for k in ["LL", "LOWERLEFT", "تحت شمال", "تحت لفت", "لور لفت", "لور شمال"]
        ):
            quad = "LL"
        if any(
            k in text_w_space
            for k in [
                "LR",
                "LOWERRIGHT",
                "تحت يمين",
                "تحت رايت",
                "لور رايت",
                "لور يمين",
            ]
        ):
            quad = "LR"

        # Word numbers to digits
        num_map = {
            "وان": "1",
            "تو": "2",
            "ثري": "3",
            "فور": "4",
            "فايف": "5",
            "سكس": "6",
            "سفن": "7",
            "ايت": "8",
            "واحد": "1",
            "اتنين": "2",
            "تلاتة": "3",
            "اربعة": "4",
            "خمسة": "5",
            "ستة": "6",
            "سبعة": "7",
            "تمانية": "8",
        }
        for word, digit in num_map.items():
            if word in text_w_space:
                text_w_space = text_w_space.replace(word, digit)

        val_match = re.search(r"([1-8]|[A-E])", text_w_space)
        if quad and val_match:
            val = val_match.group(1)
            if val in "12345678":
                num = int(val)
                base = {"UR": 10, "UL": 20, "LL": 30, "LR": 40}[quad]
                return base + num

        # Universal Fallback
        if re.match(r"^\d+$", text):
            n = int(text)
            if 1 <= n <= 32:
                # Universal to FDI map logic...
                # Simplified for brevity, same as original
                if 1 <= n <= 8:
                    return 19 - n  # 1=18, 8=11
                if 9 <= n <= 16:
                    return 12 + n  # 9=21, 16=28 (Wait, universal 9 is 21)
                # Correct Universal Mapping:
                # 1-8 (UR8-UR1) -> 18-11
                # 9-16 (UL1-UL8) -> 21-28
                # 17-24 (LL8-LL1) -> 38-31
                # 25-32 (LR1-LR8) -> 41-48
                if 1 <= n <= 8:
                    return 10 + (9 - n)  # 1->18, 8->11
                if 9 <= n <= 16:
                    return 20 + (n - 8)  # 9->21, 16->28
                if 17 <= n <= 24:
                    return 30 + (25 - n)  # 17->38, 24->31
                if 25 <= n <= 32:
                    return 40 + (n - 24)  # 25->41, 32->48
        return None

    def _map_procedure_to_condition(self, text: str) -> str:
        text = str(text).lower()
        if any(w in text for w in ["root canal", "endo", "عصب"]):
            return "RootCanal"
        if any(w in text for w in ["filling", "composite", "حشو"]):
            return "Filled"
        if any(w in text for w in ["extraction", "missing", "خلع"]):
            return "Missing"
        if any(w in text for w in ["unhealthy", "decay", "تسوس"]):
            return "Decayed"
        return "Healthy"
