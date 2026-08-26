from backend import models


def test_ai_admin_stats_and_period_validation(client, super_admin_user, super_admin_headers):
    # 1. Invalid period returns 400
    res_invalid = client.get(
        "/api/v1/ai/admin/stats?period=invalid_period",
        headers=super_admin_headers,
    )
    assert res_invalid.status_code == 400
    assert "Invalid period" in res_invalid.json()["detail"]

    # 2. Valid periods (today, week, month) return 200 and null success_rate when 0 requests
    for p in ["today", "week", "month"]:
        res = client.get(
            f"/api/v1/ai/admin/stats?period={p}",
            headers=super_admin_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["period"] == p
        assert data["total_requests"] == 0
        assert data["success_rate"] is None


def test_ai_admin_logs_filtering_by_tool(client, super_admin_user, super_admin_headers, db_session):
    # Insert test AI logs
    log1 = models.AILog(
        trace_id="t1",
        tool="create_appointment",
        status="SUCCESS",
        username="dr_sami",
        input_text="Book appointment",
    )
    log2 = models.AILog(
        trace_id="t2",
        tool="summarize_treatment",
        status="FAILURE",
        username="dr_sami",
        input_text="Summarize treatment",
    )
    db_session.add_all([log1, log2])
    db_session.commit()

    # Filter by tool "create_appointment"
    res = client.get(
        "/api/v1/ai/admin/logs?tool=create_appointment",
        headers=super_admin_headers,
    )
    assert res.status_code == 200
    logs = res.json()
    assert len(logs) == 1
    assert logs[0]["tool"] == "create_appointment"

    # Filter by status false
    res_status = client.get(
        "/api/v1/ai/admin/logs?success_status=false",
        headers=super_admin_headers,
    )
    assert res_status.status_code == 200
    logs_status = res_status.json()
    assert len(logs_status) == 1
    assert logs_status[0]["status"] == "FAILURE"
