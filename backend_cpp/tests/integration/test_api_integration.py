"""Basic HTTP contracts against the real isolated C++ backend."""

import requests

from iter21_support import TIMEOUT, challenge, response_json, require_status, url


def test_health_is_up():
    response = requests.get(url("/health"), timeout=TIMEOUT)
    body = require_status(response, 200)
    assert body.get("status") == "healthy"


def test_article_types_preserve_seeded_chinese_names():
    response = requests.get(url("/api/articles/types"), timeout=TIMEOUT)
    body = require_status(response, 200)
    assert body.get("code") == 200

    data = body.get("data")
    assert isinstance(data, dict)
    types = data.get("types")
    assert isinstance(types, dict)
    assert types.get("1") == "交易策略"
    assert types.get("2") == "量化框架"
    assert types.get("101") == "CTA策略"


def test_protected_auth_endpoint_rejects_missing_and_invalid_tokens():
    missing = requests.get(url("/api/auth/me"), timeout=TIMEOUT)
    assert missing.status_code == 401

    malformed = requests.get(
        url("/api/auth/me"),
        headers={"Authorization": "NotBearer invalid"},
        timeout=TIMEOUT,
    )
    assert malformed.status_code == 401

    garbage = requests.get(
        url("/api/auth/me"),
        headers={"Authorization": "Bearer not.a.real.jwt"},
        timeout=TIMEOUT,
    )
    assert garbage.status_code == 401


def test_challenge_test_hook_requires_current_run_identity():
    response = requests.post(
        url("/api/captcha/test/challenge"),
        json={},
        headers={"X-Woniunote-Test-Run": "not-the-current-run"},
        timeout=TIMEOUT,
    )
    assert response.status_code == 404
    # The failed request must not have returned a challenge body.
    body = response_json(response)
    assert "captcha_code" not in body
    assert "captcha_id" not in body


def test_auth_register_duplicate_and_invalid_payload_statuses():
    captcha_id, captcha_code = challenge()
    assert captcha_id and captcha_code

    username = f"i21_dup_{captcha_id[:12]}"
    payload = {"username": username, "password": "Iter21!StrongPass"}
    first = requests.post(url("/api/auth/register"), json=payload, timeout=TIMEOUT)
    first_body = require_status(first, 200)
    assert first_body.get("code") == 200

    duplicate = requests.post(url("/api/auth/register"), json=payload, timeout=TIMEOUT)
    duplicate_body = require_status(duplicate, 400)
    assert duplicate_body.get("code") == 400

    missing = requests.post(
        url("/api/auth/register"), json={"username": "only"}, timeout=TIMEOUT
    )
    missing_body = require_status(missing, 400)
    assert missing_body.get("code") == 400

    malformed = requests.post(
        url("/api/auth/register"),
        data="not-json",
        headers={"Content-Type": "application/json"},
        timeout=TIMEOUT,
    )
    assert malformed.status_code == 400
