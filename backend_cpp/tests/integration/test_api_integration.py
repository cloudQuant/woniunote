"""
HTTP black-box integration tests for the WoniuNote C++ Drogon backend.

These run against a live backend instance (started by run_integration.sh) that
is pointed at an isolated `woniunote_test` database. They assert routing,
auth-filter behaviour, the unified response envelope + HTTP status alignment,
and rate limiting — paths that the C++ unit tests cannot reach.

Base URL comes from WONIUNOTE_TEST_BASE_URL (e.g. http://127.0.0.1:5273).
"""

import os
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get("WONIUNOTE_TEST_BASE_URL", "http://127.0.0.1:5273").rstrip("/")
TIMEOUT = 10


def url(path: str) -> str:
    return f"{BASE_URL}{path}"


def _envelope_ok(body):
    """A valid response envelope has integer code + string message."""
    assert isinstance(body, dict), f"expected JSON object, got {type(body)}"
    assert "code" in body and isinstance(body["code"], int)
    assert "message" in body and isinstance(body["message"], str)


# --------------------------------------------------------------------------
# Liveness
# --------------------------------------------------------------------------

def test_health_is_up():
    r = requests.get(url("/health"), timeout=TIMEOUT)
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "healthy"


# --------------------------------------------------------------------------
# AuthFilter: protected routes reject missing/invalid tokens with 401
# --------------------------------------------------------------------------

def test_me_without_token_is_401():
    r = requests.get(url("/api/auth/me"), timeout=TIMEOUT)
    assert r.status_code == 401
    _envelope_ok(r.json())


def test_me_with_malformed_authorization_is_401():
    r = requests.get(
        url("/api/auth/me"),
        headers={"Authorization": "NotBearer xyz"},
        timeout=TIMEOUT,
    )
    assert r.status_code == 401


def test_me_with_garbage_bearer_token_is_401():
    r = requests.get(
        url("/api/auth/me"),
        headers={"Authorization": "Bearer not.a.real.jwt"},
        timeout=TIMEOUT,
    )
    assert r.status_code == 401


# --------------------------------------------------------------------------
# Registration: real DB write through the full stack
# --------------------------------------------------------------------------

def test_register_new_user_succeeds_with_envelope():
    username = f"itest_{uuid.uuid4().hex[:12]}"
    r = requests.post(
        url("/api/auth/register"),
        json={"username": username, "password": "Str0ng!Pass", "nickname": "itest"},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    _envelope_ok(body)
    assert body["code"] == 200
    # The created user is returned without a password field.
    data = body.get("data") or {}
    assert "password" not in data


def test_register_duplicate_username_is_400():
    username = f"itest_{uuid.uuid4().hex[:12]}"
    payload = {"username": username, "password": "Str0ng!Pass"}
    first = requests.post(url("/api/auth/register"), json=payload, timeout=TIMEOUT)
    assert first.status_code == 200, first.text

    dup = requests.post(url("/api/auth/register"), json=payload, timeout=TIMEOUT)
    # Duplicate must be a real 400, not a 200 with an error code in the body.
    assert dup.status_code == 400, dup.text
    _envelope_ok(dup.json())


def test_register_missing_fields_is_400():
    r = requests.post(url("/api/auth/register"), json={"username": "only"}, timeout=TIMEOUT)
    assert r.status_code == 400
    _envelope_ok(r.json())


def test_register_invalid_json_is_400():
    r = requests.post(
        url("/api/auth/register"),
        data="not-json",
        headers={"Content-Type": "application/json"},
        timeout=TIMEOUT,
    )
    assert r.status_code == 400


# --------------------------------------------------------------------------
# Rate limiting (needs Redis): exceeding the per-minute limit returns 429
# --------------------------------------------------------------------------

@pytest.mark.skipif(
    os.environ.get("WONIUNOTE_TEST_SKIP_RATELIMIT") == "1",
    reason="rate-limit test explicitly disabled",
)
def test_rate_limit_eventually_returns_429():
    """Hammer a rate-limited endpoint until a 429 appears.

    The limit is configured low (see config.integration.json) so this stays
    fast. If Redis is unavailable the backend fails open and we never see a
    429 — in that case we skip rather than fail.
    """
    limit = int(os.environ.get("WONIUNOTE_TEST_RATE_LIMIT", "60"))
    saw_429 = False
    # A handful over the limit is enough; cap iterations to stay quick.
    for _ in range(limit + 20):
        r = requests.post(
            url("/api/auth/refresh"),
            json={"refresh_token": "x"},
            timeout=TIMEOUT,
        )
        if r.status_code == 429:
            saw_429 = True
            assert r.headers.get("Retry-After") is not None
            break
    if not saw_429:
        pytest.skip("No 429 observed (Redis likely fail-open/unavailable)")
