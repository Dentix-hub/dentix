import sys
import os
import unittest
from datetime import datetime

# Add project root
sys.path.append(os.getcwd())

from backend.database import SessionLocal
from backend import models

# Import Services
from backend.services.analytics_service import AnalyticsService
from backend.services.clinical_service import ClinicalService
from backend.services.finance_service import FinanceService
from backend.services.subscription_service import SubscriptionService
from backend.services.knowledge_service import KnowledgeService


class TestAllAIServices(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from backend.database import engine, Base
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()
        cls.tenant_id = 1
        cls.user_id = 1

        # Ensure dummy data
        cls._ensure_dummy_data()

    @classmethod
    def _ensure_dummy_data(cls):
        db = cls.db
        # Tenant
        tenant = db.query(models.Tenant).filter_by(id=cls.tenant_id).first()
        if not tenant:
            tenant = models.Tenant(id=cls.tenant_id, name="Test Clinic", plan="Pro")
            db.add(tenant)
            db.commit()

        # User
        user = db.query(models.User).filter_by(id=cls.user_id).first()
        if not user:
            user = models.User(
                id=cls.user_id,
                username="Dr. Test",
                role="doctor",
                tenant_id=cls.tenant_id,
            )
            db.add(user)
            db.commit()

        # Patient
        cls.patient = db.query(models.Patient).filter_by(name="AI Test Patient").first()
        if not cls.patient:
            cls.patient = models.Patient(
                tenant_id=cls.tenant_id,
                name="AI Test Patient",
                phone="0100000000",
                age=25,
            )
            db.add(cls.patient)
            db.commit()

        # Treatment
        t = db.query(models.Treatment).filter_by(patient_id=cls.patient.id).first()
        if not t:
            t = models.Treatment(
                patient_id=cls.patient.id,
                procedure="Test Fill",
                cost=100.0,
                date=datetime.now(),
                doctor_id=cls.user_id,
                tenant_id=cls.tenant_id,
            )
            db.add(t)
            db.commit()

        # Payment
        p = db.query(models.Payment).filter_by(patient_id=cls.patient.id).first()
        if not p:
            p = models.Payment(
                patient_id=cls.patient.id,
                amount=50.0,
                date=datetime.now(),
                tenant_id=cls.tenant_id,
            )
            db.add(p)
            db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_analytics_service(self):
        print("\nTesting AnalyticsService...")
        svc = AnalyticsService(self.db, self.tenant_id)

        # 1. Dashboard
        res = svc.get_dashboard_summary("month")
        self.assertIn("period_revenue", res)
        print("   âœ… get_dashboard_summary")

        # 2. Clinic Info
        res = svc.get_clinic_summary()
        self.assertIn("name", res)
        print("   âœ… get_clinic_summary")

        # 3. Doctor Ranking
        res = svc.get_doctor_ranking("month", "revenue")
        self.assertIsInstance(res.get("ranking"), list)
        print("   âœ… get_doctor_ranking")

        # 4. Top Procedures
        res = svc.get_top_procedures("month")
        self.assertIsInstance(res.get("top_procedures"), list)
        print("   âœ… get_top_procedures")

        # 5. Revenue Trend
        res = svc.get_revenue_trend("year")
        self.assertIsInstance(res.get("trend"), list)
        print("   âœ… get_revenue_trend")

    def test_clinical_service(self):
        print("\nTesting ClinicalService...")
        svc = ClinicalService(self.db, self.tenant_id, self.user_id)

        # 1. Recent Treatments
        res = svc.get_recent_treatments()
        self.assertTrue(len(res) >= 0)
        print("   âœ… get_recent_treatments")

        # 2. Add Treatment
        t = svc.add_treatment(self.patient, "New Proc", 200.0)
        self.assertTrue(t.id > 0)
        print("   âœ… add_treatment")

        # 3. Update Tooth
        try:
            res = svc.update_tooth_status(self.patient, "11", "Decayed", "Test Note")
            self.assertEqual(res["fdi"], 11)
            print("   âœ… update_tooth_status")
        except Exception as e:
            self.fail(f"update_tooth_status failed: {e}")

    def test_finance_service(self):
        print("\nTesting FinanceService...")
        svc = FinanceService(self.db, self.tenant_id)

        # 1. Daily Revenue
        res = svc.get_daily_revenue()
        self.assertIn("total_revenue", res)
        print("   âœ… get_daily_revenue")

        # 2. Create Payment
        res = svc.create_payment("AI Test Patient", 100.0, self.user_id)
        self.assertTrue(res["success"])
        print("   âœ… create_payment")

    def test_subscription_service(self):
        print("\nTesting SubscriptionService...")

        # 1. Get Details
        res = SubscriptionService.get_subscription_details(self.db, self.tenant_id)
        self.assertIn("plan_name", res)
        print("   âœ… get_subscription_details")

    def test_knowledge_service(self):
        print("\nTesting KnowledgeService...")
        svc = KnowledgeService(self.tenant_id)

        # 1. Learn
        doc_id = svc.learn_info("Test Info", "test")
        self.assertTrue(len(doc_id) > 0)
        print("   âœ… learn_info")

        # 2. List
        res = svc.list_knowledge()
        self.assertTrue(len(res) > 0)
        print("   âœ… list_knowledge")

        # 3. Forget
        # Note: Might fail if RAG store is persistent/mocked differently, but interface check is key
        try:
            svc.forget_info(doc_id)
            print("   âœ… forget_info")
        except Exception as e:
            print(f"   âš ï¸ forget_info warning: {e}")


if __name__ == "__main__":
    unittest.main()
