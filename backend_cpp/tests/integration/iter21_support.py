"""Shared helpers for the isolated Iteration 21 black-box HTTP suite."""

from __future__ import annotations

import os
import re
import subprocess
import uuid
from dataclasses import dataclass, field

import pytest
import requests

BASE_URL = os.environ.get("WONIUNOTE_TEST_BASE_URL", "").rstrip("/")
RUN_ID = os.environ.get("WONIUNOTE_TEST_RUN_ID", "")
TIMEOUT = 10


@dataclass
class UserCredentials:
    username: str
    password: str = field(repr=False)
    user_id: int = 0


@dataclass
class AuthenticatedUser(UserCredentials):
    access_token: str = field(default="", repr=False)
    refresh_token: str = field(default="", repr=False)

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}


def url(path: str) -> str:
    if not BASE_URL:
        pytest.fail("isolated integration runner did not set WONIUNOTE_TEST_BASE_URL")
    return f"{BASE_URL}{path}"


def response_json(response: requests.Response) -> dict:
    try:
        body = response.json()
    except ValueError:
        pytest.fail(f"expected JSON response, received HTTP {response.status_code}")
    if not isinstance(body, dict):
        pytest.fail("expected a JSON object response")
    return body


def require_status(response: requests.Response, expected: int) -> dict:
    if response.status_code != expected:
        pytest.fail(f"expected HTTP {expected}, received HTTP {response.status_code}")
    return response_json(response)


def register_user() -> UserCredentials:
    username = f"i21_{uuid.uuid4().hex[:16]}"
    password = "Iter21!StrongPass"
    response = requests.post(
        url("/api/auth/register"),
        json={"username": username, "password": password, "nickname": "Iter21"},
        timeout=TIMEOUT,
    )
    body = require_status(response, 200)
    data = body.get("data")
    if body.get("code") != 200 or not isinstance(data, dict):
        pytest.fail("registration did not return a successful user envelope")
    user_id = data.get("userid")
    if not isinstance(user_id, int) or user_id <= 0:
        pytest.fail("registration response omitted the created user id")
    return UserCredentials(username=username, password=password, user_id=user_id)


def challenge() -> tuple[str, str]:
    if not RUN_ID:
        pytest.fail("isolated integration runner did not set WONIUNOTE_TEST_RUN_ID")
    response = requests.post(
        url("/api/captcha/test/challenge"),
        json={},
        headers={"X-Woniunote-Test-Run": RUN_ID},
        timeout=TIMEOUT,
    )
    body = require_status(response, 200)
    data = body.get("data")
    if body.get("code") != 200 or not isinstance(data, dict):
        pytest.fail("challenge hook did not return a successful envelope")
    captcha_id = data.get("captcha_id")
    captcha_code = data.get("captcha_code")
    if not isinstance(captcha_id, str) or not captcha_id:
        pytest.fail("challenge hook omitted the captcha id")
    if not isinstance(captcha_code, str) or not captcha_code:
        pytest.fail("challenge hook omitted the captcha answer")
    return captcha_id, captcha_code


def login(credentials: UserCredentials) -> AuthenticatedUser:
    captcha_id, captcha_code = challenge()
    response = requests.post(
        url("/api/auth/login"),
        json={
            "username": credentials.username,
            "password": credentials.password,
            "captcha_id": captcha_id,
            "captcha_code": captcha_code,
        },
        timeout=TIMEOUT,
    )
    body = require_status(response, 200)
    data = body.get("data")
    if body.get("code") != 200 or not isinstance(data, dict):
        pytest.fail("login did not return a successful authentication envelope")
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    if not isinstance(access_token, str) or not access_token:
        pytest.fail("successful login omitted its access token")
    if not isinstance(refresh_token, str) or not refresh_token:
        pytest.fail("successful login omitted its refresh token")
    return AuthenticatedUser(
        username=credentials.username,
        password=credentials.password,
        user_id=credentials.user_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )


def create_user() -> AuthenticatedUser:
    return login(register_user())


def create_article(author: AuthenticatedUser, *, drafted: int = 0) -> int:
    response = requests.post(
        url("/api/articles"),
        headers=author.headers,
        json={
            "headline": f"Iter21 {uuid.uuid4().hex[:12]}",
            "type": 1,
            "content": "<p>isolated integration fixture</p>",
            "credit": 0,
            "drafted": drafted,
        },
        timeout=TIMEOUT,
    )
    body = require_status(response, 200)
    data = body.get("data")
    if body.get("code") != 200 or not isinstance(data, dict):
        pytest.fail("article creation did not return a successful envelope")
    article_id = data.get("articleid")
    if not isinstance(article_id, int) or article_id <= 0:
        pytest.fail("article creation response omitted the article id")
    return article_id


def owned_mysql_connection():
    """Connect only after verifying the runner's exact disposable container."""
    run_id = RUN_ID
    if not re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{12}", run_id):
        pytest.fail("isolated runner did not provide a valid run id")

    host = os.environ.get("WONIUNOTE_TEST_DB_HOST", "")
    port = os.environ.get("WONIUNOTE_TEST_DB_PORT", "")
    database = os.environ.get("WONIUNOTE_TEST_DB_NAME", "")
    username = os.environ.get("WONIUNOTE_TEST_DB_USER", "")
    password = os.environ.get("WONIUNOTE_TEST_DB_PASSWORD", "")
    container = os.environ.get("WONIUNOTE_TEST_MYSQL_CONTAINER", "")
    expected_database = f"woniunote_test_{run_id.replace('-', '')}"
    if host != "127.0.0.1" or database != expected_database or username != "root":
        pytest.fail("refusing MySQL access outside this run's loopback test schema")
    if not re.fullmatch(r"[0-9]{1,5}", port) or not 1024 <= int(port) <= 65535 or not password:
        pytest.fail("isolated runner omitted its owned MySQL connection settings")
    if not re.fullmatch(r"[0-9a-f]{64}", container):
        pytest.fail("isolated runner omitted the owned MySQL container id")

    inspect = subprocess.run(
        [
            "docker", "inspect", "--format",
            '{{.Id}}|{{index .Config.Labels "org.woniunote.iter21.run-id"}}|'
            '{{index .Config.Labels "org.woniunote.iter21.service"}}',
            container,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    expected_identity = f"{container}|{run_id}|mysql"
    if inspect.returncode != 0 or inspect.stdout.strip() != expected_identity:
        pytest.fail("MySQL container identity does not match this run")
    mapping = subprocess.run(
        ["docker", "port", container, "3306/tcp"],
        capture_output=True,
        text=True,
        check=False,
    )
    if mapping.returncode != 0 or f"127.0.0.1:{port}" not in mapping.stdout.splitlines():
        pytest.fail("MySQL container port is not this run's loopback mapping")

    import pymysql

    connection = None
    try:
        connection = pymysql.connect(
            host=host,
            port=int(port),
            user=username,
            password=password,
            database=database,
            connect_timeout=5,
            read_timeout=8,
            write_timeout=8,
            charset="utf8mb4",
            autocommit=False,
        )
        with connection.cursor() as cursor:
            cursor.execute("SET SESSION lock_wait_timeout = 5")
            cursor.execute("SET SESSION innodb_lock_wait_timeout = 5")
        return connection
    except Exception:
        if connection is not None:
            connection.close()
        pytest.fail("connection to the verified run-owned MySQL service failed")
