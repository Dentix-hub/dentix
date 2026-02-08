from typing import Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy import text
from ... import models
from .base import BaseHandler
from backend.services.patient_service import PatientService
# Security
from ..tools.security import risk_level, RiskLevel

class FinanceHandler(BaseHandler):
    """Handles payments, pricing, and financial records."""

    def __init__(self, db, user):
        super().__init__(db, user)
        # Initialize PatientService for lookups
        self.patient_service = PatientService(db, self.tenant_id)

    @risk_level(RiskLevel.SAFE)
    async def get_financial_record(self, params: Dict) -> Dict:
        """Get patient financial record."""
        name = params.get("patient_name", "")
        if not name:
            return {"error": "اسم المريض مطلوب"}

        # Find patient using Service
        patients = await self.patient_service.search_patients_by_name(name)

        if not patients:
            return {"message": f"لم يتم العثور على مريض باسم '{name}'"}

        # If multiple matches, ask for clarification
        if len(patients) > 1:
            return {
                "message": f"تم العثور على {len(patients)} مريض. يرجى تحديد الاسم بدقة:",
                "patients": [{"id": p.id, "name": p.name, "phone": p.phone} for p in patients]
            }

        # Single match
        patient = patients[0]

        # Calculate totals
        total_cost = self.db.query(models.Treatment).filter(
            models.Treatment.patient_id == patient.id
        ).with_entities(
            models.Treatment.cost
        ).all()

        total_paid = self.db.query(models.Payment).filter(
            models.Payment.patient_id == patient.id
        ).with_entities(
            models.Payment.amount
        ).all()

        cost_sum = sum(t.cost or 0 for t in total_cost)
        paid_sum = sum(p.amount or 0 for p in total_paid)
        remaining = cost_sum - paid_sum

        return {
            "message": f"الحساب المالي: {patient.name}",
            "patient_name": patient.name,
            "total_cost": cost_sum,
            "total_paid": paid_sum,
            "remaining": remaining,
            "status": "مسدد بالكامل" if remaining <= 0 else f"متبقي {remaining:.2f} جنيه"
        }

    @risk_level(RiskLevel.WRITE)
    async def create_payment(self, params: Dict) -> Dict:
        """Create a new payment for a patient."""
        patient_name = params.get("patient_name", "")
        amount = params.get("amount", 0)

        if not patient_name:
            return {"error": "missing_name", "message": "اسم المريض مطلوب"}

        try:
            amount = float(amount)
            if amount <= 0:
                return {"error": "invalid_amount", "message": "المبلغ يجب أن يكون أكبر من صفر"}
        except (ValueError, TypeError):
            return {"error": "invalid_amount", "message": "المبلغ غير صالح"}

        # Find patient using Service
        patients = await self.patient_service.search_patients_by_name(patient_name)

        if not patients:
            return {"error": "patient_not_found", "message": f"لم يتم العثور على مريض باسم '{patient_name}'"}

        # If multiple matches, ask for clarification
        if len(patients) > 1:
            return {
                "error": "multiple_patients",
                "message": f"تم العثور على {len(patients)} مريض (نسخة محدثة). يرجى تحديد الاسم بدقة:",
                "patients": [{"id": p.id, "name": p.name, "phone": p.phone} for p in patients]
            }

        # Single match
        patient = patients[0]

        # Find doctor_id from most recent treatment for this patient
        doctor_id = None
        if self.user and self.user.id:
            doctor_id = self.user.id
        else:
            # Try to get from most recent treatment
            recent_treatment = self.db.query(models.Treatment).filter(
                models.Treatment.patient_id == patient.id,
                models.Treatment.doctor_id.isnot(None)
            ).order_by(models.Treatment.date.desc()).first()
            if recent_treatment:
                doctor_id = recent_treatment.doctor_id
        
        # Create payment
        try:
            payment = models.Payment(
                patient_id=patient.id,
                doctor_id=doctor_id,
                amount=amount,
                date=datetime.now(),
                notes=f"دفعة عبر المساعد الذكي",
                tenant_id=self.tenant_id
            )
            self.db.add(payment)
            self.db.commit()
            self.db.refresh(payment)
        except Exception as e:
            self.db.rollback()
            return {"error": "payment_creation_failed", "message": f"حدث خطأ أثناء تسجيل الدفعة: {str(e)}"}

        return {
            "message": f"✅ تم تسجيل دفعة {amount:.2f} جنيه للمريض {patient.name}",
            "action": "payment_created",
            "payment": {
                "id": payment.id,
                "patient_name": patient.name,
                "amount": amount,
                "date": str(payment.date)
            },
            "suggestions": [f"حساب {patient.name}", f"ملف {patient.name}"]
        }

    @risk_level(RiskLevel.SAFE)
    async def get_procedure_price(self, params: Dict) -> Dict:
        """Get procedure price (General or Patient Specific)."""
        procedure_name = params.get("procedure_name") or params.get("query", "")
        patient_name = params.get("patient_name")
        
        procedure_name = procedure_name.strip().lower()
        
        if not procedure_name:
             return {"message": "يرجى تحديد اسم الإجراء."}

        # 1. Official Catalog Search
        catalog_query = self.db.query(models.Procedure).filter(
            models.Procedure.tenant_id == self.tenant_id,
            models.Procedure.name.ilike(f"%{procedure_name}%")
        )
        catalog_procedures = catalog_query.all()
        
        found_prices = []
        for p in catalog_procedures:
            found_prices.append({"name": p.name, "price": p.price, "source": "catalog"})
            
        # 2. History Search (Implicit) if not found in catalog
        if not found_prices:
             history_query = text("""
                SELECT procedure, cost 
                FROM treatments 
                WHERE tenant_id = :tenant_id 
                AND procedure LIKE :proc
                ORDER BY date DESC LIMIT 5
            """)
             history = self.db.execute(history_query, {"tenant_id": self.tenant_id, "proc": f"%{procedure_name}%"}).fetchall()
             if history:
                 avg = sum([h.cost for h in history]) / len(history)
                 found_prices.append({"name": procedure_name, "price": int(avg), "source": "history"})

        if not found_prices:
             return {"message": f"لم يتم العثور على إجراء باسم '{procedure_name}' في القائمة."}

        # Select best match
        best_match = found_prices[0]
        price_val = best_match['price']
        
        # 3. Handle Patient Logic
        if patient_name:
             # Find patient
             patients = await self.patient_service.search_patients_by_name(patient_name)
             if not patients:
                 return {"message": f"لم يتم العثور على مريض باسم '{patient_name}'. السعر العام هو {price_val} جنيه."}
            
             patient = patients[0] # Assume first match for now
             
             # Calculate "Pro" Price (e.g. check specific plan or history)
             # For now, we return the exact catalog price but personalized
             return {
                 "message": f"✅ التكلفة المتوقعة لـ **{patient.name}** لإجراء **{best_match['name']}** هي **{price_val:,.0f} جنيه**.",
                 "data": {"price": price_val, "patient": patient.name}
             }
        
        # 4. General Response (No Patient)
        return {
            "message": f"💰 السعر العام لـ **{best_match['name']}** يبدأ من **{price_val:,.0f} جنيه**.\n\nلتحديد السعر الدقيق (حسب الحالة أو التأمين)، يفضل تحديد اسم المريض.",
            "suggestions": ["تحديد مريض", "عرض القائمة"]
        }

    @risk_level(RiskLevel.SAFE)
    async def get_today_payments(self, params: Dict) -> Dict:
        """Get today's payments."""
        today = datetime.now().date()
        
        payments = self.db.query(models.Payment).join(
            models.Patient
        ).filter(
            models.Patient.tenant_id == self.tenant_id,
            models.Payment.date >= datetime.combine(today, datetime.min.time())
        ).all()
        
        total = sum(p.amount or 0 for p in payments)
        
        # Get patient names
        patient_ids = [p.patient_id for p in payments]
        patients = {p.id: p.name for p in self.db.query(models.Patient).filter(
            models.Patient.id.in_(patient_ids)
        ).all()} if patient_ids else {}
        
        return {
            "message": f"مدفوعات اليوم: {total:.2f} جنيه",
            "total": total,
            "count": len(payments),
            "payments": [
                {
                    "patient_name": patients.get(p.patient_id, "غير معروف"),
                    "amount": p.amount,
                    "time": p.date.strftime("%H:%M") if p.date else None,
                    "notes": p.notes
                }
                for p in payments
            ][:20]
        }

    @risk_level(RiskLevel.SAFE)
    async def get_expenses(self, params: Dict) -> Dict:
        """Get expenses for a period."""
        period = params.get("period", "month")
        today = datetime.now().date()
        
        if period == "today":
            start_date = today
        elif period == "week":
            start_date = today - timedelta(days=7)
        else:  # month
            start_date = today - timedelta(days=30)
        
        expenses = self.db.query(models.Expense).filter(
            models.Expense.tenant_id == self.tenant_id,
            models.Expense.date >= start_date
        ).all()
        
        total = sum(e.cost or 0 for e in expenses)
        
        # Group by category
        by_category = {}
        for e in expenses:
            cat = e.category or "أخرى"
            by_category[cat] = by_category.get(cat, 0) + (e.cost or 0)
        
        return {
            "message": f"المصروفات ({period}): {total:.2f} جنيه",
            "total": total,
            "count": len(expenses),
            "by_category": by_category,
            "expenses": [
                {
                    "item": e.item_name,
                    "cost": e.cost,
                    "category": e.category,
                    "date": str(e.date)
                }
                for e in expenses
            ][:20]
        }
    @risk_level(RiskLevel.SAFE)
    async def analyze_procedure_cost(self, params: Dict) -> Dict:
        """Analyze procedure cost using CostEngine."""
        procedure_name = params.get("procedure_name", "").strip()
        if not procedure_name:
            return {"message": "يرجى تحديد اسم الإجراء لتحليله."}

        # Find procedure logic similar to get_procedure_price
        proc = self.db.query(models.Procedure).filter(
            models.Procedure.tenant_id == self.tenant_id,
            models.Procedure.name.ilike(f"%{procedure_name}%")
        ).first()

        if not proc:
             return {"message": f"لم يتم العثور على إجراء باسم '{procedure_name}'."}

        # Calculate Cost
        from backend.services.cost_engine import CostEngine
        engine = CostEngine(self.db, self.tenant_id)
        analysis = engine.calculate_procedure_cost(proc.id)

        # AI Recommendations
        cost = analysis['total_estimated_cost']
        price = analysis['current_price']
        margin_pct = analysis['margin_percentage']
        
        recommendation = ""
        if margin_pct < 20:
             recommendation = f"\n⚠️ **تنبيه:** هامش الربح منخفض ({margin_pct}%). يُنصح بمراجعة السعر أو تقليل تكلفة المواد."
             target_price = cost * 1.5 # Target 33% margin
             recommendation += f"\n💡 سعر مقترح لتحقيق ربح 33%: **{target_price:,.0f} جنيه**"
        elif margin_pct > 80:
             recommendation = "\n✅ هامش ربح ممتاز."
        else:
             recommendation = "\n✅ هامش ربح جيد ومتوازن."

        # Format Response
        msg = f"📊 **تحليل تكلفة: {proc.name}**\n"
        msg += f"➖ التكلفة الفعلية (المواد): **{cost:,.2f} جنيه**\n"
        msg += f"➕ سعر البيع الحالي: **{price:,.2f} جنيه**\n"
        msg += f"💰 صافي الربح: **{analysis['profit_margin']:,.2f} جنيه** ({margin_pct}%)\n"
        msg += recommendation
        
        # Add breakdown details context for AI to answer follow-ups
        details_text = "\n\n🛠️ **تفاصيل المواد:**\n"
        for item in analysis['breakdown']:
             details_text += f"- {item['material_name']}: {item['weight_used']} (Cost: {item['estimated_cost']:.2f})\n"

        return {
            "message": msg,
            "data": analysis,
            "context_info": details_text # Helper for LLM to elaborate if asked
        }
