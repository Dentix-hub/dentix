"""
Admin System Module Tests.
Tests for system stats, audit logs, system logs, and health endpoints.
"""


def test_get_system_stats(client, super_admin_headers):
    """Test fetching admin dashboard statistics."""
    response = client.get("/api/v1/admin/stats", headers=super_admin_headers)
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    data = res["data"]
    assert "total_tenants" in data
    assert "active_tenants" in data
    assert "expired_tenants" in data
    assert "total_revenue" in data
    assert "plan_distribution" in data
    assert isinstance(data["total_tenants"], int)
    assert isinstance(data["total_revenue"], (int, float))


def test_get_audit_logs(client, super_admin_headers):
    """Test fetching audit logs."""
    response = client.get("/api/v1/admin/audit-logs", headers=super_admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_system_logs(client, super_admin_headers):
    """Test fetching system error logs."""
    response = client.get("/api/v1/admin/system/logs", headers=super_admin_headers)
    assert response.status_code == 200
    res = response.json()
    assert isinstance(res, list) or isinstance(res.get("data"), list)


def test_health_check(client):
    """Test public health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


def test_liveness_probe(client):
    """Test Kubernetes liveness probe."""
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_stats_requires_super_admin(client, admin_headers):
    """Test that stats endpoint rejects non-super-admin."""
    response = client.get("/api/v1/admin/stats", headers=admin_headers)
    assert response.status_code == 403


def test_audit_logs_requires_super_admin(client, admin_headers):
    """Test that audit logs endpoint rejects non-super-admin."""
    response = client.get("/api/v1/admin/audit-logs", headers=admin_headers)
    assert response.status_code == 403
