"""Real HTTP/admin-filter contracts for the isolated Iteration 21 run."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests

from iter21_support import RUN_ID, TIMEOUT, create_user, owned_mysql_connection, require_status, url


ADMIN_STATS_PATH = "/api/admin/stats"
ADMIN_TIMEOUT_SECONDS = 5.0


def _required_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        pytest.fail(f"isolated runner did not provide {name}")
    return value


def _admin_get(session: requests.Session, access_token: str) -> requests.Response:
    return session.get(
        url(ADMIN_STATS_PATH),
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=TIMEOUT,
    )


def _set_role(user_id: int, role: str) -> None:
    connection = owned_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE users SET role = %s WHERE userid = %s", (role, user_id))
            assert cursor.rowcount == 1
        connection.commit()
    finally:
        connection.close()


def _delete_user(user_id: int) -> None:
    """Delete only a newly-created fixture user in this run-owned schema."""
    connection = owned_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE userid = %s", (user_id,))
            assert cursor.rowcount == 1
        connection.commit()
    finally:
        connection.close()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _signed_test_access_token(sub: str) -> str:
    """Sign only malformed-sub filter probes with this disposable run's JWT key."""
    if not re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{12}", RUN_ID):
        pytest.fail("refusing to forge a token without this run's validated ID")
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64url(
        json.dumps(
            {
                "iss": "woniunote",
                "sub": sub,
                "type": "access",
                "iat": int(time.time()),
                "exp": int(time.time()) + 300,
            },
            separators=(",", ":"),
        ).encode()
    )
    signing_input = f"{header}.{payload}"
    # run_integration.sh writes this test-only value into its private generated
    # config. It is deliberately derived from RUN_ID and never logged.
    secret = f"iteration21-test-{RUN_ID}-local-only".encode("utf-8")
    signature = hmac.new(secret, signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url(signature)}"


def _verify_owned_mysql_container() -> tuple[str, int]:
    run_id = _required_env("WONIUNOTE_TEST_RUN_ID")
    if RUN_ID != run_id or not re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{12}", run_id):
        pytest.fail("pytest and the isolated MySQL run IDs do not match")
    container_id = _required_env("WONIUNOTE_TEST_MYSQL_CONTAINER_ID")
    host = _required_env("WONIUNOTE_TEST_DB_HOST")
    raw_port = _required_env("WONIUNOTE_TEST_DB_PORT")
    if host != "127.0.0.1" or not re.fullmatch(r"[0-9]{1,5}", raw_port):
        pytest.fail("refusing MySQL fault injection outside a loopback endpoint")
    port = int(raw_port)
    if not 1024 <= port <= 65535 or not re.fullmatch(r"[0-9a-f]{64}", container_id):
        pytest.fail("isolated runner omitted its owned MySQL container identity")

    inspected = subprocess.run(
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
    if inspected.returncode != 0:
        pytest.fail("could not verify the runner-owned MySQL container")
    fields = inspected.stdout.strip().split("\t")
    if len(fields) != 5:
        pytest.fail("could not verify the runner-owned MySQL container metadata")
    actual_id, actual_run_id, service, ports_json, running = fields
    if (actual_id, actual_run_id, service, running) != (container_id, run_id, "mysql", "true"):
        pytest.fail("refusing to stop a MySQL container not owned by this run")
    try:
        bindings = json.loads(ports_json).get("3306/tcp")
    except (AttributeError, json.JSONDecodeError):
        bindings = None
    if not isinstance(bindings, list) or len(bindings) != 1:
        pytest.fail("owned MySQL container has no unique published endpoint")
    binding = bindings[0]
    if binding.get("HostIp") != "127.0.0.1" or binding.get("HostPort") != str(port):
        pytest.fail("owned MySQL endpoint does not match its loopback mapping")
    return container_id, port


def _blocked_admin_select_visible(connection) -> bool:
    db_user = _required_env("WONIUNOTE_TEST_DB_USER")
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.PROCESSLIST "
            "WHERE DB = DATABASE() AND USER = %s "
            "AND INFO LIKE %s",
            (db_user, "SELECT role FROM users WHERE userid =%"),
        )
        return cursor.fetchone()[0] > 0


def test_admin_filter_allows_admin_and_rejects_non_admin(user):
    admin = create_user()
    _set_role(admin.user_id, "admin")

    with requests.Session() as session:
        allowed = _admin_get(session, admin.access_token)
        allowed_body = require_status(allowed, 200)
        assert allowed_body.get("code") == 200
        stats = allowed_body.get("data")
        assert isinstance(stats, dict)
        assert {
            "user_count",
            "article_count",
            "comment_count",
            "articles_week",
            "users_week",
        }.issubset(stats)

        denied = _admin_get(session, user.access_token)
        denied_body = require_status(denied, 403)
        assert denied_body.get("code") == 403


def test_admin_filter_rejects_a_valid_token_for_a_missing_user():
    missing = create_user()
    _delete_user(missing.user_id)

    with requests.Session() as session:
        response = _admin_get(session, missing.access_token)
    body = require_status(response, 401)
    assert body.get("code") == 401


def test_admin_filter_rejects_empty_noninteger_negative_and_overflow_subjects():
    with requests.Session() as session:
        for sub in ("", "not-an-integer", "-1", "2147483648", "9223372036854775808"):
            response = _admin_get(session, _signed_test_access_token(sub))
            body = require_status(response, 401)
            assert body.get("code") == 401


@pytest.mark.fault_injection
def test_admin_filter_times_out_while_real_users_table_lock_is_held_then_recovers():
    admin = create_user()
    _set_role(admin.user_id, "admin")
    connection = owned_mysql_connection()
    observer = None
    executor = ThreadPoolExecutor(max_workers=1)
    session = requests.Session()
    response_future = None
    started = time.monotonic()
    try:
        connection.autocommit(True)
        observer = owned_mysql_connection()
        observer.autocommit(True)
        with connection.cursor() as cursor:
            cursor.execute("LOCK TABLES users WRITE")

        response_future = executor.submit(_admin_get, session, admin.access_token)
        lock_deadline = time.monotonic() + 3.0
        while time.monotonic() < lock_deadline and not _blocked_admin_select_visible(observer):
            time.sleep(0.05)
        assert _blocked_admin_select_visible(observer), (
            "AdminFilter SQL never waited on the real table lock"
        )

        response = response_future.result(timeout=8.0)
        elapsed = time.monotonic() - started
        body = require_status(response, 503)
        assert body.get("code") == 503
        assert 4.0 <= elapsed < ADMIN_TIMEOUT_SECONDS + 3.0
    finally:
        if observer is not None:
            observer.close()
        connection.close()  # Closing the owner session releases LOCK TABLES.
        if response_future is not None and not response_future.done():
            response_future.result(timeout=TIMEOUT)
        executor.shutdown(wait=True, cancel_futures=True)

    # The late SELECT now completes after the timeout response. Reusing the
    # same HTTP keep-alive session checks that it neither grants access nor
    # injects a second response ahead of the next request.
    time.sleep(0.2)
    recovered = _admin_get(session, admin.access_token)
    recovered_body = require_status(recovered, 200)
    assert recovered_body.get("code") == 200
    session.close()


@pytest.mark.fault_injection
def test_admin_filter_database_outage_is_503_and_owned_service_recovers():
    admin = create_user()
    _set_role(admin.user_id, "admin")
    container_id, _ = _verify_owned_mysql_container()
    session = requests.Session()
    assert require_status(_admin_get(session, admin.access_token), 200).get("code") == 200

    stopped = False
    try:
        subprocess.run(
            ["docker", "stop", container_id],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        stopped = True
        started = time.monotonic()
        response = _admin_get(session, admin.access_token)
        elapsed = time.monotonic() - started
        body = require_status(response, 503)
        assert body.get("code") == 503
        assert elapsed < 8.0
    finally:
        if stopped:
            subprocess.run(
                ["docker", "start", container_id],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )

    recovery_deadline = time.monotonic() + 30.0
    while time.monotonic() < recovery_deadline:
        try:
            recovered = _admin_get(session, admin.access_token)
        except requests.RequestException:
            time.sleep(0.25)
            continue
        if recovered.status_code == 200:
            assert require_status(recovered, 200).get("code") == 200
            break
        assert recovered.status_code == 503
        time.sleep(0.25)
    else:
        pytest.fail("admin endpoint did not recover after restarting this run's MySQL container")
    session.close()
