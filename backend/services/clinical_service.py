from typing import Dict, Any, List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend import models, schemas, crud

class ClinicalService:
    def __init__(self, db: Session, tenant_id: int, user_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    def get_recent_treatments(self, limit: int = 20) -> List[Dict[str, Any]]:
        treatments = self.db.query(models.Treatment).join(
            models.Patient
        ).filter(
            models.Patient.tenant_id == self.tenant_id
        ).order_by(models.Treatment.date.desc()).limit(limit).all()
        
        # Get patient names
        patient_ids = [t.patient_id for t in treatments]
        patients = {p.id: p.name for p in self.db.query(models.Patient).filter(
            models.Patient.id.in_(patient_ids)
        ).all()} if patient_ids else {}
        
        return [
            {
                "id": t.id,
                "patient_name": patients.get(t.patient_id, "غير معروف"),
                "procedure": t.procedure,
                "diagnosis": t.diagnosis,
                "cost": t.cost,
                "date": str(t.date)
            }
            for t in treatments
        ]

    def get_lab_orders(self, status: str = "all", limit: int = 30) -> List[Dict[str, Any]]:
        query = self.db.query(models.LabOrder).join(
            models.Patient
        ).filter(
            models.Patient.tenant_id == self.tenant_id
        )
        
        if status != "all":
            query = query.filter(models.LabOrder.status == status)
        
        orders = query.order_by(models.LabOrder.order_date.desc()).limit(limit).all()
        
        patient_ids = [o.patient_id for o in orders]
        patients = {p.id: p.name for p in self.db.query(models.Patient).filter(
            models.Patient.id.in_(patient_ids)
        ).all()} if patient_ids else {}
        
        lab_ids = [o.laboratory_id for o in orders if o.laboratory_id]
        labs = {l.id: l.name for l in self.db.query(models.Laboratory).filter(
            models.Laboratory.id.in_(lab_ids)
        ).all()} if lab_ids else {}
        
        return [
            {
                "id": o.id,
                "patient_name": patients.get(o.patient_id, "غير معروف"),
                "lab_name": labs.get(o.laboratory_id, "غير محدد"),
                "work_type": o.work_type,
                "status": o.status,
                "cost": o.cost,
                "due_date": str(o.due_date) if o.due_date else None
            }
            for o in orders
        ]

    def record_medical_note(self, patient: models.Patient, note: str, note_type: str = "general") -> str:
        """Append note to patient file."""
        current_notes = patient.notes or ""
        type_labels = {
            "diagnosis": "🔍 تشخيص",
            "procedure": "🩺 إجراء",
            "prescription": "💊 وصفة",
            "followup": "📅 متابعة",
            "general": "📝 ملاحظة"
        }
        type_label = type_labels.get(note_type, "📝 ملاحظة")
        new_note = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {type_label}: {note}"
        patient.notes = (current_notes + new_note).strip()
        self.db.commit()
        return new_note

    def update_tooth_status(self, patient: models.Patient, tooth_str: str, condition: str, notes: str) -> Dict[str, Any]:
        """Update tooth status with FDI parsing."""
        fdi_number = self._parse_tooth_number(tooth_str)
        if not fdi_number:
            raise ValueError(f"Invalid tooth number: {tooth_str}")

        status_data = schemas.ToothStatusCreate(
            patient_id=patient.id,
            tooth_number=fdi_number,
            condition=condition,
            notes=notes
        )
        crud.update_tooth_status(self.db, status_data, self.tenant_id)
        
        return {
            "fdi": fdi_number,
            "condition": condition,
            "patient": patient.name
        }

    def add_treatment(self, patient: models.Patient, procedure: str, cost: float, 
                     tooth_str: str = None, diagnosis: str = None, notes: str = None) -> models.Treatment:
        """Create treatment and optionally update tooth/financials."""
        
        # Treatment Notes
        treatment_notes = ""
        if tooth_str: treatment_notes += f"سن: {tooth_str}. "
        if diagnosis: treatment_notes += f"تشخيص: {diagnosis}. "
        if notes: treatment_notes += notes
        treatment_notes += " [AI]"

        # Create Record
        treatment = models.Treatment(
            patient_id=patient.id,
            procedure=procedure,
            cost=cost,
            notes=treatment_notes.strip(),
            date=datetime.now(),
            doctor_id=self.user_id,
            tenant_id=self.tenant_id,
            diagnosis=diagnosis or "General"
        )
        self.db.add(treatment)
        self.db.commit()
        self.db.refresh(treatment)

        # Auto-update tooth
        if tooth_str and diagnosis:
            try:
                condition = self._map_procedure_to_condition(procedure + " " + diagnosis)
                if condition != "Healthy":
                    self.update_tooth_status(patient, tooth_str, condition, f"Auto: {procedure}")
            except Exception as e:
                print(f"Auto-tooth update failed: {e}")

        return treatment

    def _parse_tooth_number(self, tooth_str: Any) -> Optional[int]:
        """Parse tooth number (FDI, Universal, or Palmer/Miller) to FDI."""
        if not tooth_str: return None
        import re
        text = str(tooth_str).upper().replace(" ", "").strip()
        
        # FDI Direct
        if re.match(r'^[1-8][1-8]$', text): return int(text)

        # Palmer/Quadrants
        text_w_space = str(tooth_str).upper()
        quad = None
        if any(k in text_w_space for k in ["UR", "UPPERRIGHT", "فوق يمين", "ابر رايت", "أبر رايت", "أبر يمين", "ابر يمين", "فوق رايت"]): quad = "UR"
        if any(k in text_w_space for k in ["UL", "UPPERLEFT", "فوق شمال", "فوق لفت", "ابر لفت", "أبر لفت", "أبر شمال", "ابر شمال"]): quad = "UL"
        if any(k in text_w_space for k in ["LL", "LOWERLEFT", "تحت شمال", "تحت لفت", "لور لفت", "لور شمال"]): quad = "LL"
        if any(k in text_w_space for k in ["LR", "LOWERRIGHT", "تحت يمين", "تحت رايت", "لور رايت", "لور يمين"]): quad = "LR"
        
        # Word numbers to digits
        num_map = {"وان": "1", "تو": "2", "ثري": "3", "فور": "4", "فايف": "5", "سكس": "6", "سفن": "7", "ايت": "8",
                   "واحد": "1", "اتنين": "2", "تلاتة": "3", "اربعة": "4", "خمسة": "5", "ستة": "6", "سبعة": "7", "تمانية": "8"}
        for word, digit in num_map.items():
            if word in text_w_space:
                text_w_space = text_w_space.replace(word, digit)

        val_match = re.search(r'([1-8]|[A-E])', text_w_space)
        if quad and val_match:
            val = val_match.group(1)
            if val in "12345678":
                num = int(val)
                base = {"UR": 10, "UL": 20, "LL": 30, "LR": 40}[quad]
                return base + num

        # Universal Fallback
        if re.match(r'^\d+$', text):
            n = int(text)
            if 1 <= n <= 32:
                # Universal to FDI map logic...
                # Simplified for brevity, same as original
                if 1 <= n <= 8: return 19 - n # 1=18, 8=11
                if 9 <= n <= 16: return 12 + n # 9=21, 16=28 (Wait, universal 9 is 21)
                # Correct Universal Mapping:
                # 1-8 (UR8-UR1) -> 18-11
                # 9-16 (UL1-UL8) -> 21-28
                # 17-24 (LL8-LL1) -> 38-31
                # 25-32 (LR1-LR8) -> 41-48
                if 1 <= n <= 8: return 10 + (9 - n) # 1->18, 8->11
                if 9 <= n <= 16: return 20 + (n - 8) # 9->21, 16->28
                if 17 <= n <= 24: return 30 + (25 - n) # 17->38, 24->31
                if 25 <= n <= 32: return 40 + (n - 24) # 25->41, 32->48 
        return None

    def _map_procedure_to_condition(self, text: str) -> str:
        text = str(text).lower()
        if any(w in text for w in ["root canal", "endo", "عصب"]): return "RootCanal"
        if any(w in text for w in ["filling", "composite", "حشو"]): return "Filled"
        if any(w in text for w in ["extraction", "missing", "خلع"]): return "Missing"
        if any(w in text for w in ["unhealthy", "decay", "تسوس"]): return "Decayed"
        return "Healthy"
