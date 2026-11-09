"""Causal policy markers: billing changes must invalidate older administrative undo."""

from datetime import timezone


def tenant_policy_marker(tenant):
    end = tenant.subscription_end_date
    if end is not None and end.tzinfo is not None:
        end = end.astimezone(timezone.utc).replace(tzinfo=None)
    return {
        "_policy_revision": tenant.policy_revision,
        "_contract_end": end.isoformat() if end else None,
        "_future_plan_id": tenant.future_plan_id,
        "_scheduled_plan_id": tenant.scheduled_downgrade_plan_id,
    }
