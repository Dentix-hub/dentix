def test_security_ip_block_validation(client, super_admin_user, super_admin_headers):
    # 1. Reject invalid IP formats
    res_invalid_1 = client.post(
        "/api/v1/admin/security/ip-block",
        headers=super_admin_headers,
        json={"ip_address": "999.999.999.999", "reason": "Test Invalid"},
    )
    assert res_invalid_1.status_code == 400
    assert "غير صالح" in res_invalid_1.json()["detail"] or "Invalid IP" in res_invalid_1.json()["detail"]

    res_invalid_2 = client.post(
        "/api/v1/admin/security/ip-block",
        headers=super_admin_headers,
        json={"ip_address": "not_an_ip", "reason": "Test Invalid"},
    )
    assert res_invalid_2.status_code == 400

    # 2. Accept valid IPv4
    res_v4 = client.post(
        "/api/v1/admin/security/ip-block",
        headers=super_admin_headers,
        json={"ip_address": "198.51.100.42", "reason": "Brute force attack"},
    )
    assert res_v4.status_code == 200, res_v4.text

    # 3. Accept valid IPv6
    res_v6 = client.post(
        "/api/v1/admin/security/ip-block",
        headers=super_admin_headers,
        json={"ip_address": "2001:db8:85a3::8a2e:370:7334", "reason": "Suspicious IPv6 traffic"},
    )
    assert res_v6.status_code == 200, res_v6.text

    # 4. Successfully unblock
    res_unblock = client.delete(
        "/api/v1/admin/security/ip-block/198.51.100.42",
        headers=super_admin_headers,
    )
    assert res_unblock.status_code == 200

    # 5. Unblock non-existent IP returns 404
    res_unblock_404 = client.delete(
        "/api/v1/admin/security/ip-block/198.51.100.42",
        headers=super_admin_headers,
    )
    assert res_unblock_404.status_code == 404
