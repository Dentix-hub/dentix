"""The patient UI must discover the exact clinical API rollout decision."""

from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from backend import models, schemas
from backend.auth import create_access_token
from backend.main import app
from backend.services.care_session_service import CareSessionService
from backend.tests.services.test_care_session_workflow_unification_v2 import (
    setup_env as setup_env,
    set_native_writes_flag,
    seed_visit,
)


@pytest.mark.asyncio
async def test_feature_discovery_matches_native_api_in_both_directions(
    async_db_session, setup_env
):
    env = setup_env
    user, tenant = env["doctor1"], env["tenant"]
    await async_db_session.execute(
        delete(models.TenantFeature).where(
            models.TenantFeature.tenant_id == tenant.id,
            models.TenantFeature.feature_key == "clinical_vnext_native_writes",
        )
    )
    await async_db_session.commit()
    token = create_access_token(
        data={"sub": user.username, "tenant_id": tenant.id, "role": user.role}
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(
            "/api/v1/settings/features", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, response.text
        assert "clinical_vnext_native_writes" in response.json()["data"]["features"]
        # Explicit tenant opt-out still wins over the global rollout.
        await set_native_writes_flag(async_db_session, tenant.id, False)
        response = await client.get(
            "/api/v1/settings/features", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert "clinical_vnext_native_writes" not in response.json()["data"]["features"]


@pytest.mark.asyncio
async def test_multiple_canal_sizes_and_tapers_survive_history_resume_and_amendment(
    async_db_session, setup_env
):
    env = setup_env
    _, item, _ = await seed_visit(async_db_session, env, status="completed")
    service = CareSessionService(async_db_session, env["tenant"].id, env["doctor1"])
    visit = await service.start_session(
        env["patient1"].id,
        schemas.CareSessionCreate(
            is_historical=True,
            actual_visit_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
            work_item_ids=[item.id],
            historical_observations=[
                {
                    "work_item_id": item.id,
                    "tooth_key": "46",
                    "canal_id": canal,
                    "observation_code": "working_length",
                    "structured_value": {
                        "length_mm": length,
                        "maf": size,
                        "taper": taper,
                        "canal_id": canal,
                    },
                }
                for canal, length, size, taper in [
                    ("MB", 20, "#25", 0.04),
                    ("ML", 21, "#30", 0.06),
                ]
            ],
        ),
    )
    assert {
        (o.canal_id, o.structured_value["maf"], o.structured_value["taper"])
        for o in visit.observations
    } == {("MB", "#25", 0.04), ("ML", "#30", 0.06)}
    summary = service.generate_session_summary(visit)
    assert "taper 0.04" in summary and "taper 0.06" in summary
    following = await service.start_session(
        env["patient1"].id,
        schemas.CareSessionCreate(
            resume_work_item_ids=[item.id], resume_from_session_id=visit.id
        ),
    )
    assert {
        (o.canal_id, o.structured_value["taper"]) for o in following.observations
    } == {("MB", 0.04), ("ML", 0.06)}
    original = next(o for o in visit.observations if o.canal_id == "MB")
    await service.amend_observation(
        env["patient1"].id,
        original.id,
        schemas.CareObservationAmend(
            reason="Correct file specification", structured_value={"taper": 0.06}
        ),
    )
    assert original.structured_value["taper"] == 0.04
    refreshed = await service.get_session(env["patient1"].id, following.id)
    assert (
        next(o for o in refreshed.observations if o.canal_id == "MB").structured_value[
            "taper"
        ]
        == 0.06
    )
