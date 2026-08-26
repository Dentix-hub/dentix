def test_super_admin_profile_update_policy(client, super_admin_user, super_admin_headers):
    # 1. Reject empty update
    res_empty = client.put(
        "/api/v1/admin/system/profile",
        headers=super_admin_headers,
        json={"username": "", "email": "", "password": ""},
    )
    assert res_empty.status_code == 400
    assert "لم يتم تقديم أي بيانات" in res_empty.json()["detail"]

    # 2. Reject weak password (< 8 chars)
    res_weak_pwd = client.put(
        "/api/v1/admin/system/profile",
        headers=super_admin_headers,
        json={"password": "short"},
    )
    assert res_weak_pwd.status_code == 400
    assert "8 أحرف" in res_weak_pwd.json()["detail"]

    # 3. Successful update of username, email and strong password
    res_success = client.put(
        "/api/v1/admin/system/profile",
        headers=super_admin_headers,
        json={
            "username": "super_admin_updated",
            "email": "updated_super@dentix.test",
            "password": "StrongPassword9988!@#",
        },
    )
    assert res_success.status_code == 200, res_success.text
    data = res_success.json()["data"]
    assert data["username"] == "super_admin_updated"
    assert data["email"] == "updated_super@dentix.test"
