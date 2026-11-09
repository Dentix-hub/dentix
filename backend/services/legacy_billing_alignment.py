"""Apply an explicit operator-approved legacy term manifest before serving traffic.

Only global catalog metadata is touched; tenant periods and receipts are immutable.
The approval is installed separately on the old schema, before production promotion.
"""

from datetime import datetime, timezone
import hashlib
import json
from uuid import UUID

from sqlalchemy import insert, select, text, update

from backend import models

APPROVAL_KEY = "commercial_legacy_day_terms_v1"
APPLIED_KEY = "commercial_legacy_day_terms_v1_applied"
INSTALLATION_KEY = "commercial_billing_installation_id"


def align_legacy_billing_terms(engine, *, required=False):
    settings = models.SystemSetting.__table__
    plans = models.SubscriptionPlan.__table__
    audits = models.AuditLog.__table__
    with engine.begin() as conn:
        approval = conn.execute(
            select(settings.c.value)
            .where(settings.c.key == APPROVAL_KEY)
            .with_for_update()
        ).scalar_one_or_none()
        if approval is None:
            existing = conn.execute(
                select(plans.c.name, plans.c.billing_cycle_unit, plans.c.duration_days)
            ).all()
            launch_only = all(
                row.name in {"essential", "professional", "business"}
                and row.billing_cycle_unit == "month"
                and row.duration_days == 30
                for row in existing
            )
            if required and not launch_only:
                raise ValueError(
                    "Legacy billing approval is required before serving this catalog"
                )
            return False
        payload = json.loads(approval)
        if not isinstance(payload, dict) or payload.get("version") != 1:
            raise ValueError("Invalid legacy billing approval")
        installation = conn.execute(
            select(settings.c.value)
            .where(settings.c.key == INSTALLATION_KEY)
            .with_for_update()
        ).scalar_one_or_none()
        if (
            not installation
            or str(UUID(installation)) != installation
            or payload.get("installation_id") != installation
        ):
            raise ValueError("Billing approval belongs to a different installation")
        legacy = payload.get("legacy")
        monthly = payload.get("monthly")
        if (
            not isinstance(legacy, list)
            or not legacy
            or not isinstance(monthly, list)
            or len(monthly) != 3
        ):
            raise ValueError(
                "Approval must identify legacy contracts and the three launch plans"
            )
        approved = legacy + monthly
        ids = []
        for item in approved:
            if (
                not isinstance(item, dict)
                or set(item) != {"id", "name", "duration_days"}
                or type(item["id"]) is not int
                or item["id"] <= 0
                or not isinstance(item["name"], str)
                or not item["name"]
                or type(item["duration_days"]) is not int
                or item["duration_days"] <= 0
            ):
                raise ValueError("Invalid approved plan identity")
            ids.append(item["id"])
        if len(set(ids)) != len(ids) or {p["name"] for p in monthly} != {
            "essential",
            "professional",
            "business",
        }:
            raise ValueError("Duplicate or invalid launch plan identities")
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        marker = conn.execute(
            select(settings.c.value)
            .where(settings.c.key == APPLIED_KEY)
            .with_for_update()
        ).scalar_one_or_none()
        if marker is not None:
            if marker != digest:
                raise ValueError("Completed billing approval cannot be replaced")
            return (
                False  # Later explicit administrator term edits remain authoritative.
            )
        if conn.dialect.name == "postgresql":
            # Serialize catalog creation as well as edits while verifying the full cohort.
            table_name = conn.dialect.identifier_preparer.format_table(plans)
            schema = (
                conn.get_execution_options().get("schema_translate_map", {}).get(None)
            )
            if schema:
                table_name = (
                    conn.dialect.identifier_preparer.quote_schema(schema)
                    + "."
                    + table_name
                )
            conn.execute(text(f"LOCK TABLE {table_name} IN SHARE ROW EXCLUSIVE MODE"))
        rows = {
            row.id: row
            for row in conn.execute(
                select(plans).order_by(plans.c.id).with_for_update()
            )
        }
        if set(rows) != set(ids):
            raise ValueError("Approved catalog cohort is incomplete or drifted")
        for item in approved:
            row = rows.get(item["id"])
            if (
                row is None
                or row.name != item["name"]
                or row.duration_days != item["duration_days"]
            ):
                raise ValueError("Approved billing catalog identity drifted")
            allowed = {"day", "month"} if item in legacy else {"month"}
            if row.billing_cycle_unit not in allowed:
                raise ValueError("Approved billing unit drifted")
        before = []
        for item in legacy:
            row = rows[item["id"]]
            before.append(
                dict(
                    id=row.id,
                    billing_cycle_unit=row.billing_cycle_unit,
                    policy_revision=row.policy_revision,
                )
            )
            if row.billing_cycle_unit != "day":
                conn.execute(
                    update(plans)
                    .where(plans.c.id == row.id)
                    .values(
                        billing_cycle_unit="day",
                        policy_revision=row.policy_revision + 1,
                    )
                )
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        conn.execute(
            insert(audits).values(
                action="LEGACY_BILLING_TERMS_ALIGNED",
                entity_type="SubscriptionPlan",
                performed_by_username="release-preflight",
                old_value=json.dumps(before),
                new_value=json.dumps({"approval_sha256": digest, "legacy": legacy}),
                details="Owner approved retaining legacy day durations; launch tiers remain calendar-monthly",
                created_at=now,
            )
        )
        conn.execute(
            insert(settings).values(
                key=APPLIED_KEY,
                value=digest,
                description="Completed owner-approved legacy billing alignment",
                updated_at=now,
            )
        )
        return True
