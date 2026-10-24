"""Public and authenticated user DTO projection contracts for Iteration 21."""

from __future__ import annotations

import math

import pytest
import requests

from iter21_support import TIMEOUT, create_user, owned_mysql_connection, require_status, url


PUBLIC_USER_FIELDS = {"userid", "username", "nickname", "avatar"}
PRIVATE_USER_FIELDS = PUBLIC_USER_FIELDS | {"qq", "role", "credit"}


def _db_user_snapshot(user_id: int) -> dict:
    connection = owned_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT userid, username, nickname, avatar, qq, role, credit "
                "FROM users WHERE userid = %s",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None:
                pytest.fail("run-owned database did not contain the isolated test user")
        connection.commit()
    finally:
        connection.close()

    return {
        "userid": int(row[0]),
        "username": row[1],
        "nickname": row[2],
        "avatar": row[3],
        "qq": row[4],
        "role": row[5],
        "credit": int(row[6]),
    }


def _db_password_hashes(user_ids: tuple[int, ...]) -> list[str]:
    placeholders = ", ".join(["%s"] * len(user_ids))
    connection = owned_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT userid, password FROM users WHERE userid IN ({placeholders})",
                user_ids,
            )
            rows = cursor.fetchall()
            hashes = {int(row[0]): row[1] for row in rows}
        connection.commit()
    finally:
        connection.close()
    if set(hashes) != set(user_ids):
        pytest.fail("run-owned database did not contain all isolated test users")
    return [hashes[user_id] for user_id in user_ids]


def _set_test_user_credit(user_id: int, credit: int) -> None:
    connection = owned_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE users SET credit = %s WHERE userid = %s", (credit, user_id))
            if cursor.rowcount != 1:
                pytest.fail("could not update the isolated user's test credit")
        connection.commit()
    finally:
        connection.close()


def _promote_test_user_to_admin(user_id: int) -> None:
    """Promote only this test's dedicated account in the run-owned schema."""
    connection = owned_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE users SET role = 'admin' WHERE userid = %s", (user_id,))
            if cursor.rowcount != 1:
                pytest.fail("could not promote the isolated admin test account")
        connection.commit()
    finally:
        connection.close()


def _assert_projection_matches(payload, expected: dict, fields: set[str]) -> None:
    if not isinstance(payload, dict):
        pytest.fail("user response did not contain an object projection")
    if set(payload) != fields:
        pytest.fail("user response contained a different field set than its DTO contract")
    for field in fields:
        if payload.get(field) != expected.get(field):
            pytest.fail(f"user response field {field} differed from the independent database row")


def _assert_no_password_material(response: requests.Response, secrets: list[str]) -> None:
    body = response.content
    if any(secret and secret.encode("utf-8") in body for secret in secrets):
        pytest.fail("user response contained password or password-hash material")


def _expect_user_response(response: requests.Response, fields: set[str], expected: dict,
                          secrets: list[str]) -> dict:
    body = require_status(response, 200)
    if body.get("code") != 200:
        pytest.fail("user endpoint did not return a successful response envelope")
    payload = body.get("data")
    _assert_projection_matches(payload, expected, fields)
    _assert_no_password_material(response, secrets)
    return payload


def _public_projection(user: dict) -> dict:
    return {field: user[field] for field in PUBLIC_USER_FIELDS}


def test_public_profiles_and_authenticated_projection_resist_userid_overrides():
    owner = create_user()
    other = create_user()
    admin = create_user()
    _promote_test_user_to_admin(admin.user_id)
    _set_test_user_credit(owner.user_id, 327)
    _set_test_user_credit(other.user_id, 814)

    secrets = [
        owner.password,
        other.password,
        admin.password,
        *_db_password_hashes((owner.user_id, other.user_id, admin.user_id)),
    ]

    other_profile_response = requests.put(
        url("/api/users/profile"),
        headers=other.headers,
        json={
            "nickname": "Iter21 other profile",
            "qq": "23000002",
            "avatar": "other.png",
        },
        timeout=TIMEOUT,
    )
    other_profile_body = require_status(other_profile_response, 200)
    if other_profile_body.get("code") != 200:
        pytest.fail("other test user's profile update failed")
    other_after_own_update = _db_user_snapshot(other.user_id)
    _assert_projection_matches(
        other_profile_body.get("data"), other_after_own_update, PRIVATE_USER_FIELDS
    )
    _assert_no_password_material(other_profile_response, secrets)

    other_before_attack = other_after_own_update
    profile_response = requests.put(
        url("/api/users/profile"),
        params={"userid": other.user_id},
        headers=owner.headers,
        json={
            "userid": other.user_id,
            "nickname": "Iter21 owner profile",
            "qq": "23000001",
            "avatar": "owner.png",
            "role": "admin",
            "credit": 99999,
        },
        timeout=TIMEOUT,
    )
    profile_body = require_status(profile_response, 200)
    if profile_body.get("code") != 200:
        pytest.fail("owner profile update failed")
    saved_user = profile_body.get("data")
    owner_after_update = _db_user_snapshot(owner.user_id)
    other_after_attack = _db_user_snapshot(other.user_id)
    _assert_projection_matches(saved_user, owner_after_update, PRIVATE_USER_FIELDS)
    _assert_no_password_material(profile_response, secrets)
    if other_after_attack != other_before_attack:
        pytest.fail("userid overrides changed the other isolated user's database profile")
    if owner_after_update["role"] != "user" or owner_after_update["credit"] != 327:
        pytest.fail("profile update accepted a body-supplied role or credit")

    public_owner = _public_projection(owner_after_update)
    anonymous_owner_response = requests.get(
        url(f"/api/users/{owner.user_id}"), timeout=TIMEOUT
    )
    _expect_user_response(anonymous_owner_response, PUBLIC_USER_FIELDS, public_owner, secrets)

    self_owner_response = requests.get(
        url(f"/api/users/{owner.user_id}"), headers=owner.headers, timeout=TIMEOUT
    )
    _expect_user_response(self_owner_response, PUBLIC_USER_FIELDS, public_owner, secrets)

    other_identity_owner_response = requests.get(
        url(f"/api/users/{owner.user_id}"), headers=other.headers, timeout=TIMEOUT
    )
    _expect_user_response(
        other_identity_owner_response, PUBLIC_USER_FIELDS, public_owner, secrets
    )

    query_id_override_response = requests.get(
        url(f"/api/users/{other.user_id}"),
        params={"userid": owner.user_id},
        headers=owner.headers,
        timeout=TIMEOUT,
    )
    _expect_user_response(
        query_id_override_response,
        PUBLIC_USER_FIELDS,
        _public_projection(other_after_attack),
        secrets,
    )

    auth_me_response = requests.get(
        url("/api/auth/me"), headers=owner.headers, timeout=TIMEOUT
    )
    _expect_user_response(auth_me_response, PRIVATE_USER_FIELDS, owner_after_update, secrets)

    admin_pages = math.ceil(_db_user_count() / 100)
    listed_owner = None
    for page in range(1, admin_pages + 1):
        response = requests.get(
            url("/api/admin/users"),
            params={"page": page, "page_size": 100},
            headers=admin.headers,
            timeout=TIMEOUT,
        )
        body = require_status(response, 200)
        if body.get("code") != 200 or not isinstance(body.get("data"), list):
            pytest.fail("admin users endpoint did not return its user list")
        _assert_no_password_material(response, secrets)
        listed_owner = next(
            (user for user in body["data"] if user.get("userid") == owner.user_id),
            listed_owner,
        )
        if listed_owner is not None:
            break
    if listed_owner is None:
        pytest.fail("admin users response did not include the isolated owner account")
    _assert_projection_matches(listed_owner, owner_after_update, PRIVATE_USER_FIELDS)


def _db_user_count() -> int:
    connection = owned_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM users")
            row = cursor.fetchone()
        connection.commit()
    finally:
        connection.close()
    return int(row[0])
