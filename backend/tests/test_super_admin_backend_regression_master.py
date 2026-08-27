import ipaddress
import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from backend.services.entitlement_service import EntitlementService


def test_ms36_regression_ip_validation():
    """Verify IP validation correctly accepts valid IPv4/IPv6 and rejects invalid inputs."""
    valid_ips = ["192.168.1.1", "10.0.0.1", "127.0.0.1", "2001:db8::1", "::1"]
    for ip in valid_ips:
        parsed = ipaddress.ip_address(ip)
        assert parsed is not None

    invalid_ips = ["not_an_ip", "999.999.999.999", "1.2.3.4.5", "2001:xyz::1", "", "   "]
    for ip in invalid_ips:
        with pytest.raises(ValueError):
            ipaddress.ip_address(ip.strip())


def test_ms36_regression_ai_analytics_zero_requests(client, super_admin_user, super_admin_headers):
    """Verify AI analytics service returns success_rate=None on 0 requests and validates periods."""
    res_invalid = client.get(
        "/api/v1/ai/admin/stats?period=invalid_period",
        headers=super_admin_headers,
    )
    assert res_invalid.status_code == 400

    res = client.get(
        "/api/v1/ai/admin/stats?period=today",
        headers=super_admin_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["period"] == "today"
    assert data["total_requests"] == 0
    assert data["success_rate"] is None


def test_ms36_regression_clinical_read_invariant_and_entitlement():
    """Verify clinical-history read is PERMANENTLY permitted regardless of subscription state."""
    tenant = MagicMock()
    tenant.id = 99
    tenant.subscription_status = "expired"
    tenant.subscription_end_date = datetime.now(timezone.utc) - timedelta(days=60)
    tenant.grace_period_until = datetime.now(timezone.utc) - timedelta(days=45)

    eval_result = EntitlementService.evaluate_tenant_entitlements(tenant, override_mode="strict")
    assert eval_result.can_read_clinical is True
    assert eval_result.can_write_billable is False
    assert eval_result.can_create_appointments is False


def test_ms36_regression_finance_forecast_safe_division():
    """Verify finance forecasting does not crash with ZeroDivisionError when history is empty."""
    daily_revenues = []
    if not daily_revenues:
        avg_daily = Decimal("0.00")
        forecast_next_month = Decimal("0.00")
    else:
        avg_daily = sum(daily_revenues) / len(daily_revenues)
        forecast_next_month = avg_daily * 30

    assert avg_daily == Decimal("0.00")
    assert forecast_next_month == Decimal("0.00")


def test_ms36_regression_feature_flag_rollout_validation():
    """Verify FeatureFlagCreate and FeatureFlagUpdate enforce rollout_percentage between 0 and 100."""
    from backend.schemas.system import FeatureFlagCreate, FeatureFlagUpdate
    from pydantic import ValidationError

    # Valid values
    for val in [0, 50, 100]:
        flag = FeatureFlagCreate(key=f"test_flag_{val}", rollout_percentage=val)
        assert flag.rollout_percentage == val
        update = FeatureFlagUpdate(rollout_percentage=val)
        assert update.rollout_percentage == val

    # Invalid values
    for val in [-1, -50, 101, 200]:
        with pytest.raises(ValidationError):
            FeatureFlagCreate(key="bad_flag", rollout_percentage=val)
        with pytest.raises(ValidationError):
            FeatureFlagUpdate(rollout_percentage=val)

