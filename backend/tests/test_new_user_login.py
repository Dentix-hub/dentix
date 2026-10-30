"""Tests for new-user registration and immediate login (PR-A: fix/new-user-login)."""

import pytest

from backend import models
from backend.auth import get_password_hash
from scripts.report_unloginable_usernames import (
    find_unloginable_usernames,
    format_report,
)

STRONG_PASSWORD = "Valid#Pass89!XyZ"


@pytest.mark.parametrize(
    "case_id,typed_username,expected_stored",
    [
        ("a_trailing_space", "doc_space ", "doc_space"),
        ("b_arabic_alef_hamza", "أحمد", "أحمد"),
        ("c_mixed_case", "DrMixedCase", "DrMixedCase"),
        ("d1_teh_marbuta", "فاطمة", "فاطمة"),
        ("d2_alef_maksura", "مصطفى", "مصطفى"),
    ],
)
def test_admin_registered_user_can_login_with_typed_username(
    client, admin_headers, case_id, typed_username, expected_stored
):
    """Step 1 & 7: A user created via POST /users/register can immediately log in."""
    reg_res = client.post(
        "/api/v1/users/register",
        json={"username": typed_username, "password": STRONG_PASSWORD},
        headers=admin_headers,
    )
    assert reg_res.status_code == 200, f"[{case_id}] register failed: {reg_res.text}"
    created = reg_res.json()["data"]
    assert created["username"] == expected_stored

    login_res = client.post(
        "/api/v1/auth/token",
        data={"username": typed_username, "password": STRONG_PASSWORD},
    )
    assert (
        login_res.status_code == 200
    ), f"[{case_id}] login failed ({login_res.status_code}): {login_res.text}"
    assert login_res.json()["username"] == expected_stored


def test_login_case_insensitive_and_arabic_variant_equivalent(client, admin_headers):
    """Step 7: Login remains case-insensitive and matches across Arabic variants."""
    reg_res = client.post(
        "/api/v1/users/register",
        json={"username": "Dr_أحمد_فاطمة_مصطفى", "password": STRONG_PASSWORD},
        headers=admin_headers,
    )
    assert reg_res.status_code == 200
    assert reg_res.json()["data"]["username"] == "Dr_أحمد_فاطمة_مصطفى"

    for candidate in (
        "dr_أحمد_فاطمة_مصطفى",
        "DR_احمد_فاطمه_مصطفي",
        "  dr_إحمد_فاطمة_مصطفى  ",
    ):
        login_res = client.post(
            "/api/v1/auth/token",
            data={"username": candidate, "password": STRONG_PASSWORD},
        )
        assert login_res.status_code == 200, f"Failed for {candidate!r}: {login_res.text}"
        assert login_res.json()["username"] == "Dr_أحمد_فاطمة_مصطفى"


def test_duplicate_detection_across_arabic_variants_and_case(client, admin_headers):
    """Step 2 & 7: Duplicate detection catches Arabic variants, case, and outer spaces."""
    first = client.post(
        "/api/v1/users/register",
        json={"username": "أحمد_عيادة", "password": STRONG_PASSWORD},
        headers=admin_headers,
    )
    assert first.status_code == 200

    for duplicate in ("احمد_عياده", "إحمد_عيادة", "  أحمد_عياده  "):
        dup_res = client.post(
            "/api/v1/users/register",
            json={"username": duplicate, "password": STRONG_PASSWORD},
            headers=admin_headers,
        )
        assert dup_res.status_code == 400, f"Expected 400 for duplicate {duplicate!r}"
        assert "already registered" in dup_res.json()["detail"].lower()


@pytest.mark.parametrize(
    "invalid_username,expected_arabic_substring",
    [
        ("", "فارغ"),
        ("   ", "فارغ"),
        ("dr ahmed", "مسافات"),
        ("أحمد\tعلي", "مسافات"),
    ],
)
def test_reject_empty_or_internal_whitespace_usernames_on_create_and_update(
    client, admin_headers, test_user, invalid_username, expected_arabic_substring
):
    """Step 2: Reject usernames that are empty after trimming or contain internal whitespace."""
    reg_res = client.post(
        "/api/v1/users/register",
        json={"username": invalid_username, "password": STRONG_PASSWORD},
        headers=admin_headers,
    )
    assert reg_res.status_code == 400
    assert expected_arabic_substring in reg_res.json()["detail"]

    upd_res = client.put(
        f"/api/v1/users/{test_user.id}",
        json={"username": invalid_username},
        headers=admin_headers,
    )
    assert upd_res.status_code == 400
    assert expected_arabic_substring in upd_res.json()["detail"]


def test_update_user_trims_username_and_detects_arabic_duplicates(
    client, admin_headers, test_user
):
    """Step 2: update_user trims stored username, preserves display form, and blocks duplicates."""
    other = client.post(
        "/api/v1/users/register",
        json={"username": "دكتورة_سارة", "password": STRONG_PASSWORD},
        headers=admin_headers,
    )
    assert other.status_code == 200

    dup_upd = client.put(
        f"/api/v1/users/{test_user.id}",
        json={"username": "دكتوره_ساره"},
        headers=admin_headers,
    )
    assert dup_upd.status_code == 400

    ok_upd = client.put(
        f"/api/v1/users/{test_user.id}",
        json={"username": "  أحمد_الجديد  ", "password": STRONG_PASSWORD},
        headers=admin_headers,
    )
    assert ok_upd.status_code == 200
    assert ok_upd.json()["data"]["username"] == "أحمد_الجديد"

    login_res = client.post(
        "/api/v1/auth/token",
        data={"username": "أحمد_الجديد", "password": STRONG_PASSWORD},
    )
    assert login_res.status_code == 200
    assert login_res.json()["username"] == "أحمد_الجديد"


def test_json_body_and_legacy_query_param_register_both_work(client, admin_headers):
    """Step 5 & 7: JSON body (with full_name & patient_visibility_mode) and query fallback work."""
    json_res = client.post(
        "/api/v1/users/register",
        json={
            "username": "dr_json_body",
            "password": STRONG_PASSWORD,
            "full_name": "د. أحمد كامل",
            "role": "doctor",
            "permissions": '["view_patients","view_calendar"]',
            "patient_visibility_mode": "appointments_only",
        },
        headers=admin_headers,
    )
    assert json_res.status_code == 200
    json_data = json_res.json()["data"]
    assert json_data["username"] == "dr_json_body"
    assert json_data["full_name"] == "د. أحمد كامل"
    assert json_data["patient_visibility_mode"] == "appointments_only"

    legacy_res = client.post(
        "/api/v1/users/register",
        params={
            "username": "dr_legacy_query ",
            "password": STRONG_PASSWORD,
            "full_name": "Legacy Doc",
            "role": "receptionist",
            "permissions": '["view_patients"]',
        },
        headers=admin_headers,
    )
    assert legacy_res.status_code == 200
    legacy_data = legacy_res.json()["data"]
    assert legacy_data["username"] == "dr_legacy_query"
    assert legacy_data["full_name"] == "Legacy Doc"
    assert legacy_data["role"] == "receptionist"

    login_res = client.post(
        "/api/v1/auth/token",
        data={"username": "dr_legacy_query", "password": STRONG_PASSWORD},
    )
    assert login_res.status_code == 200


@pytest.mark.asyncio
async def test_existing_unnormalized_rows_can_login_and_report_script_counts_only(
    client, db_session, async_db_session, test_tenant
):
    """Step 3: Pre-existing DB rows with trailing spaces or أ/ة/ى can log in and are reported."""
    raw_u1 = models.User(
        username="legacy_space ",
        full_name="Sensitive Full Name PHI",
        email="sensitive_phi@example.com",
        hashed_password=get_password_hash(STRONG_PASSWORD),
        role="doctor",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    raw_u2 = models.User(
        username="أروى_ة",
        full_name="Another Secret Name",
        email="secret2@example.com",
        hashed_password=get_password_hash(STRONG_PASSWORD),
        role="doctor",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add_all([raw_u1, raw_u2])
    db_session.commit()
    db_session.refresh(raw_u1)
    db_session.refresh(raw_u2)

    # Both pre-existing rows can now log in without rewriting DB data
    for login_name in ("legacy_space", "legacy_space ", "أروى_ة", "اروي_ه"):
        res = client.post(
            "/api/v1/auth/token",
            data={"username": login_name, "password": STRONG_PASSWORD},
        )
        assert res.status_code == 200, f"Failed login for {login_name!r}: {res.text}"

    summary = await find_unloginable_usernames(async_db_session)
    assert summary["matched_count"] >= 1
    assert (test_tenant.id, raw_u2.id, repr("أروى_ة")) in summary["rows"]
    assert (test_tenant.id, raw_u1.id, repr("legacy_space ")) in summary[
        "whitespace_rows"
    ]

    report_text = format_report(summary)
    assert "Sensitive Full Name PHI" not in report_text
    assert "sensitive_phi@example.com" not in report_text
    assert "أروى_ة" not in report_text
    assert f"tenant_id={test_tenant.id}" in report_text
