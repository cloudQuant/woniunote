"""Real MySQL/Redis contracts for Iteration 21 authentication and registration."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import subprocess
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import redis
import requests
import pytest

from iter21_support import (
    RUN_ID,
    TIMEOUT,
    challenge,
    login,
    owned_mysql_connection,
    register_user,
    require_status,
    url,
)


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.fail(f"isolated runner did not provide {name}")
    return value


def _db_connection():
    connection = owned_mysql_connection()
    connection.autocommit(True)
    return connection


def _verify_owned_redis_container() -> str:
    run_id = _required_env("WONIUNOTE_TEST_RUN_ID")
    if RUN_ID != run_id or not re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{12}", run_id):
        pytest.fail("isolated runner did not provide a valid run id")

    host = _required_env("WONIUNOTE_TEST_REDIS_HOST")
    raw_port = _required_env("WONIUNOTE_TEST_REDIS_PORT")
    container_id = _required_env("WONIUNOTE_TEST_REDIS_CONTAINER_ID")
    if host != "127.0.0.1" or not re.fullmatch(r"[0-9]{1,5}", raw_port):
        pytest.fail("refusing Redis access outside this run's loopback endpoint")
    port = int(raw_port)
    if not 1024 <= port <= 65535 or not re.fullmatch(r"[0-9a-f]{64}", container_id):
        pytest.fail("isolated runner omitted its owned Redis connection settings")

    inspection = subprocess.run(
        [
            "docker",
            "inspect",
            "--format",
            '{{.Id}}\t{{index .Config.Labels "org.woniunote.iter21.run-id"}}'
            '\t{{index .Config.Labels "org.woniunote.iter21.service"}}'
            '\t{{json .NetworkSettings.Ports}}\t{{.State.Running}}',
            container_id,
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if inspection.returncode != 0:
        pytest.fail("could not verify the runner-owned Redis container")
    fields = inspection.stdout.strip().split("\t")
    if len(fields) != 5:
        pytest.fail("could not verify the runner-owned Redis container metadata")
    actual_id, actual_run_id, service, ports_json, running = fields
    if (actual_id, actual_run_id, service, running) != (container_id, run_id, "redis", "true"):
        pytest.fail("refusing Redis access outside the running container owned by this run")
    try:
        bindings = json.loads(ports_json).get("6379/tcp")
    except (AttributeError, json.JSONDecodeError):
        bindings = None
    if not isinstance(bindings, list) or len(bindings) != 1:
        pytest.fail("owned Redis container has no unique published endpoint")
    binding = bindings[0]
    if binding.get("HostIp") != "127.0.0.1" or binding.get("HostPort") != str(port):
        pytest.fail("owned Redis endpoint does not match its loopback mapping")
    return container_id


def _redis_client():
    _verify_owned_redis_container()
    return redis.Redis(
        host=_required_env("WONIUNOTE_TEST_REDIS_HOST"),
        port=int(_required_env("WONIUNOTE_TEST_REDIS_PORT")),
        password=_required_env("WONIUNOTE_TEST_REDIS_PASSWORD"),
        db=0,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=2,
    )


def _session_key(user_id: int) -> str:
    return f"refresh_jti:{user_id}"


def _jwt_claims(token: str) -> dict:
    """Read claims from a token actually issued by the isolated backend."""
    parts = token.split(".")
    assert len(parts) == 3
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")))
    assert isinstance(claims, dict)
    return claims


def _sign_test_claims(claims: dict) -> str:
    """Sign controlled edge-case tokens with this disposable run's JWT key."""
    run_id = _required_env("WONIUNOTE_TEST_RUN_ID")
    if not re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{12}", run_id):
        pytest.fail("refusing to sign a token without this run's validated ID")
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}')
    payload_json = json.dumps(claims, separators=(",", ":")).encode("utf-8")
    payload = base64.urlsafe_b64encode(payload_json).rstrip(b"=")
    header_segment = header.rstrip(b"=").decode("ascii")
    payload_segment = payload.decode("ascii")
    signing_input = f"{header_segment}.{payload_segment}"
    # This secret is generated per run by the isolated integration runner.
    secret = f"iteration21-test-{run_id}-local-only".encode("utf-8")
    signature = hmac.new(secret, signing_input.encode("ascii"), hashlib.sha256).digest()
    signature_segment = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
    return f"{signing_input}.{signature_segment}"


def _expired_refresh_token(refresh_token: str) -> str:
    claims = _jwt_claims(refresh_token)
    claims["exp"] = int(time.time()) - 60
    return _sign_test_claims(claims)


def _assert_session_matches_token(client, user_id: int, refresh_token: str) -> int:
    claims = _jwt_claims(refresh_token)
    sid = claims.get("sid")
    jti = claims.get("jti")
    assert isinstance(sid, str) and sid
    assert isinstance(jti, str) and jti
    assert claims.get("type") == "refresh"
    assert client.get(_session_key(user_id)) == f"{sid}:{jti}"
    ttl = client.ttl(_session_key(user_id))
    remaining = int(claims["exp"] - time.time())
    assert ttl > 0
    assert ttl <= remaining + 1
    return ttl


def _assert_unchanged_session(client, key: str, expected_value: str, ttl_before_ms: int) -> int:
    assert client.get(key) == expected_value
    ttl_after_ms = client.pttl(key)
    assert ttl_after_ms > 0
    assert ttl_after_ms <= ttl_before_ms
    return ttl_after_ms


def _register_payload(username: str) -> dict:
    return {"username": username, "password": "Iter21!StrongPass", "nickname": "Iter21"}


def _register_request(username: str, *, headers: dict | None = None):
    return requests.post(
        url("/api/auth/register"),
        json=_register_payload(username),
        headers=headers,
        timeout=TIMEOUT,
    )


def _assert_user_and_initial_credit(connection, username: str, user_id: int) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT userid FROM users WHERE username = %s",
            (username,),
        )
        user_rows = cursor.fetchall()
        assert user_rows == ((user_id,),)
        cursor.execute(
            "SELECT category, target, credit FROM credit WHERE userid = %s",
            (user_id,),
        )
        credit_rows = cursor.fetchall()
    assert credit_rows == (("用户注册", user_id, 50),)


def _sequenced_pair(first, second):
    """Start both callers behind a barrier while fixing Redis operation order."""
    start = threading.Barrier(3)
    first_done = threading.Event()

    def run_first():
        start.wait(timeout=10)
        result = first()
        first_done.set()
        return result

    def run_second():
        start.wait(timeout=10)
        if not first_done.wait(timeout=TIMEOUT + 2):
            raise AssertionError("first request did not finish behind the barrier")
        return second()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(run_first)
        second_future = pool.submit(run_second)
        start.wait(timeout=10)
        return first_future.result(timeout=TIMEOUT + 5), second_future.result(timeout=TIMEOUT + 5)


def _auth_fault_headers(mode: str) -> dict[str, str]:
    return {
        "X-Woniunote-Test-Run": _required_env("WONIUNOTE_TEST_RUN_ID"),
        "X-Woniunote-Test-Auth-Fault": mode,
    }


def test_login_requires_and_consumes_a_real_cached_captcha():
    credentials = register_user()

    missing = requests.post(
        url("/api/auth/login"),
        json={"username": credentials.username, "password": credentials.password},
        timeout=TIMEOUT,
    )
    assert require_status(missing, 400).get("code") == 400

    captcha_id, captcha_code = challenge()

    invalid = requests.post(
        url("/api/auth/login"),
        json={
            "username": credentials.username,
            "password": credentials.password,
            "captcha_id": captcha_id,
            "captcha_code": captcha_code + "X",
        },
        timeout=TIMEOUT,
    )
    invalid_body = require_status(invalid, 400)
    assert invalid_body.get("code") == 400

    replay = requests.post(
        url("/api/auth/login"),
        json={
            "username": credentials.username,
            "password": credentials.password,
            "captcha_id": captcha_id,
            "captcha_code": captcha_code,
        },
        timeout=TIMEOUT,
    )
    replay_body = require_status(replay, 400)
    assert replay_body.get("code") == 400


def test_login_error_after_valid_captcha_consumes_the_challenge():
    credentials = register_user()
    captcha_id, captcha_code = challenge()
    payload = {
        "username": credentials.username,
        "captcha_id": captcha_id,
        "captcha_code": captcha_code,
    }

    bad_password = requests.post(
        url("/api/auth/login"),
        json={**payload, "password": credentials.password + "wrong"},
        timeout=TIMEOUT,
    )
    assert require_status(bad_password, 401).get("code") == 401

    retry = requests.post(
        url("/api/auth/login"),
        json={**payload, "password": credentials.password},
        timeout=TIMEOUT,
    )
    assert require_status(retry, 400).get("code") == 400


def test_successfully_used_captcha_cannot_be_reused_for_a_second_login():
    credentials = register_user()
    captcha_id, captcha_code = challenge()
    payload = {
        "username": credentials.username,
        "password": credentials.password,
        "captcha_id": captcha_id,
        "captcha_code": captcha_code,
    }

    success = requests.post(url("/api/auth/login"), json=payload, timeout=TIMEOUT)
    success_body = require_status(success, 200)
    assert success_body.get("code") == 200
    assert isinstance(success_body.get("data", {}).get("access_token"), str)

    replay = requests.post(url("/api/auth/login"), json=payload, timeout=TIMEOUT)
    assert require_status(replay, 400).get("code") == 400


def test_expired_cached_captcha_is_rejected_by_real_login_validation():
    credentials = register_user()
    response = requests.post(
        url("/api/captcha/test/challenge"),
        params={"expire": "true"},
        json={},
        headers={"X-Woniunote-Test-Run": _required_env("WONIUNOTE_TEST_RUN_ID")},
        timeout=TIMEOUT,
    )
    body = require_status(response, 200)
    data = body.get("data")
    assert body.get("code") == 200 and isinstance(data, dict)
    captcha_id = data.get("captcha_id")
    captcha_code = data.get("captcha_code")
    assert isinstance(captcha_id, str) and captcha_id
    assert isinstance(captcha_code, str) and captcha_code

    expired = requests.post(
        url("/api/auth/login"),
        json={
            "username": credentials.username,
            "password": credentials.password,
            "captcha_id": captcha_id,
            "captcha_code": captcha_code,
        },
        timeout=TIMEOUT,
    )
    assert require_status(expired, 400).get("code") == 400


def test_login_refresh_rotation_and_refresh_only_logout(credentials):
    authenticated = login(credentials)
    redis_client = _redis_client()

    access_claims = _jwt_claims(authenticated.access_token)
    refresh_claims = _jwt_claims(authenticated.refresh_token)
    assert access_claims.get("sid") == refresh_claims.get("sid")
    _assert_session_matches_token(
        redis_client, authenticated.user_id, authenticated.refresh_token
    )

    me = requests.get(url("/api/auth/me"), headers=authenticated.headers, timeout=TIMEOUT)
    me_body = require_status(me, 200)
    assert me_body.get("code") == 200
    assert me_body.get("data", {}).get("userid") == authenticated.user_id

    refreshed = requests.post(
        url("/api/auth/refresh"),
        json={"refresh_token": authenticated.refresh_token},
        timeout=TIMEOUT,
    )
    refreshed_body = require_status(refreshed, 200)
    refreshed_data = refreshed_body.get("data")
    assert isinstance(refreshed_data, dict)
    assert isinstance(refreshed_data.get("access_token"), str)
    assert isinstance(refreshed_data.get("refresh_token"), str)
    _assert_session_matches_token(
        redis_client, authenticated.user_id, refreshed_data["refresh_token"]
    )

    old_token = requests.post(
        url("/api/auth/refresh"),
        json={"refresh_token": authenticated.refresh_token},
        timeout=TIMEOUT,
    )
    old_body = require_status(old_token, 401)
    assert old_body.get("code") == 401

    refresh_token = refreshed_data["refresh_token"]
    logout = requests.post(
        url("/api/auth/logout"),
        json={"refresh_token": refresh_token},
        timeout=TIMEOUT,
    )
    assert require_status(logout, 200).get("code") == 200
    assert redis_client.get(_session_key(authenticated.user_id)) is None

    repeated_logout = requests.post(
        url("/api/auth/logout"),
        json={"refresh_token": refresh_token},
        timeout=TIMEOUT,
    )
    assert require_status(repeated_logout, 200).get("code") == 200

    after_logout = requests.post(
        url("/api/auth/refresh"),
        json={"refresh_token": refresh_token},
        timeout=TIMEOUT,
    )
    assert require_status(after_logout, 401).get("code") == 401


def test_logout_rejects_conflicting_access_and_refresh_identities():
    first = login(register_user())
    second = login(register_user())

    response = requests.post(
        url("/api/auth/logout"),
        headers=first.headers,
        json={"refresh_token": second.refresh_token},
        timeout=TIMEOUT,
    )
    assert require_status(response, 401).get("code") == 401

    redis_client = _redis_client()
    assert redis_client.get(_session_key(first.user_id)) is not None
    assert redis_client.get(_session_key(second.user_id)) is not None


def test_logout_rejects_same_user_credentials_with_different_sids_and_preserves_latest():
    credentials = register_user()
    old_login = login(credentials)
    current_login = login(credentials)
    redis_client = _redis_client()
    key = _session_key(credentials.user_id)
    assert _jwt_claims(old_login.refresh_token)["sid"] != _jwt_claims(
        current_login.refresh_token
    )["sid"]
    _assert_session_matches_token(
        redis_client, credentials.user_id, current_login.refresh_token
    )
    current_value = redis_client.get(key)
    ttl_before_ms = redis_client.pttl(key)
    assert current_value is not None and ttl_before_ms > 0

    conflicting_logout = requests.post(
        url("/api/auth/logout"),
        headers=old_login.headers,
        json={"refresh_token": current_login.refresh_token},
        timeout=TIMEOUT,
    )
    assert require_status(conflicting_logout, 401).get("code") == 401
    _assert_unchanged_session(redis_client, key, current_value, ttl_before_ms)

    still_valid = requests.post(
        url("/api/auth/refresh"),
        json={"refresh_token": current_login.refresh_token},
        timeout=TIMEOUT,
    )
    valid_body = require_status(still_valid, 200)
    rotated = valid_body.get("data", {}).get("refresh_token")
    assert isinstance(rotated, str) and rotated
    _assert_session_matches_token(redis_client, credentials.user_id, rotated)


def test_refresh_without_session_record_is_rejected_without_creating_state():
    authenticated = login(register_user())
    redis_client = _redis_client()
    key = _session_key(authenticated.user_id)
    assert redis_client.get(key) is not None
    assert redis_client.delete(key) == 1

    response = requests.post(
        url("/api/auth/refresh"),
        json={"refresh_token": authenticated.refresh_token},
        timeout=TIMEOUT,
    )
    assert require_status(response, 401).get("code") == 401
    assert redis_client.get(key) is None
    assert redis_client.pttl(key) == -2


def test_refresh_rejects_legacy_jti_only_session_value_without_mutating_it():
    authenticated = login(register_user())
    redis_client = _redis_client()
    key = _session_key(authenticated.user_id)
    legacy_value = _jwt_claims(authenticated.refresh_token)["jti"]
    initial_ttl_ms = redis_client.pttl(key)
    assert initial_ttl_ms > 0
    assert redis_client.set(key, legacy_value, px=initial_ttl_ms)
    ttl_before_ms = redis_client.pttl(key)

    response = requests.post(
        url("/api/auth/refresh"),
        json={"refresh_token": authenticated.refresh_token},
        timeout=TIMEOUT,
    )
    assert require_status(response, 401).get("code") == 401
    _assert_unchanged_session(redis_client, key, legacy_value, ttl_before_ms)


def test_refresh_rejects_wrong_type_bad_signature_and_expired_signed_token_without_mutation():
    authenticated = login(register_user())
    redis_client = _redis_client()
    key = _session_key(authenticated.user_id)
    expected_value = redis_client.get(key)
    ttl_before_ms = redis_client.pttl(key)
    assert expected_value is not None and ttl_before_ms > 0

    refresh_parts = authenticated.refresh_token.split(".")
    assert len(refresh_parts) == 3 and refresh_parts[2]
    replacement = "A" if refresh_parts[2][0] != "A" else "B"
    refresh_parts[2] = replacement + refresh_parts[2][1:]
    bad_signature = ".".join(refresh_parts)

    invalid_tokens = (
        authenticated.access_token,
        bad_signature,
        _expired_refresh_token(authenticated.refresh_token),
    )
    for token in invalid_tokens:
        response = requests.post(
            url("/api/auth/refresh"),
            json={"refresh_token": token},
            timeout=TIMEOUT,
        )
        assert require_status(response, 401).get("code") == 401
        ttl_before_ms = _assert_unchanged_session(
            redis_client, key, expected_value, ttl_before_ms
        )


def test_logout_ignores_expired_access_but_accepts_live_refresh():
    credentials = register_user()
    captcha_id, captcha_code = challenge()
    response = requests.post(
        url("/api/auth/login"),
        json={
            "username": credentials.username,
            "password": credentials.password,
            "captcha_id": captcha_id,
            "captcha_code": captcha_code,
        },
        headers=_auth_fault_headers("expired_access"),
        timeout=TIMEOUT,
    )
    body = require_status(response, 200)
    auth_data = body.get("data")
    assert isinstance(auth_data, dict)
    access_token = auth_data.get("access_token")
    refresh_token = auth_data.get("refresh_token")
    assert isinstance(access_token, str) and access_token
    assert isinstance(refresh_token, str) and refresh_token
    assert _jwt_claims(access_token)["sid"] == _jwt_claims(refresh_token)["sid"]

    expired_access_logout = requests.post(
        url("/api/auth/logout"),
        headers={"Authorization": f"Bearer {access_token}"},
        json={},
        timeout=TIMEOUT,
    )
    assert require_status(expired_access_logout, 401).get("code") == 401
    assert _redis_client().get(_session_key(credentials.user_id)) is not None

    still_live = requests.post(
        url("/api/auth/refresh"),
        json={"refresh_token": refresh_token},
        timeout=TIMEOUT,
    )
    assert require_status(still_live, 200).get("code") == 200

    logout = requests.post(
        url("/api/auth/logout"),
        json={"refresh_token": refresh_token},
        timeout=TIMEOUT,
    )
    assert require_status(logout, 200).get("code") == 200
    assert _redis_client().get(_session_key(credentials.user_id)) is None


def test_same_refresh_is_single_use_under_twenty_concurrent_rounds(credentials):
    redis_client = _redis_client()

    for _ in range(20):
        authenticated = login(credentials)
        _assert_session_matches_token(
            redis_client, credentials.user_id, authenticated.refresh_token
        )
        start = threading.Barrier(3)

        def refresh_same_token():
            start.wait(timeout=10)
            return requests.post(
                url("/api/auth/refresh"),
                json={"refresh_token": authenticated.refresh_token},
                timeout=TIMEOUT,
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(refresh_same_token) for _ in range(2)]
            start.wait(timeout=10)
            responses = [future.result(timeout=TIMEOUT + 5) for future in futures]

        assert sorted(response.status_code for response in responses) == [200, 401]
        winner = next(response for response in responses if response.status_code == 200)
        winner_data = require_status(winner, 200).get("data")
        assert isinstance(winner_data, dict)
        new_refresh_token = winner_data.get("refresh_token")
        assert isinstance(new_refresh_token, str) and new_refresh_token
        _assert_session_matches_token(redis_client, credentials.user_id, new_refresh_token)


def test_refresh_then_logout_and_logout_then_refresh_are_linearized():
    redis_client = _redis_client()

    refresh_then_logout_user = login(register_user())

    def do_refresh():
        return requests.post(
            url("/api/auth/refresh"),
            json={"refresh_token": refresh_then_logout_user.refresh_token},
            timeout=TIMEOUT,
        )

    refreshed, logout = _sequenced_pair(
        do_refresh,
        lambda: requests.post(
            url("/api/auth/logout"),
            json={"refresh_token": refresh_then_logout_user.refresh_token},
            timeout=TIMEOUT,
        ),
    )
    refreshed_body = require_status(refreshed, 200)
    assert require_status(logout, 200).get("code") == 200
    new_refresh = refreshed_body["data"]["refresh_token"]
    assert redis_client.get(_session_key(refresh_then_logout_user.user_id)) is None
    assert require_status(
        requests.post(
            url("/api/auth/refresh"),
            json={"refresh_token": new_refresh},
            timeout=TIMEOUT,
        ),
        401,
    ).get("code") == 401

    logout_then_refresh_user = login(register_user())
    logout, rejected_refresh = _sequenced_pair(
        lambda: requests.post(
            url("/api/auth/logout"),
            json={"refresh_token": logout_then_refresh_user.refresh_token},
            timeout=TIMEOUT,
        ),
        lambda: requests.post(
            url("/api/auth/refresh"),
            json={"refresh_token": logout_then_refresh_user.refresh_token},
            timeout=TIMEOUT,
        ),
    )
    assert require_status(logout, 200).get("code") == 200
    assert require_status(rejected_refresh, 401).get("code") == 401
    assert redis_client.get(_session_key(logout_then_refresh_user.user_id)) is None


def test_new_login_then_old_logout_preserves_replacement_session():
    redis_client = _redis_client()
    old_login = login(register_user())

    new_login_response, old_logout = _sequenced_pair(
        lambda: login(old_login),
        lambda: requests.post(
            url("/api/auth/logout"),
            json={"refresh_token": old_login.refresh_token},
            timeout=TIMEOUT,
        ),
    )
    assert require_status(old_logout, 200).get("code") == 200
    assert _jwt_claims(new_login_response.refresh_token)["sid"] != _jwt_claims(
        old_login.refresh_token
    )["sid"]
    _assert_session_matches_token(
        redis_client, old_login.user_id, new_login_response.refresh_token
    )
    refreshed = requests.post(
        url("/api/auth/refresh"),
        json={"refresh_token": new_login_response.refresh_token},
        timeout=TIMEOUT,
    )
    assert require_status(refreshed, 200).get("code") == 200


def test_one_hundred_registrations_commit_user_and_initial_credit_immediately():
    connection = _db_connection()
    try:
        for _ in range(100):
            credentials = register_user()
            _assert_user_and_initial_credit(
                connection, credentials.username, credentials.user_id
            )
    finally:
        connection.close()


def test_same_name_concurrent_registration_has_one_success_and_stable_conflicts():
    username = f"i21_race_{uuid.uuid4().hex[:20]}"
    start = threading.Barrier(9)

    def attempt_registration():
        start.wait(timeout=10)
        return _register_request(username)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(attempt_registration) for _ in range(8)]
        start.wait(timeout=10)
        responses = [future.result(timeout=TIMEOUT + 5) for future in futures]

    assert [response.status_code for response in responses].count(200) == 1
    assert [response.status_code for response in responses].count(400) == 7
    success = next(response for response in responses if response.status_code == 200)
    data = require_status(success, 200).get("data")
    assert isinstance(data, dict)
    user_id = data.get("userid")
    assert isinstance(user_id, int) and user_id > 0

    connection = _db_connection()
    try:
        _assert_user_and_initial_credit(connection, username, user_id)
    finally:
        connection.close()


def test_empty_transaction_reports_only_confirmed_commit():
    response = requests.post(
        url("/api/auth/test/empty-transaction"),
        json={},
        headers={"X-Woniunote-Test-Run": _required_env("WONIUNOTE_TEST_RUN_ID")},
        timeout=TIMEOUT,
    )
    body = require_status(response, 200)
    assert body.get("code") == 200
    assert body.get("data", {}).get("committed") is True


@pytest.mark.fault_injection
def test_registration_sql_failure_fault_rolls_back_user_and_credit():
    username = f"i21_sqlfail_{uuid.uuid4().hex[:16]}"
    connection = _db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT AUTO_INCREMENT FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users'"
            )
            next_user_id = cursor.fetchone()[0]
        assert isinstance(next_user_id, int) and next_user_id > 0
    finally:
        connection.close()

    response = _register_request(
        username,
        headers=_auth_fault_headers("sql_fail_after_user_insert"),
    )
    require_status(response, 500)

    connection = _db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT userid FROM users WHERE username = %s", (username,))
            assert cursor.fetchall() == ()
            cursor.execute(
                "SELECT creditid FROM credit WHERE userid = %s AND category = %s",
                (next_user_id, "用户注册"),
            )
            assert cursor.fetchall() == ()
    finally:
        connection.close()


@pytest.mark.fault_injection
def test_registration_discarded_commit_callback_fault_returns_unknown_with_request_id():
    username = f"i21_commitunknown_{uuid.uuid4().hex[:16]}"
    started = time.monotonic()
    response = _register_request(
        username,
        headers=_auth_fault_headers("drop_commit_callback"),
    )
    elapsed = time.monotonic() - started
    body = require_status(response, 503)
    assert elapsed <= 3.5
    assert body.get("code") == 503
    assert body.get("error_code") == "WRITE_OUTCOME_UNKNOWN"
    request_id = body.get("request_id")
    assert isinstance(request_id, str) and request_id
    assert "token" not in body

    connection = _db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT userid FROM users WHERE username = %s", (username,))
            rows = cursor.fetchall()
        assert len(rows) == 1
        _assert_user_and_initial_credit(connection, username, rows[0][0])
    finally:
        connection.close()


@pytest.mark.fault_injection
def test_z_runner_owned_redis_outage_is_bounded_and_recovers_outage():
    container_id = _verify_owned_redis_container()

    credentials = register_user()
    try:
        subprocess.run(
            ["docker", "stop", container_id],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        captcha_id, captcha_code = challenge()
        started = time.monotonic()
        response = requests.post(
            url("/api/auth/login"),
            json={
                "username": credentials.username,
                "password": credentials.password,
                "captcha_id": captcha_id,
                "captcha_code": captcha_code,
            },
            timeout=5,
        )
        elapsed = time.monotonic() - started
        body = require_status(response, 503)
        assert elapsed <= 3.0
        assert body.get("code") == 503
    finally:
        subprocess.run(
            ["docker", "start", container_id],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )

    redis_client = _redis_client()
    for _ in range(30):
        try:
            redis_client.ping()
            break
        except redis.RedisError:
            time.sleep(0.2)
    else:
        pytest.fail("runner-owned Redis did not recover after restart")
    assert login(credentials).user_id == credentials.user_id
