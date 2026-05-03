from typing import Dict
from ... import models
from .base import BaseHandler

# Import Services
from ...services.analytics_service import AnalyticsService
from ...services.subscription_service import SubscriptionService
from ...services.knowledge_service import KnowledgeService


class AdminHandler(BaseHandler):
    """
    Handles admin statistics, clinic info, and reports.
    Refactored to delegate logic to Core Services.
    """

    def __init__(self, db, user: models.User):
        super().__init__(db, user)
        # Initialize Services
        self.analytics = AnalyticsService(db, self.tenant_id)
        self.subscription = SubscriptionService()  # Static methods mostly
        self.knowledge = KnowledgeService(self.tenant_id)

    async def get_dashboard_stats(self, params: Dict) -> Dict:
        """Get dashboard statistics."""
        period = params.get("period", "today")
        data = self.analytics.get_dashboard_summary(period)

        return {"message": f"📊 إحصائيات ({period})", **data}

    async def get_subscription_info(self, params: Dict) -> Dict:
        """Get subscription information for the tenant."""
        data = self.subscription.get_subscription_details(self.db, self.tenant_id)

        if not data:
            return {"error": "العيادة غير موجودة"}

        return {"message": "معلومات الاشتراك", "subscription": data}

    async def get_clinic_info(self, params: Dict) -> Dict:
        """Get clinic information."""
        data = self.analytics.get_clinic_summary()

        if not data:
            return {"error": "العيادة غير موجودة"}

        return {"message": "معلومات العيادة", "clinic": data}

    async def get_users_list(self, params: Dict) -> Dict:
        """Get list of users/doctors/staff."""
        users = (
            self.db.query(models.User)
            .filter(models.User.tenant_id == self.tenant_id)
            .all()
        )

        return {
            "message": f"قائمة المستخدمين: {len(users)} مستخدم",
            "users": [
                {
                    "id": u.id,
                    "username": u.username,
                    "full_name": u.username,  # fallback as username is often used as name
                    "role": u.role,
                    "email": u.email,
                    "is_active": True,  # No is_active on User model? Default to True
                }
                for u in users
            ],
        }

    async def get_doctor_ranking(self, params: Dict) -> Dict:
        """Get doctor ranking by revenue or patients."""
        period = params.get("period", "month")
        metric = params.get("metric", "revenue")

        data = self.analytics.get_doctor_ranking(period, metric)
        rankings = data.get("ranking", [])

        # Format message
        if rankings:
            metric_label = {"revenue": "إيرادات", "patients": "مرضى"}.get(
                metric, metric
            )
            unit = " جنيه" if metric == "revenue" else ""
            message = f"🏆 ترتيب الدكاترة ({metric_label} - {period}):\n"
            for i, r in enumerate(rankings[:5], 1):
                message += f"{i}. {r['name']}: {r['value']:,.0f}{unit}\n"
        else:
            message = "لا يوجد بيانات كافية للترتيب."

        return {"message": message, **data}

    async def compare_periods(self, params: Dict) -> Dict:
        """Compare two periods (revenue, patients, appointments)."""
        metric = params.get("metric", "revenue")
        period1 = params.get("period1", "this_month")
        period2 = params.get("period2", "last_month")

        data = self.analytics.compare_periods(period1, period2, metric)

        # Format message
        p1_val = data["period1"]["value"]
        p2_val = data["period2"]["value"]
        change = data["change_percent"]

        direction = "📈" if change > 0 else "📉" if change < 0 else "➡️"
        metric_label = {
            "revenue": "الإيرادات",
            "patients": "المرضى الجدد",
            "appointments": "المواعيد",
        }.get(metric, metric)
        unit = " جنيه" if metric == "revenue" else ""

        message = f"{direction} **مقارنة {metric_label}**\n\n"
        message += f"• {period1}: {p1_val:,.0f}{unit}\n"
        message += f"• {period2}: {p2_val:,.0f}{unit}\n"
        message += f"• التغير: {change:+.1f}%"

        return {"message": message, **data}

    async def get_ai_stats(self, params: Dict) -> Dict:
        """Get AI usage statistics."""
        period = params.get("period", "today")
        data = self.analytics.get_ai_stats(period)

        tool_text = "\n".join(
            [f"• {t['name']}: {t['count']} مرة" for t in data["top_tools"]]
        )

        message = (
            f"📊 **إحصائيات المساعد ({period})**\n\n"
            f"🔢 العدد الكلي: {data['total']}\n"
            f"✅ ناجحة: {data['success']}\n"
            f"⚡ متوسط السرعة: {data['avg_latency']:.0f}ms\n\n"
            f"**أكثر الأدوات استخداماً:**\n{tool_text}"
        )

        return {"message": message, "stats": data}

    async def learn_clinic_info(self, params: Dict) -> Dict:
        """Add info to RAG store."""
        info_text = params.get("info_text")
        category = params.get("category", "general")

        if not info_text:
            return {"error": "missing_info", "message": "لم يتم تحديد معلومة لحفظها"}

        doc_id = self.knowledge.learn_info(info_text, category)

        return {
            "message": "✅ تم حفظ المعلومة بنجاح في ذاكرة العيادة.",
            "doc_id": doc_id,
            "category": category,
        }

    async def list_my_knowledge(self, params: Dict) -> Dict:
        """List all RAG knowledge for tenant."""
        results = self.knowledge.list_knowledge()

        if not results:
            return {"message": "الذاكرة فارغة حالياً."}

        output = "📝 **المعلومات المحفوظة:**\n"
        for i, res in enumerate(results, 1):
            text_preview = (
                (res["text"][:100] + "...") if len(res["text"]) > 100 else res["text"]
            )
            output += f"{i}. [{res['id'][:8]}] {text_preview}\n"

        return {"message": output, "knowledge": results}

    async def forget_info(self, params: Dict) -> Dict:
        """Delete from RAG store."""
        item_id = params.get("item_id")

        if not item_id:
            return {"error": "missing_id", "message": "يرجى تحديد رقم المعلومة لحذفها."}

        success = self.knowledge.forget_info(item_id)

        if success:
            return {"message": f"✅ تم حذف المعلومة [{item_id}] من الذاكرة."}
        else:
            return {"error": "delete_failed", "message": "لم ينجح الحذف."}

    async def get_top_procedures(self, params: Dict) -> Dict:
        """Get top procedures by usage or revenue."""
        period = params.get("period", "month")
        limit = int(params.get("limit", 5))

        data = self.analytics.get_top_procedures(period, limit)
        top_list = data.get("top_procedures", [])

        message = f"🏆 **أكثر الإجراءات طلباً ({period})**\n"
        for i, item in enumerate(top_list, 1):
            message += f"{i}. {item['name']}: {item['count']} مرة ({item['revenue']:,.0f} ج.م)\n"

        return {"message": message, **data}

    async def get_revenue_trend(self, params: Dict) -> Dict:
        """Get revenue trend over time."""
        period = params.get("period", "year")
        data = self.analytics.get_revenue_trend(period)

        trend = data.get("trend", [])

        message = f"📈 **تطور الإيرادات ({period})**\n"
        for item in trend[-5:]:  # Show last 5
            message += f"• {item['date']}: {item['revenue']:,.0f} ج.م\n"

        return {"message": message, **data}

    async def send_appointment_reminders(self, params: Dict) -> Dict:
        """Mock: Send WhatsApp reminders for appointments."""
        date_str = params.get("date", "tomorrow")
        return {
            "message": f"✅ تم جدولة إرسال تذكيرات المواعيد ليوم {date_str} عبر واتساب.",
            "status": "queued",
        }

    async def send_whatsapp_message(self, params: Dict) -> Dict:
        """Mock: Send a single WhatsApp message."""
        patient_name = params.get("patient_name")
        message_body = params.get("message")

        if not patient_name:
            return {"error": "missing_name", "message": "اسم المريض مطلوب"}

        return {
            "message": f'✅ تم إرسال الرسالة إلى {patient_name}:\n"{message_body}"',
            "status": "sent",
        }
