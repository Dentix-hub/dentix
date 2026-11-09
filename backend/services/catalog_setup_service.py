"""Reviewed, atomic catalog initialization; never reprices or reassigns a legacy contract."""

import hashlib
import json
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from backend import models, schemas
from backend.services.subscription_service import SubscriptionService

TRIAL_KEYS = ("system_trial_plan_name", "system_trial_duration_days")


def _features(raw):
    try:
        value = json.loads(raw)
        if isinstance(value, list) and all(isinstance(key, str) for key in value):
            return {key: True for key in value}
        if isinstance(value, dict) and all(
            isinstance(flag, bool) for flag in value.values()
        ):
            return {key: True for key, flag in value.items() if flag is True}
        return raw
    except (ValueError, TypeError):
        return raw


async def preview_catalog_setup(db):
    rows = list(
        (
            await db.execute(
                select(models.SubscriptionPlan)
                .order_by(models.SubscriptionPlan.id)
                .execution_options(populate_existing=True)
            )
        ).scalars()
    )
    settings = {
        r.key: r.value
        for r in (
            await db.execute(
                select(models.SystemSetting)
                .where(models.SystemSetting.key.in_(TRIAL_KEYS))
                .execution_options(populate_existing=True)
            )
        ).scalars()
    }
    existing = {p.name: p for p in rows}
    template = SubscriptionService.get_launch_catalog_template()
    conflicts = []
    for spec in template:
        row = existing.get(spec["name"])
        if row is None:
            continue
        different = [
            key
            for key, value in spec.items()
            if (
                _features(getattr(row, key)) != _features(value)
                if key == "features"
                else getattr(row, key) != value
            )
        ]
        if not row.is_active:
            different.append("is_active")
        if row.ai_features not in (None, ""):
            different.append("ai_features")
        if different:
            conflicts.append({"plan_id": row.id, "name": row.name, "fields": different})
    for row in rows:
        if row.is_default and row.name != "professional":
            conflicts.append(
                {"plan_id": row.id, "name": row.name, "fields": ["existing_default"]}
            )
    preserved = [
        {c.key: getattr(row, c.key) for c in models.SubscriptionPlan.__table__.columns}
        for row in rows
    ]
    state = {"plans": preserved, "trial": settings, "approved_template": template}
    digest = hashlib.sha256(
        json.dumps(state, sort_keys=True, default=str).encode()
    ).hexdigest()
    return {
        "snapshot": digest,
        "create_plans": [s for s in template if s["name"] not in existing],
        "preserved_plans": preserved,
        "conflicts": conflicts,
        "current_trial": settings,
        "proposed_trial": {"plan": "professional", "days": 14, "card_required": False},
        "already_configured": not any(s["name"] not in existing for s in template)
        and settings == {TRIAL_KEYS[0]: "professional", TRIAL_KEYS[1]: "14"},
        "existing_subscriptions_changed": 0,
    }


async def apply_catalog_setup(db, request, actor):
    try:
        if db.get_bind().dialect.name == "postgresql":
            await db.execute(text("SELECT pg_advisory_xact_lock(18467301)"))
        await db.execute(
            select(models.SubscriptionPlan.id)
            .order_by(models.SubscriptionPlan.id)
            .with_for_update()
        )
        await db.execute(
            select(models.SystemSetting.key)
            .where(models.SystemSetting.key.in_(TRIAL_KEYS))
            .order_by(models.SystemSetting.key)
            .with_for_update()
        )
        preview = await preview_catalog_setup(db)
        if request.expected_snapshot != preview["snapshot"]:
            raise HTTPException(
                409, "Catalog or trial policy changed; refresh the setup preview"
            )
        if preview["conflicts"]:
            raise HTTPException(
                409,
                "Existing named plans/defaults require explicit review; no values were overwritten",
            )
        if preview["already_configured"]:
            raise HTTPException(409, "Catalog setup is already configured")
        for spec in preview["create_plans"]:
            db.add(models.SubscriptionPlan(**spec, is_active=True))
        await db.flush()
        current = await SubscriptionService.get_trial_policy(db)
        await SubscriptionService.update_trial_policy(
            db,
            schemas.TrialPolicyUpdateRequest(
                trial_plan_name="professional",
                trial_duration_days=14,
                expected_trial_plan_id=current.trial_plan_id,
                expected_trial_duration_days=current.trial_duration_days,
                reason=request.reason,
            ),
            actor,
            commit=False,
        )
        created = [spec["name"] for spec in preview["create_plans"]]
        db.add(
            models.AuditLog(
                action="COMMERCIAL_CATALOG_SETUP",
                entity_type="SubscriptionPlan",
                performed_by_id=actor.id,
                performed_by_username=actor.username,
                old_value=json.dumps(
                    {
                        "plan_ids": [p["id"] for p in preview["preserved_plans"]],
                        "trial": preview["current_trial"],
                    }
                ),
                new_value=json.dumps(
                    {"created_plans": created, "trial": preview["proposed_trial"]}
                ),
                details=request.reason,
            )
        )
        await db.commit()
        return {
            "created_plans": created,
            "preserved_plan_ids": [p["id"] for p in preview["preserved_plans"]],
            "trial_policy": preview["proposed_trial"],
            "existing_subscriptions_changed": 0,
        }
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            409, "Concurrent catalog change; refresh the preview"
        ) from exc
    except Exception:
        await db.rollback()
        raise
