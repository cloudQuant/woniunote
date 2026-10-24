"""The Redis-backed rate-limit probe runs after all functional tests."""

import os

import requests

from iter21_support import TIMEOUT, url


def test_refresh_rate_limit_returns_real_429_with_retry_after():
    limit = int(os.environ.get("WONIUNOTE_TEST_RATE_LIMIT", "60"))
    saw_429 = False
    with requests.Session() as session:
        for _ in range(limit + 20):
            response = session.post(
                url("/api/auth/refresh"),
                json={"refresh_token": "invalid-rate-limit-probe"},
                timeout=TIMEOUT,
            )
            if response.status_code == 429:
                saw_429 = True
                retry_after = response.headers.get("Retry-After")
                assert retry_after is not None
                assert retry_after.isdecimal()
                assert int(retry_after) > 0
                break
    assert saw_429, "isolated Redis-backed refresh limiter did not emit HTTP 429"
