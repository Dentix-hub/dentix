import pytest
from datetime import datetime
from sqlalchemy import select

from backend import models
from backend.database import Base

# Import Services
from backend.services.analytics_service import AnalyticsService
from backend.services.clinical_service import ClinicalService
from backend.services.finance_service import FinanceService
from backend.services.subscription_service import SubscriptionService
from backend.services.knowledge_service import KnowledgeService


@pytest.fixture(scope="function")
async def seed_data(async_db_session, async_engine_fixture):
    # Ensure tables are created in the async test database
    async with async_engine_fixture.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure Tenant
    stmt_tenant = select(models.Tenant).where(models.Tenant.id == 1)
    res_tenant = await async_db_session.execute(stmt_tenant)
    tenant = res_tenant.scalars().first()
    if not tenant:
        tenant = models.Tenant(id=1, name="Test Clinic", plan="Pro")
        async_db_session.add(tenant)
        await async_db_session.commit()

    # Ensure User
    stmt_user = select(models.User).where(models.User.id == 1)
    res_user = await async_db_session.execute(stmt_user)
    user = res_user.scalars().first()
    if not user:
        user = models.User(
            id=1,
            username="Dr. Test",
            email="dr_test@test.com",
            hashed_password="pw",
            role="doctor",
            tenant_id=1,
        )
        async_db_session.add(user)
        await async_db_session.commit()

    # Ensure Patient
    stmt_patient = select(models.Patient).where(models.Patient.name == "AI Test Patient")
    res_patient = await async_db_session.execute(stmt_patient)
    patient = res_patient.scalars().first()
    if not patient:
        patient = models.Patient(
            tenant_id=1,
            name="AI Test Patient",
            phone="0100000000",
            age=25,
            medical_history="None",
            notes="",
        )
        async_db_session.add(patient)
        await async_db_session.commit()
        await async_db_session.refresh(patient)

    # Ensure Treatment
    stmt_t = select(models.Treatment).where(models.Treatment.patient_id == patient.id)
    res_t = await async_db_session.execute(stmt_t)
    t = res_t.scalars().first()
    if not t:
        t = models.Treatment(
            patient_id=patient.id,
            procedure="Test Fill",
            cost=100.0,
            date=datetime.now(),
            doctor_id=1,
            tenant_id=1,
        )
        async_db_session.add(t)
        await async_db_session.commit()

    # Ensure Payment
    stmt_p = select(models.Payment).where(models.Payment.patient_id == patient.id)
    res_p = await async_db_session.execute(stmt_p)
    p = res_p.scalars().first()
    if not p:
        p = models.Payment(
            patient_id=patient.id,
            amount=50.0,
            date=datetime.now(),
            tenant_id=1,
        )
        async_db_session.add(p)
        await async_db_session.commit()

    return patient


@pytest.mark.asyncio
async def test_analytics_service(async_db_session, seed_data):
    print("\nTesting AnalyticsService...")
    svc = AnalyticsService(async_db_session, tenant_id=1)

    # 1. Dashboard
    res = await svc.get_dashboard_summary("month")
    assert "period_revenue" in res

    # 2. Clinic Info
    res = await svc.get_clinic_summary()
    assert "name" in res

    # 3. Doctor Ranking
    res = await svc.get_doctor_ranking("month", "revenue")
    assert isinstance(res.get("ranking"), list)

    # 4. Top Procedures
    res = await svc.get_top_procedures("month")
    assert isinstance(res.get("top_procedures"), list)

    # 5. Revenue Trend
    res = await svc.get_revenue_trend("year")
    assert isinstance(res.get("trend"), list)


@pytest.mark.asyncio
async def test_clinical_service(async_db_session, seed_data):
    print("\nTesting ClinicalService...")
    svc = ClinicalService(async_db_session, tenant_id=1, user_id=1)

    # 1. Recent Treatments
    res = await svc.get_recent_treatments()
    assert len(res) >= 0

    # 2. Add Treatment
    t = await svc.add_treatment(seed_data, "New Proc", 200.0)
    assert t.id > 0

    # 3. Update Tooth
    res = await svc.update_tooth_status(seed_data, "11", "Decayed", "Test Note")
    assert res["fdi"] == 11


@pytest.mark.asyncio
async def test_finance_service(async_db_session, seed_data):
    print("\nTesting FinanceService...")
    svc = FinanceService(async_db_session, tenant_id=1)

    # 1. Daily Revenue
    res = await svc.get_daily_revenue()
    assert "total_revenue" in res

    # 2. Create Payment
    res = await svc.create_payment("AI Test Patient", 100.0, user_id=1)
    assert res["success"]


@pytest.mark.asyncio
async def test_subscription_service(async_db_session, seed_data):
    print("\nTesting SubscriptionService...")
    res = await SubscriptionService.get_subscription_details(async_db_session, tenant_id=1)
    assert "plan_name" in res


@pytest.mark.asyncio
async def test_knowledge_service(seed_data):
    print("\nTesting KnowledgeService...")
    svc = KnowledgeService(tenant_id=1)

    # 1. Learn
    doc_id = svc.learn_info("Test Info", "test")
    assert len(doc_id) > 0

    # 2. List
    res = svc.list_knowledge()
    assert len(res) > 0

    # 3. Forget
    success = svc.forget_info(doc_id)
    assert success is True
