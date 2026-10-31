"""Regression coverage for historical identifiers and clinic-calendar filters."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import select

from backend import models, schemas
from backend.auth import create_access_token
from backend.main import app
from backend.services.care_session_service import CareSessionService
from backend.services.clinical_workspace_service import FEATURE_FLAG_CLINICAL_NATIVE_WRITES
from backend.tests.services.test_care_session_workflow_unification_v2 import setup_env as setup_env
from backend.tests.test_care_session_delivery_integrity import care_pg as care_pg


@pytest.mark.asyncio
async def test_historical_identifiers_preserve_long_and_arabic_titles_on_postgresql(care_pg):
    db, tenants, users, patients, _, items = care_pg
    tenant, user, patient, item = tenants[0], users[0], patients[0], items[0]
    patient.assigned_doctor_id = user.id
    flag = (await db.execute(select(models.FeatureFlag).where(
        models.FeatureFlag.key == FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
    ))).scalar_one_or_none()
    if flag is None:
        db.add(models.FeatureFlag(key=FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
                                  is_global_enabled=True, rollout_percentage=100))
    else:
        flag.is_global_enabled = True
    await db.flush()
    prefix = "Detailed clinical assessment including restorative preparation and final occlusal adjustment"
    titles = [prefix + " before restoration", prefix + " after restoration",
              "تقييم الحالة وتجهيز السن للحشو", "تقييم الحالة وإنهاء الحشو", "X" * 255]
    entries = [{"title": title} for title in titles]
    titles.append("Template-defined stage")
    entries.append({"title": titles[-1], "step_code": "step_1", "logical_step_code": "step_1"})
    service = CareSessionService(db, tenant.id, user)
    payload = schemas.CareSessionCreate(
        is_historical=True, actual_visit_date=datetime.now(timezone.utc) - timedelta(days=3),
        work_item_ids=[item.id], historical_steps=entries,
    )
    visit = await service.start_session(patient.id, payload)
    assert [step.title for step in visit.steps] == titles
    codes = [step.logical_step_code for step in visit.steps]
    assert codes[-1] == "step_1"
    assert len(set(codes)) == len(titles)
    assert all(0 < len(step.step_code) <= 64 and 0 < len(step.logical_step_code) <= 64
               for step in visit.steps)
    repeated = await service.start_session(patient.id, payload)
    assert [step.logical_step_code for step in repeated.steps] == codes
    assert all(step.occurrence_number == 2 and step.is_repeat for step in repeated.steps)


@pytest.mark.parametrize("entry", [
    {"title": "x" * 256}, {"title": "   "},
    {"title": "Valid title", "step_code": "x" * 65},
    {"title": "Valid title", "logical_step_code": "x" * 65},
])
def test_invalid_historical_step_input_cannot_fall_back_to_unvalidated_dict(entry):
    with pytest.raises(ValidationError):
        schemas.CareSessionCreate(is_historical=True, historical_steps=[entry])


def test_legacy_explicit_step_code_remains_a_valid_label():
    payload = schemas.CareSessionCreate(is_historical=True, historical_steps=[{"step_code": "assessment"}])
    assert payload.historical_steps[0].title == "assessment"
    assert payload.historical_steps[0].step_code == "assessment"


@pytest.mark.asyncio
@pytest.mark.parametrize("zone,day", [
    ("Africa/Cairo", date(2026, 11, 30)), ("Africa/Cairo", date(2026, 8, 17)),
    ("America/New_York", date(2026, 3, 8)), ("America/New_York", date(2026, 11, 1)),
    ("Asia/Riyadh", date(2026, 11, 30)),
])
async def test_calendar_range_contains_exactly_the_clinic_local_day(async_db_session, setup_env, zone, day):
    env = setup_env
    env["tenant"].timezone = zone
    tz = ZoneInfo(zone)
    start = datetime.combine(day, time.min, tzinfo=tz)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz)
    instants = [start - timedelta(minutes=1), start, start + timedelta(minutes=30),
                end - timedelta(microseconds=1), end]
    requests = [models.NextVisitRequest(
        tenant_id=env["tenant"].id, patient_id=env["patient1"].id,
        reason=f"Synthetic calendar boundary {i}", status="requested",
        preferred_time_window_start=instant.astimezone(timezone.utc),
    ) for i, instant in enumerate(instants)]
    async_db_session.add_all(requests)
    await async_db_session.commit()
    service = CareSessionService(async_db_session, env["tenant"].id, env["doctor1"])
    result = await service.get_follow_up_dashboard(calendar_date_from=day, calendar_date_to=day)
    assert {row.id for row in result.items} == {row.id for row in requests[1:4]}

    token = create_access_token(data={"sub": env["doctor1"].username,
                                      "tenant_id": env["tenant"].id, "role": "doctor"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/next-visit-requests/dashboard",
                                    params={"calendar_date_from": day.isoformat(), "calendar_date_to": day.isoformat()},
                                    headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, response.text
    assert {row["id"] for row in response.json()["data"]["items"]} == {row.id for row in requests[1:4]}


@pytest.mark.asyncio
async def test_existing_datetime_filters_keep_exact_instant_semantics(async_db_session, setup_env):
    env = setup_env
    boundary = datetime(2026, 11, 30, tzinfo=timezone.utc)
    requests = [models.NextVisitRequest(
        tenant_id=env["tenant"].id, patient_id=env["patient1"].id,
        reason=f"Synthetic instant {i}", status="requested", preferred_time_window_start=instant,
    ) for i, instant in enumerate([boundary, boundary + timedelta(microseconds=1)])]
    async_db_session.add_all(requests)
    await async_db_session.commit()
    service = CareSessionService(async_db_session, env["tenant"].id, env["doctor1"])
    result = await service.get_follow_up_dashboard(date_from=boundary, date_to=boundary)
    assert [row.id for row in result.items] == [requests[0].id]


@pytest.mark.asyncio
@pytest.mark.parametrize("filters", [
    {"calendar_date_from": date(2026, 12, 1), "calendar_date_to": date(2026, 11, 30)},
    {"calendar_date_to": date(2026, 11, 30), "date_from": datetime(2026, 11, 1, tzinfo=timezone.utc)},
])
async def test_calendar_filters_reject_inverted_or_mixed_ranges(async_db_session, setup_env, filters):
    env = setup_env
    service = CareSessionService(async_db_session, env["tenant"].id, env["doctor1"])
    with pytest.raises(HTTPException) as error:
        await service.get_follow_up_dashboard(**filters)
    assert error.value.status_code == 422
