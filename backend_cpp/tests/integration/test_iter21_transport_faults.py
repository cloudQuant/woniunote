"""Real MySQL/Redis ACK loss and delay tests for the isolated Iteration 21 run."""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import socket
import subprocess
import threading
import time
import uuid
import warnings
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

import pytest
import requests

from iter21_fault_proxy import (
    MysqlPreparedCommitTracker,
    TransparentFaultProxy,
    extract_mysql_packets,
    extract_resp_commands,
    extract_resp_frames,
    is_mysql_commit,
    is_mysql_commit_prepare,
    is_mysql_ssl_request,
    is_redis_auth_write,
    mysql_prepare_response_statement_id,
)
from iter21_support import RUN_ID, UserCredentials, owned_mysql_connection, register_user


TEST_TIMEOUT_SECONDS = 8
APP_DELAY_SECONDS = 2.0
REDIS_REPLY_DELAY_SECONDS = 3.0
SESSION_VALUE = re.compile(r"^[0-9a-f]{32}:[0-9a-f]{32}$")
AUTH_REDIS_COMPLETION = re.compile(
    r"^\[AUTH_REDIS_COMPLETION\] id=(\d+) operation=(login|refresh|logout) "
    r"elapsed_ms=([0-9]+(?:\.[0-9]+)?) "
    r"outcome=(success|exception|synchronous_error)$",
    re.MULTILINE,
)


def _required_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        pytest.fail(f"isolated harness omitted required setting {name}")
    return value


def _loopback_port(excluded: Optional[set[int]] = None) -> int:
    excluded = excluded or set()
    for _ in range(20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        if port not in excluded:
            return port
    pytest.fail("could not allocate a distinct loopback backend port")
    raise AssertionError("unreachable")


def _verify_owned_container(service: str) -> tuple[str, int]:
    run_id = _required_env("WONIUNOTE_TEST_RUN_ID")
    if RUN_ID != run_id:
        pytest.fail("pytest and service run IDs disagree")
    if service == "mysql":
        container_id = _required_env("WN_I21_MYSQL_ID")
        host = _required_env("WN_I21_DB_HOST")
        port = int(_required_env("WN_I21_DB_PORT"))
        internal_port = "3306/tcp"
    elif service == "redis":
        container_id = _required_env("WN_I21_REDIS_ID")
        host = _required_env("WN_I21_REDIS_HOST")
        port = int(_required_env("WN_I21_REDIS_PORT"))
        internal_port = "6379/tcp"
    else:
        raise ValueError("unsupported owned service")

    if host != "127.0.0.1" or not 1024 <= port <= 65535:
        pytest.fail(f"owned {service} endpoint is not a validated loopback port")
    completed = subprocess.run(
        [
            "docker",
            "inspect",
            "--format",
            '{{.Id}}\t{{index .Config.Labels "org.woniunote.iter21.run-id"}}'
            '\t{{index .Config.Labels "org.woniunote.iter21.service"}}'
            "\t{{json .NetworkSettings.Ports}}\t{{.State.Running}}",
            container_id,
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if completed.returncode != 0:
        pytest.fail(f"could not verify the run-owned {service} container")
    fields = completed.stdout.strip().split("\t")
    if len(fields) != 5:
        pytest.fail(f"could not verify the run-owned {service} container metadata")
    actual_id, actual_run_id, actual_service, ports_text, running = fields
    if (
        actual_id != container_id
        or actual_run_id != run_id
        or actual_service != service
        or running != "true"
    ):
        pytest.fail(f"refusing to connect to a non-owned {service} container")
    try:
        bindings = json.loads(ports_text).get(internal_port)
    except (AttributeError, json.JSONDecodeError):
        bindings = None
    if not isinstance(bindings, list) or len(bindings) != 1:
        pytest.fail(f"owned {service} container has no unique published endpoint")
    binding = bindings[0]
    if binding.get("HostIp") != "127.0.0.1" or binding.get("HostPort") != str(port):
        pytest.fail(f"owned {service} endpoint does not match its loopback mapping")
    return container_id, port


def _docker_cli(service: str, args: list[str]) -> str:
    if service == "mysql":
        container_id, _ = _verify_owned_container("mysql")
        env_name = "MYSQL_PWD"
        secret = _required_env("WN_I21_DB_PASSWORD")
    else:
        container_id, _ = _verify_owned_container("redis")
        env_name = "REDISCLI_AUTH"
        secret = _required_env("WN_I21_REDIS_PASSWORD")
    child_env = os.environ.copy()
    child_env[env_name] = secret
    completed = subprocess.run(
        ["docker", "exec", "-e", env_name, container_id, *args],
        env=child_env,
        capture_output=True,
        text=True,
        timeout=6,
        check=False,
    )
    if completed.returncode != 0:
        pytest.fail(f"independent {service} verification query failed")
    return completed.stdout.rstrip("\r\n")


def _register_via_main_service() -> UserCredentials:
    return register_user()


def _new_unregistered_credentials() -> UserCredentials:
    return UserCredentials(
        username=f"i21_fault_{uuid.uuid4().hex[:18]}",
        password="Iter21!StrongPass",
    )


def _challenge_at(base_url: str) -> tuple[str, str]:
    response = requests.post(
        f"{base_url}/api/captcha/test/challenge",
        json={},
        headers={"X-Woniunote-Test-Run": _required_env("WONIUNOTE_TEST_RUN_ID")},
        timeout=5,
    )
    try:
        body = response.json()
    except ValueError:
        pytest.fail("secondary backend challenge hook did not return JSON")
    data = body.get("data") if isinstance(body, dict) else None
    if (
        response.status_code != 200
        or not isinstance(data, dict)
        or body.get("code") != 200
        or not isinstance(data.get("captcha_id"), str)
        or not isinstance(data.get("captcha_code"), str)
    ):
        pytest.fail("secondary backend did not provide its real test challenge")
    return data["captcha_id"], data["captcha_code"]


def _login_at(base_url: str, credentials: UserCredentials) -> dict:
    captcha_id, captcha_code = _challenge_at(base_url)
    response = requests.post(
        f"{base_url}/api/auth/login",
        json={
            "username": credentials.username,
            "password": credentials.password,
            "captcha_id": captcha_id,
            "captcha_code": captcha_code,
        },
        timeout=TEST_TIMEOUT_SECONDS,
    )
    try:
        body = response.json()
    except ValueError:
        pytest.fail("secondary backend login did not return JSON")
    data = body.get("data") if isinstance(body, dict) else None
    if (
        response.status_code != 200
        or not isinstance(data, dict)
        or body.get("code") != 200
        or not isinstance(data.get("refresh_token"), str)
        or not isinstance(data.get("access_token"), str)
    ):
        pytest.fail("secondary backend could not establish the baseline session")
    return data


def _jwt_claims(token: str) -> dict:
    try:
        parts = token.split(".")
        encoded = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(encoded.encode("ascii")))
    except (IndexError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        pytest.fail("refresh token claim decoding failed")
    if not isinstance(claims, dict):
        pytest.fail("refresh token claims are malformed")
    return claims


def _redis_session(user_id: int) -> tuple[str, int]:
    key = f"refresh_jti:{user_id}"
    value = _docker_cli("redis", ["redis-cli", "--raw", "GET", key])
    ttl_text = _docker_cli("redis", ["redis-cli", "--raw", "TTL", key])
    try:
        ttl = int(ttl_text)
    except ValueError:
        pytest.fail("independent Redis TTL query returned an invalid result")
    return value, ttl


def _record_fault_evidence(
    case_name: str,
    mysql: TransparentFaultProxy,
    redis: TransparentFaultProxy,
    auth_redis_completions: Optional[list[dict]] = None,
) -> None:
    evidence_dir = Path(_required_env("WONIUNOTE_TEST_EVIDENCE_DIR"))
    evidence_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    evidence_dir.chmod(0o700)
    attempt_id = getattr(mysql, "evidence_attempt_id", uuid.uuid4().hex[:12])
    path = evidence_dir / f"iter21-transport-{case_name}-{attempt_id}.json"
    payload = {
        "run_id": _required_env("WONIUNOTE_TEST_RUN_ID"),
        "case": case_name,
        "attempt_id": attempt_id,
        "mysql": mysql.snapshot(),
        "redis": redis.snapshot(),
        "proxy_endpoints": {
            "mysql": {
                "listen_host": mysql.host,
                "listen_port": mysql.port,
                "upstream_host": mysql.upstream_host,
                "upstream_port": mysql.upstream_port,
            },
            "redis": {
                "listen_host": redis.host,
                "listen_port": redis.port,
                "upstream_host": redis.upstream_host,
                "upstream_port": redis.upstream_port,
            },
        },
        "secondary_backend_config_endpoints": {
            "mysql": getattr(mysql, "secondary_backend_endpoint", None),
            "redis": getattr(redis, "secondary_backend_endpoint", None),
        },
        "payloads_recorded": False,
    }
    if auth_redis_completions is not None:
        payload["auth_redis_completion_events"] = auth_redis_completions
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2)
        stream.write("\n")


def _require_mysql_fault_observable(proxy: TransparentFaultProxy) -> None:
    metrics = proxy.snapshot()
    lifetime = metrics.get("lifetime")
    if not isinstance(lifetime, dict):
        pytest.fail("MySQL proxy omitted lifetime protocol diagnostics")
    if (
        lifetime.get("protocol_gaps", 0)
        or lifetime.get("mysql_tls_connections", 0)
        or lifetime.get("mysql_unsupported_connections", 0)
    ):
        pytest.fail(
            "MySQL proxy cannot inspect the actual COMMIT path because this backend "
            "connection negotiated TLS or another unsupported protocol: "
            f"{json.dumps(metrics, sort_keys=True)}"
        )


class _FaultBackend:
    def __init__(self):
        self.run_id = _required_env("WONIUNOTE_TEST_RUN_ID")
        self.runtime = Path(_required_env("WONIUNOTE_TEST_RUNTIME_DIR")).resolve()
        self.mysql_container_id, self.mysql_port = _verify_owned_container("mysql")
        self.redis_container_id, self.redis_port = _verify_owned_container("redis")
        self.mysql_proxy = TransparentFaultProxy(
            "mysql", "127.0.0.1", self.mysql_port
        )
        self.redis_proxy = TransparentFaultProxy(
            "redis", "127.0.0.1", self.redis_port
        )
        self.attempt_id = uuid.uuid4().hex[:12]
        self.mysql_proxy.evidence_attempt_id = self.attempt_id
        self.redis_proxy.evidence_attempt_id = self.attempt_id
        self.root = self.runtime / "fault-proxy-runtime"
        self.base_url = ""
        self.process: Optional[subprocess.Popen] = None
        self.log_file = None
        self.pid_file: Optional[Path] = None
        self.owns_runtime = False

    def start(self) -> "_FaultBackend":
        try:
            if os.environ.get("WN_I21_MYSQL_TLS_STATUS") != "DISABLED":
                pytest.fail(
                    "secondary backend plaintext transport requires the run-owned "
                    "MySQL TLS-disabled readback"
                )
            if self.root.exists():
                pytest.fail("transport-fault runtime already exists for this run")
            self.root.mkdir(mode=0o700)
            self.owns_runtime = True
            for name in ("config", "logs", "uploads", "evidence"):
                (self.root / name).mkdir(mode=0o700)
            self.mysql_proxy.start()
            self.redis_proxy.start()
            try:
                primary_port = int(_required_env("WN_I21_TEST_PORT"))
            except ValueError:
                pytest.fail("primary backend HTTP port is invalid")
            if not 1024 <= primary_port <= 65535:
                pytest.fail("primary backend HTTP port is invalid")
            excluded_ports = {
                self.mysql_proxy.port,
                self.redis_proxy.port,
                primary_port,
                3306,
                6379,
                5173,
                8888,
            }
            port = _loopback_port(excluded_ports)
            self.base_url = f"http://127.0.0.1:{port}"
            config_path = self._write_config(port)
            binary = Path(_required_env("WONIUNOTE_TEST_BACKEND_BIN")).resolve()
            if not binary.is_file() or not os.access(binary, os.X_OK):
                pytest.fail("isolated harness backend binary is unavailable")
            process_env = os.environ.copy()
            process_env.pop("WONIUNOTE_TEST_BASE_URL", None)
            process_env["WONIUNOTE_ENV"] = "test"
            process_env["WONIUNOTE_TEST_RUN_ID"] = self.run_id
            # MariaDB Connector/C may enforce TLS by default when built with
            # DEFAULT_SSL_VERIFY_SERVER_CERT. This process-only override allows
            # plaintext access to the verified run-owned TLS-disabled test DB.
            process_env["MARIADB_TLS_DISABLE_PEER_VERIFICATION"] = "1"
            # Keep the merged process stream separate from Logger's own file
            # sink; separate descriptors writing one path can overwrite each
            # other's offsets and corrupt the completion markers.
            self.log_file = (self.root / "logs" / "process.log").open("w", encoding="utf-8")
            self.process = subprocess.Popen(
                [str(binary), str(config_path)],
                cwd=str(self.root),
                env=process_env,
                stdout=self.log_file,
                stderr=subprocess.STDOUT,
            )
            self.pid_file = self.root / "backend.pid"
            self.pid_file.write_text(f"{self.process.pid}\n", encoding="ascii")
            self.pid_file.chmod(0o600)
            self._wait_ready()
            return self
        except BaseException:
            self.close()
            raise

    def _write_config(self, port: int) -> Path:
        template = Path(_required_env("WONIUNOTE_TEST_CONFIG_TEMPLATE"))
        config = json.loads(template.read_text(encoding="utf-8"))
        config["listeners"] = [{"address": "127.0.0.1", "port": port, "https": False}]
        app = config.setdefault("app", {})
        app["document_root"] = str(self.root / "uploads")
        app["upload_path"] = str(self.root / "uploads")
        app["log"] = {
            "log_path": str(self.root / "logs"),
            "logfile_base_name": "transport-backend",
            "log_level": "WARN",
        }
        db = config["db_clients"][0]
        db.update(
            {
                "host": "127.0.0.1",
                "port": self.mysql_proxy.port,
                "dbname": _required_env("WN_I21_DB_NAME"),
                "user": _required_env("WN_I21_DB_USER"),
                "passwd": _required_env("WN_I21_DB_PASSWORD"),
                "number_of_connections": 4,
                "timeout": 5.0,
            }
        )
        self.mysql_proxy.secondary_backend_endpoint = {
            "host": db["host"],
            "port": int(db["port"]),
        }
        redis = config["redis_clients"][0]
        redis.update(
            {
                "host": "127.0.0.1",
                "port": self.redis_proxy.port,
                "passwd": _required_env("WN_I21_REDIS_PASSWORD"),
                "db": 0,
                "number_of_connections": 2,
                "timeout": 5.0,
            }
        )
        self.redis_proxy.secondary_backend_endpoint = {
            "host": redis["host"],
            "port": int(redis["port"]),
        }
        custom = config["custom_config"]
        custom.update(
            {
                "app_name": "WoniuNote-Iter21-Transport-Fault-Test",
                "app_mode": "test",
                "jwt_secret": f"iteration21-fault-{self.run_id}-local-only",
                "test_run_id": self.run_id,
            }
        )
        path = self.root / "config" / "config.json"
        path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        path.chmod(0o600)
        return path

    def _wait_ready(self) -> None:
        if self.process is None:
            pytest.fail("secondary backend process was not created")
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                pytest.fail("secondary backend exited before its health endpoint became ready")
            try:
                response = requests.get(f"{self.base_url}/health", timeout=0.5)
                if response.status_code == 200:
                    return
            except requests.RequestException:
                pass
            time.sleep(0.1)
        pytest.fail("secondary backend did not become ready within the startup limit")

    def completion_log_offset(self) -> int:
        log_path = self.root / "logs" / "process.log"
        if not log_path.is_file():
            pytest.fail("isolated backend completion log is unavailable")
        return log_path.stat().st_size

    def auth_redis_completions(self, offset: int) -> list[dict]:
        # The backend process redirects stderr to its one private stdout log.
        # The marker itself bypasses Logger, whose console and file sinks can
        # duplicate a line into the same file.
        log_path = self.root / "logs" / "process.log"
        try:
            with log_path.open("rb") as stream:
                stream.seek(offset)
                tail = stream.read().decode("utf-8", errors="replace")
        except OSError:
            pytest.fail("isolated backend completion log could not be read")
        return [
            {
                "id": match.group(1),
                "operation": match.group(2),
                "elapsed_ms": float(match.group(3)),
                "outcome": match.group(4),
            }
            for match in AUTH_REDIS_COMPLETION.finditer(tail)
        ]

    def close(self) -> None:
        backend_return_code: Optional[int] = None
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2.0)
            backend_return_code = self.process.returncode
            self.process = None
        self.redis_proxy.stop()
        self.mysql_proxy.stop()
        if self.log_file is not None:
            self.log_file.close()
            self.log_file = None
        if self.pid_file is not None:
            self.pid_file.unlink(missing_ok=True)
            self.pid_file = None
        if self.owns_runtime:
            preserved = False
            try:
                self._preserve_runtime_evidence(backend_return_code)
                preserved = True
            except (OSError, ValueError) as error:
                warnings.warn(
                    "could not preserve private transport diagnostics; retaining the "
                    f"run-owned runtime directory ({type(error).__name__})",
                    RuntimeWarning,
                )
            if preserved:
                shutil.rmtree(self.root, ignore_errors=True)
                self.owns_runtime = False

    def _preserve_runtime_evidence(self, backend_return_code: Optional[int]) -> None:
        evidence_dir = Path(_required_env("WONIUNOTE_TEST_EVIDENCE_DIR"))
        evidence_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        evidence_dir.chmod(0o700)
        source = self.root / "logs" / "process.log"
        log_path = evidence_dir / f"iter21-transport-backend-{self.attempt_id}.log"
        if source.exists():
            source_info = source.stat()
            if not source.is_file():
                raise OSError("backend diagnostic log is not a regular file")
            max_bytes = 2 * 1024 * 1024
            with source.open("rb") as input_stream:
                start_offset = max(0, source_info.st_size - max_bytes)
                input_stream.seek(start_offset)
                retained = input_stream.read(max_bytes)
            descriptor = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as output_stream:
                output_stream.write(retained)
            backend_log = {
                "file": log_path.name,
                "original_bytes": source_info.st_size,
                "retained_bytes": len(retained),
                "truncated": source_info.st_size > len(retained),
                "contents_included": True,
            }
        else:
            backend_log = {"file": None, "contents_included": False}
        metadata = {
            "run_id": self.run_id,
            "attempt_id": self.attempt_id,
            "backend_exit_code": backend_return_code,
            "http_listen_port": urlsplit(self.base_url).port if self.base_url else None,
            "backend_log": backend_log,
            "mysql": {
                "listen_host": self.mysql_proxy.host,
                "listen_port": self.mysql_proxy.port,
                "upstream_host": self.mysql_proxy.upstream_host,
                "upstream_port": self.mysql_proxy.upstream_port,
                "metrics": self.mysql_proxy.snapshot(),
                "secondary_backend_config_endpoint": getattr(
                    self.mysql_proxy, "secondary_backend_endpoint", None
                ),
            },
            "redis": {
                "listen_host": self.redis_proxy.host,
                "listen_port": self.redis_proxy.port,
                "upstream_host": self.redis_proxy.upstream_host,
                "upstream_port": self.redis_proxy.upstream_port,
                "metrics": self.redis_proxy.snapshot(),
                "secondary_backend_config_endpoint": getattr(
                    self.redis_proxy, "secondary_backend_endpoint", None
                ),
            },
            "payloads_recorded": False,
        }
        metadata_path = evidence_dir / f"iter21-transport-runtime-{self.attempt_id}.json"
        descriptor = os.open(
            metadata_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(metadata, stream, indent=2)
            stream.write("\n")


def _wait_for_auth_redis_completion(
    backend: _FaultBackend,
    offset: int,
    operation: str,
    outcome: str,
) -> dict:
    deadline = time.monotonic() + 1.0
    events = backend.auth_redis_completions(offset)
    while not events and time.monotonic() < deadline:
        time.sleep(0.02)
        events = backend.auth_redis_completions(offset)
    if len(events) != 1:
        pytest.fail(
            "expected exactly one local authentication Redis completion marker; "
            f"found {len(events)}"
        )
    event = events[0]
    if event["operation"] != operation or event["outcome"] != outcome:
        pytest.fail(
            "authentication Redis completion marker did not match the operation "
            "and callback outcome"
        )
    if event["elapsed_ms"] > 2000.0:
        pytest.fail("local authentication Redis callback exceeded 2000 ms")
    return event


def _require_unchanged_auth_redis_completion(
    backend: _FaultBackend, offset: int, expected: dict
) -> None:
    deadline = time.monotonic() + 0.5
    while True:
        events = backend.auth_redis_completions(offset)
        if events != [expected]:
            pytest.fail(
                "late Redis ACK produced an additional local completion marker or "
                "changed the first completion"
            )
        if time.monotonic() >= deadline:
            return
        time.sleep(0.02)


def _auth_completion_evidence_snapshot(
    backend: _FaultBackend, offset: int, fallback: list[dict]
) -> list[dict]:
    try:
        return backend.auth_redis_completions(offset)
    except BaseException:
        # Do not replace the first assertion or transport failure while saving
        # the private, sanitized evidence summary.
        return fallback


def _wait_for_delayed_redis_ack(backend: _FaultBackend) -> None:
    deadline = time.monotonic() + REDIS_REPLY_DELAY_SECONDS + 2.0
    while (
        backend.redis_proxy.snapshot()["delayed_replies_forwarded"] != 1
        and time.monotonic() < deadline
    ):
        time.sleep(0.05)


def _assert_no_second_http_response(sock: socket.socket) -> None:
    sock.settimeout(0.25)
    try:
        extra_response = sock.recv(1)
    except socket.timeout:
        extra_response = b""
    if extra_response:
        pytest.fail("a second HTTP response arrived after the late Redis callback")


@pytest.fixture
def fault_backend():
    backend = _FaultBackend()
    try:
        backend.start()
        yield backend
    finally:
        backend.close()


def test_protocol_matchers_ignore_non_auth_evals_and_non_commit_queries():
    assert not is_mysql_commit(b"\x03SELECT 1")
    assert is_mysql_commit(b"\x03 COMMIT ; ")
    assert not is_mysql_commit_prepare(b"\x16SELECT 1")
    tracker = MysqlPreparedCommitTracker()
    prepared_payload = b"\x16COMMIT"
    assert tracker.track_prepare(prepared_payload)
    statement_id = 0x12345678
    prepare_ok_payload = (
        b"\x00"
        + statement_id.to_bytes(4, "little")
        + b"\x00\x00\x00\x00\x00\x00\x00"
    )
    prepare_ok_frame = (
        len(prepare_ok_payload).to_bytes(3, "little")
        + b"\x01"
        + prepare_ok_payload
    )
    assert mysql_prepare_response_statement_id(prepare_ok_frame) == statement_id
    tracker.observe_prepare_reply(prepare_ok_frame)
    execute_payload = b"\x17" + statement_id.to_bytes(4, "little") + b"\x00\x01\x00\x00"
    assert tracker.is_commit_execute(execute_payload)
    tracker.close_statement(statement_id)
    assert not tracker.is_commit_execute(execute_payload)
    tracker.track_prepare(prepared_payload)
    tracker.observe_prepare_reply(prepare_ok_frame)
    assert tracker.is_commit_execute(execute_payload)
    tracker.reset()
    assert not tracker.is_commit_execute(execute_payload)
    ssl_request = (1 << 11).to_bytes(4, "little") + (0).to_bytes(28, "little")
    assert is_mysql_ssl_request(ssl_request)
    assert not is_mysql_ssl_request((1).to_bytes(32, "little"))
    assert not is_redis_auth_write([b"EVAL", b"return 1", b"1", b"rate_limit:user"])
    assert is_redis_auth_write(
        [b"EVAL", b"return 1", b"1", b"refresh_jti:42", b"old", b"new"]
    )
    assert is_redis_auth_write(
        [b"SET", b"refresh_jti:42", b"sid:jti", b"EX", b"10"]
    )

    commit_payload = b"\x03COMMIT"
    mysql_frame = (
        len(commit_payload).to_bytes(3, byteorder="little")
        + b"\x00"
        + commit_payload
    )
    mysql_size, mysql_packets = extract_mysql_packets(bytearray(mysql_frame))
    assert mysql_size == len(mysql_frame)
    assert len(mysql_packets) == 1 and is_mysql_commit(mysql_packets[0])

    redis_command = (
        b"*4\r\n$3\r\nSET\r\n$14\r\nrefresh_jti:42\r\n"
        b"$7\r\nsid:jti\r\n$2\r\nEX\r\n"
    )
    redis_size, commands = extract_resp_commands(bytearray(redis_command))
    assert redis_size == len(redis_command)
    assert len(commands) == 1 and is_redis_auth_write(commands[0])
    redis_reply = b":1\r\n"
    reply_size, replies = extract_resp_frames(bytearray(redis_reply))
    assert reply_size == len(redis_reply) and replies == [redis_reply]


def test_mysql_proxy_observes_commit_then_drops_server_ack_and_closes_stream():
    def mysql_frame(payload: bytes, sequence: int) -> bytes:
        return len(payload).to_bytes(3, "little") + bytes([sequence]) + payload

    def recv_frame(sock: socket.socket) -> bytes:
        header = bytearray()
        while len(header) < 4:
            chunk = sock.recv(4 - len(header))
            if not chunk:
                raise AssertionError("fake MySQL peer closed before a full packet header")
            header.extend(chunk)
        payload_size = int.from_bytes(header[:3], "little")
        payload = bytearray()
        while len(payload) < payload_size:
            chunk = sock.recv(payload_size - len(payload))
            if not chunk:
                raise AssertionError("fake MySQL peer closed before a full packet payload")
            payload.extend(chunk)
        return bytes(header + payload)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    server.settimeout(3.0)
    upstream_port = server.getsockname()[1]
    server_error: list[BaseException] = []
    observed_commands: list[bytes] = []

    def fake_mysql_server() -> None:
        try:
            peer, _ = server.accept()
            with peer:
                peer.settimeout(3.0)
                recv_frame(peer)  # The first client packet is treated as handshake data.
                peer.sendall(mysql_frame(b"\x00\x00\x00\x02\x00\x00\x00", 2))
                observed_commands.append(recv_frame(peer)[4:])
                peer.sendall(mysql_frame(b"\x00\x00\x00\x02\x00\x00\x00", 1))
        except BaseException as error:
            server_error.append(error)

    server_thread = threading.Thread(
        target=fake_mysql_server,
        name="iter21-test-fake-mysql",
        daemon=False,
    )
    server_thread.start()
    proxy = TransparentFaultProxy("mysql", "127.0.0.1", upstream_port).start()
    client: Optional[socket.socket] = None
    try:
        proxy.arm("mysql.commit", "drop")
        client = socket.create_connection((proxy.host, proxy.port), timeout=3.0)
        client.settimeout(3.0)
        client.sendall(mysql_frame(b"\x00" * 32, 1))
        assert recv_frame(client)[4:] == b"\x00\x00\x00\x02\x00\x00\x00"
        client.sendall(mysql_frame(b"\x03COMMIT", 0))
        assert client.recv(1) == b""
        server_thread.join(timeout=3.0)
        assert not server_thread.is_alive()
        assert not server_error
        assert observed_commands == [b"\x03COMMIT"]
        metrics = proxy.snapshot()
        assert metrics["matched"] == 1
        assert metrics["replies_dropped"] == 1
        assert metrics["dropped_connection_closes"] == 1
        assert metrics["mysql_query_packets"] == 1
        assert metrics["mysql_commit_query_packets"] == 1
        assert metrics["mysql_command_codes"] == {"0x03": 1}
        assert metrics["protocol_gaps"] == 0
    finally:
        if client is not None:
            client.close()
        proxy.stop()
        server.close()
        server_thread.join(timeout=3.0)
        assert not server_thread.is_alive()


def test_proxy_metric_reset_retains_lifetime_transport_diagnostics():
    proxy = TransparentFaultProxy("mysql", "127.0.0.1", 3306)
    proxy._add_metric("accepted_connections")
    proxy._add_metric("mysql_handshake_packets")
    proxy._add_metric("mysql_tls_connections")
    proxy._add_metric("protocol_gaps")

    proxy.reset_metrics()
    metrics = proxy.snapshot()

    assert metrics["accepted_connections"] == 0
    assert metrics["protocol_gaps"] == 0
    assert metrics["lifetime"]["accepted_connections"] == 1
    assert metrics["lifetime"]["mysql_handshake_packets"] == 1
    assert metrics["lifetime"]["mysql_tls_connections"] == 1
    assert metrics["lifetime"]["protocol_gaps"] == 1


@pytest.mark.fault_injection
def test_redis_login_set_reply_drop_returns_503_after_session_is_persisted(fault_backend):
    credentials = _register_via_main_service()
    captcha_id, captcha_code = _challenge_at(fault_backend.base_url)
    fault_backend.mysql_proxy.reset_metrics()
    fault_backend.redis_proxy.reset_metrics()
    fault_backend.redis_proxy.arm("redis.login_set", "drop")
    log_offset = fault_backend.completion_log_offset()
    completion_events = []
    try:
        started = time.monotonic()
        response = requests.post(
            f"{fault_backend.base_url}/api/auth/login",
            json={
                "username": credentials.username,
                "password": credentials.password,
                "captcha_id": captcha_id,
                "captcha_code": captcha_code,
            },
            timeout=TEST_TIMEOUT_SECONDS,
        )
        elapsed = time.monotonic() - started
        try:
            body = response.json()
        except ValueError:
            pytest.fail("Redis write timeout did not return a JSON error envelope")

        redis_metrics = fault_backend.redis_proxy.snapshot()
        if (
            redis_metrics["matched"] != 1
            or redis_metrics["replies_dropped"] != 1
            or redis_metrics["dropped_connection_closes"] != 1
            or redis_metrics["protocol_gaps"]
        ):
            pytest.fail(
                "Redis SET ACK drop did not trigger once before HTTP evaluation: "
                f"{json.dumps(redis_metrics, sort_keys=True)}"
            )
        if response.status_code != 503 or not isinstance(body, dict) or body.get("code") != 503:
            pytest.fail("login did not return HTTP 503 after its real Redis ACK was dropped")
        if elapsed > 3.0:
            pytest.fail("login did not finish within the bounded Redis failure deadline")
        completion = _wait_for_auth_redis_completion(
            fault_backend, log_offset, "login", "exception"
        )
        completion_events = [completion]
        value, ttl = _redis_session(credentials.user_id)
        if SESSION_VALUE.fullmatch(value) is None or ttl <= 0:
            pytest.fail("independent Redis read did not find the committed login session")
    finally:
        _record_fault_evidence(
            "redis-login-set-drop",
            fault_backend.mysql_proxy,
            fault_backend.redis_proxy,
            _auth_completion_evidence_snapshot(
                fault_backend, log_offset, completion_events
            ),
        )


@pytest.mark.fault_injection
def test_redis_login_delayed_set_ack_completes_once_before_late_ack(fault_backend):
    credentials = _register_via_main_service()
    captcha_id, captcha_code = _challenge_at(fault_backend.base_url)
    fault_backend.mysql_proxy.reset_metrics()
    fault_backend.redis_proxy.reset_metrics()
    fault_backend.redis_proxy.arm(
        "redis.login_set", "delay", delay_seconds=REDIS_REPLY_DELAY_SECONDS
    )
    log_offset = fault_backend.completion_log_offset()
    completion_events = []
    sock: Optional[socket.socket] = None
    try:
        started = time.monotonic()
        sock, status, body = _send_raw_json_request(
            fault_backend.base_url,
            "/api/auth/login",
            {
                "username": credentials.username,
                "password": credentials.password,
                "captcha_id": captcha_id,
                "captcha_code": captcha_code,
            },
        )
        elapsed = time.monotonic() - started
        initial_metrics = fault_backend.redis_proxy.snapshot()
        if (
            initial_metrics["matched"] != 1
            or initial_metrics["replies_delayed"] != 1
            or initial_metrics["delayed_replies_forwarded"] != 0
            or initial_metrics["protocol_gaps"]
        ):
            pytest.fail(
                "Redis login SET ACK was not held before HTTP evaluation: "
                f"{json.dumps(initial_metrics, sort_keys=True)}"
            )
        if status != 503 or body.get("code") != 503:
            pytest.fail("login did not return HTTP 503 before its delayed Redis ACK")
        if elapsed > 3.0:
            pytest.fail("login did not finish within the bounded Redis failure deadline")
        completion = _wait_for_auth_redis_completion(
            fault_backend, log_offset, "login", "exception"
        )
        completion_events = [completion]

        _wait_for_delayed_redis_ack(fault_backend)
        metrics = fault_backend.redis_proxy.snapshot()
        if (
            metrics["matched"] != 1
            or metrics["replies_delayed"] != 1
            or metrics["delayed_replies_forwarded"] != 1
            or metrics["protocol_gaps"]
        ):
            pytest.fail("Redis login SET ACK did not arrive late through the supported protocol")
        value, ttl = _redis_session(credentials.user_id)
        if SESSION_VALUE.fullmatch(value) is None or ttl <= 0:
            pytest.fail("independent Redis read did not find the committed login session")
        _require_unchanged_auth_redis_completion(
            fault_backend, log_offset, completion
        )
        _assert_no_second_http_response(sock)
    finally:
        if sock is not None:
            sock.close()
        _record_fault_evidence(
            "redis-login-set-delay",
            fault_backend.mysql_proxy,
            fault_backend.redis_proxy,
            _auth_completion_evidence_snapshot(
                fault_backend, log_offset, completion_events
            ),
        )


@pytest.mark.fault_injection
def test_redis_refresh_delayed_eval_ack_times_out_without_second_http_success(fault_backend):
    credentials = _register_via_main_service()
    session = _login_at(fault_backend.base_url, credentials)
    old_token = session["refresh_token"]
    old_claims = _jwt_claims(old_token)
    old_sid = old_claims.get("sid")
    old_jti = old_claims.get("jti")
    old_value, old_ttl = _redis_session(credentials.user_id)
    if (
        not isinstance(old_sid, str)
        or not isinstance(old_jti, str)
        or old_value != f"{old_sid}:{old_jti}"
        or old_ttl <= 0
    ):
        pytest.fail("independent Redis read did not confirm the baseline login session")

    fault_backend.mysql_proxy.reset_metrics()
    fault_backend.redis_proxy.reset_metrics()
    fault_backend.redis_proxy.arm(
        "redis.refresh_eval", "delay", delay_seconds=REDIS_REPLY_DELAY_SECONDS
    )
    log_offset = fault_backend.completion_log_offset()
    completion_events = []
    started = time.monotonic()
    sock: Optional[socket.socket] = None
    try:
        sock, status, body = _send_raw_refresh(fault_backend.base_url, old_token)
        elapsed = time.monotonic() - started
        initial_metrics = fault_backend.redis_proxy.snapshot()
        if (
            initial_metrics["matched"] != 1
            or initial_metrics["replies_delayed"] != 1
            or initial_metrics["delayed_replies_forwarded"] != 0
            or initial_metrics["protocol_gaps"]
        ):
            pytest.fail(
                "Redis refresh rotation did not reach a supported proxy matcher before "
                f"HTTP evaluation: {json.dumps(initial_metrics, sort_keys=True)}"
            )
        if status != 503 or body.get("code") != 503:
            pytest.fail("refresh did not return HTTP 503 before its delayed Redis ACK")
        if elapsed > 3.0:
            pytest.fail("refresh did not finish within the bounded Redis failure deadline")
        completion = _wait_for_auth_redis_completion(
            fault_backend, log_offset, "refresh", "exception"
        )
        completion_events = [completion]

        _wait_for_delayed_redis_ack(fault_backend)
        metrics = fault_backend.redis_proxy.snapshot()
        if (
            metrics["matched"] != 1
            or metrics["replies_delayed"] != 1
            or metrics["delayed_replies_forwarded"] != 1
            or metrics["protocol_gaps"]
        ):
            pytest.fail("Redis rotation ACK did not arrive late through the supported protocol")

        new_value, new_ttl = _redis_session(credentials.user_id)
        if (
            SESSION_VALUE.fullmatch(new_value) is None
            or new_value.split(":", 1)[0] != old_sid
            or new_value.split(":", 1)[1] == old_jti
            or new_ttl <= 0
        ):
            pytest.fail("independent Redis read did not confirm the completed session rotation")

        _require_unchanged_auth_redis_completion(
            fault_backend, log_offset, completion
        )
        _assert_no_second_http_response(sock)

        replay = requests.post(
            f"{fault_backend.base_url}/api/auth/refresh",
            json={"refresh_token": old_token},
            timeout=5,
        )
        if replay.status_code != 401:
            pytest.fail("old refresh token remained valid after the delayed rotation completed")
    finally:
        if sock is not None:
            sock.close()
        _record_fault_evidence(
            "redis-refresh-eval-delay",
            fault_backend.mysql_proxy,
            fault_backend.redis_proxy,
            _auth_completion_evidence_snapshot(
                fault_backend, log_offset, completion_events
            ),
        )


@pytest.mark.fault_injection
def test_redis_logout_delayed_eval_ack_completes_once_before_late_ack(fault_backend):
    credentials = _register_via_main_service()
    session = _login_at(fault_backend.base_url, credentials)
    refresh_token = session["refresh_token"]
    claims = _jwt_claims(refresh_token)
    session_value, session_ttl = _redis_session(credentials.user_id)
    if (
        session_value != f"{claims.get('sid')}:{claims.get('jti')}"
        or session_ttl <= 0
    ):
        pytest.fail("independent Redis read did not confirm the baseline logout session")

    fault_backend.mysql_proxy.reset_metrics()
    fault_backend.redis_proxy.reset_metrics()
    # The wire proxy classifies all authentication EVAL writes as
    # redis.refresh_eval; the command still exercises the logout Lua script.
    fault_backend.redis_proxy.arm(
        "redis.refresh_eval", "delay", delay_seconds=REDIS_REPLY_DELAY_SECONDS
    )
    log_offset = fault_backend.completion_log_offset()
    completion_events = []
    sock: Optional[socket.socket] = None
    try:
        started = time.monotonic()
        sock, status, body = _send_raw_json_request(
            fault_backend.base_url,
            "/api/auth/logout",
            {"refresh_token": refresh_token},
        )
        elapsed = time.monotonic() - started
        initial_metrics = fault_backend.redis_proxy.snapshot()
        if (
            initial_metrics["matched"] != 1
            or initial_metrics["replies_delayed"] != 1
            or initial_metrics["delayed_replies_forwarded"] != 0
            or initial_metrics["protocol_gaps"]
        ):
            pytest.fail(
                "Redis logout EVAL ACK was not held before HTTP evaluation: "
                f"{json.dumps(initial_metrics, sort_keys=True)}"
            )
        if status != 503 or body.get("code") != 503:
            pytest.fail("logout did not return HTTP 503 before its delayed Redis ACK")
        if elapsed > 3.0:
            pytest.fail("logout did not finish within the bounded Redis failure deadline")
        completion = _wait_for_auth_redis_completion(
            fault_backend, log_offset, "logout", "exception"
        )
        completion_events = [completion]

        _wait_for_delayed_redis_ack(fault_backend)
        metrics = fault_backend.redis_proxy.snapshot()
        if (
            metrics["matched"] != 1
            or metrics["replies_delayed"] != 1
            or metrics["delayed_replies_forwarded"] != 1
            or metrics["protocol_gaps"]
        ):
            pytest.fail("Redis logout EVAL ACK did not arrive late through the supported protocol")
        if _docker_cli(
            "redis", ["redis-cli", "--raw", "GET", f"refresh_jti:{credentials.user_id}"]
        ):
            pytest.fail("independent Redis read found a session after the logout EVAL completed")
        _require_unchanged_auth_redis_completion(
            fault_backend, log_offset, completion
        )
        _assert_no_second_http_response(sock)

        replay = requests.post(
            f"{fault_backend.base_url}/api/auth/refresh",
            json={"refresh_token": refresh_token},
            timeout=5,
        )
        if replay.status_code != 401:
            pytest.fail("logout did not revoke the old refresh token after its delayed EVAL")
    finally:
        if sock is not None:
            sock.close()
        _record_fault_evidence(
            "redis-logout-eval-delay",
            fault_backend.mysql_proxy,
            fault_backend.redis_proxy,
            _auth_completion_evidence_snapshot(
                fault_backend, log_offset, completion_events
            ),
        )


@pytest.mark.fault_injection
def test_mysql_commit_ack_drop_returns_unknown_with_parent_and_child_rows_persisted(fault_backend):
    credentials = _new_unregistered_credentials()
    fault_backend.mysql_proxy.reset_metrics()
    fault_backend.redis_proxy.reset_metrics()
    _require_mysql_fault_observable(fault_backend.mysql_proxy)
    fault_backend.mysql_proxy.arm("mysql.commit", "drop")
    try:
        started = time.monotonic()
        response = requests.post(
            f"{fault_backend.base_url}/api/auth/register",
            json={
                "username": credentials.username,
                "password": credentials.password,
                "nickname": "Iter21 transport fault",
            },
            timeout=TEST_TIMEOUT_SECONDS,
        )
        elapsed = time.monotonic() - started
        mysql_metrics = fault_backend.mysql_proxy.snapshot()
        if (
            mysql_metrics["matched"] != 1
            or mysql_metrics["replies_dropped"] != 1
            or mysql_metrics["dropped_connection_closes"] != 1
            or mysql_metrics["protocol_gaps"]
        ):
            pytest.fail(
                "MySQL COMMIT ACK drop did not trigger once before HTTP evaluation: "
                f"{json.dumps(mysql_metrics, sort_keys=True)}"
            )
        try:
            body = response.json()
        except ValueError:
            pytest.fail("commit ACK loss did not return a JSON error envelope")

        if (
            response.status_code != 503
            or not isinstance(body, dict)
            or body.get("code") != 503
            or body.get("error_code") != "WRITE_OUTCOME_UNKNOWN"
            or not isinstance(body.get("request_id"), str)
            or not body.get("request_id")
        ):
            pytest.fail("registration did not report WRITE_OUTCOME_UNKNOWN after commit ACK loss")
        if elapsed > 3.5:
            pytest.fail("registration did not return within the transaction outcome deadline")
        database = _required_env("WN_I21_DB_NAME")
        escaped_username = credentials.username.replace("'", "''")
        query = (
            "SELECT u.userid, u.credit, COUNT(c.creditid), COALESCE(SUM(c.credit), 0) "
            "FROM users AS u LEFT JOIN credit AS c ON c.userid = u.userid "
            f"WHERE u.username = '{escaped_username}' GROUP BY u.userid, u.credit"
        )
        rows = _docker_cli(
            "mysql",
            [
                "mysql",
                "--batch",
                "--raw",
                "--skip-column-names",
                "--default-character-set=utf8mb4",
                "-uroot",
                database,
                "-e",
                query,
            ],
        )
        fields = rows.split("\t") if rows else []
        if len(fields) != 4:
            pytest.fail("independent MySQL connection did not find the committed user and credit row")
        try:
            user_id, user_credit, child_count, child_credit = (int(value) for value in fields)
        except ValueError:
            pytest.fail("independent MySQL verification returned invalid persisted values")
        if user_id <= 0 or user_credit != 50 or child_count != 1 or child_credit != 50:
            pytest.fail("registration parent and initial-credit child rows are not fully persisted")
    finally:
        _record_fault_evidence(
            "mysql-commit-ack-drop", fault_backend.mysql_proxy, fault_backend.redis_proxy
        )


@pytest.mark.fault_injection
def test_mysql_begin_ack_drop_returns_unavailable_without_registration_rows(fault_backend):
    credentials = _new_unregistered_credentials()
    fault_backend.mysql_proxy.reset_metrics()
    fault_backend.redis_proxy.reset_metrics()
    _require_mysql_fault_observable(fault_backend.mysql_proxy)
    fault_backend.mysql_proxy.arm("mysql.begin", "drop")
    try:
        started = time.monotonic()
        response = requests.post(
            f"{fault_backend.base_url}/api/auth/register",
            json={
                "username": credentials.username,
                "password": credentials.password,
                "nickname": "Iter21 acquisition failure",
            },
            timeout=TEST_TIMEOUT_SECONDS,
        )
        elapsed = time.monotonic() - started
        metrics = fault_backend.mysql_proxy.snapshot()
        if (
            metrics["matched"] != 1
            or metrics["replies_dropped"] != 1
            or metrics["dropped_connection_closes"] != 1
            or metrics["mysql_transaction_begin_packets"] != 1
            or metrics["protocol_gaps"]
        ):
            pytest.fail(
                "MySQL transaction-begin acknowledgement fault did not trigger once: "
                f"{json.dumps(metrics, sort_keys=True)}"
            )
        try:
            body = response.json()
        except ValueError:
            pytest.fail("transaction acquisition failure did not return a JSON error envelope")
        if (
            response.status_code != 503
            or not isinstance(body, dict)
            or body.get("code") != 503
            or body.get("error_code") == "WRITE_OUTCOME_UNKNOWN"
        ):
            pytest.fail("transaction acquisition failure was not reported as known unavailable")
        if elapsed > 3.5:
            pytest.fail("transaction acquisition failure exceeded the bounded response deadline")

        connection = owned_mysql_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM users WHERE username = %s",
                    (credentials.username,),
                )
                user_rows = cursor.fetchone()[0]
                cursor.execute(
                    "SELECT COUNT(*) FROM credit c JOIN users u ON u.userid = c.userid "
                    "WHERE u.username = %s",
                    (credentials.username,),
                )
                credit_rows = cursor.fetchone()[0]
        finally:
            connection.close()
        if (user_rows, credit_rows) != (0, 0):
            pytest.fail("registration wrote rows despite transaction acquisition failure")
    finally:
        _record_fault_evidence(
            "mysql-transaction-begin-ack-drop",
            fault_backend.mysql_proxy,
            fault_backend.redis_proxy,
        )


def _send_raw_refresh(base_url: str, refresh_token: str) -> tuple[socket.socket, int, dict]:
    return _send_raw_json_request(
        base_url,
        "/api/auth/refresh",
        {"refresh_token": refresh_token},
    )


def _send_raw_json_request(
    base_url: str, path: str, payload_value: dict
) -> tuple[socket.socket, int, dict]:
    parsed = urlsplit(base_url)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.port is None:
        pytest.fail("secondary backend URL is not a loopback HTTP listener")
    sock = socket.create_connection((parsed.hostname, parsed.port), timeout=5)
    sock.settimeout(TEST_TIMEOUT_SECONDS)
    payload = json.dumps(payload_value, separators=(",", ":")).encode()
    request = (
        f"POST {path} HTTP/1.1\r\n"
        f"Host: {parsed.hostname}:{parsed.port}\r\n"
        "Content-Type: application/json\r\n"
        "Connection: keep-alive\r\n"
        f"Content-Length: {len(payload)}\r\n\r\n"
    ).encode("ascii") + payload
    sock.sendall(request)
    header_bytes = bytearray()
    while not header_bytes.endswith(b"\r\n\r\n"):
        chunk = sock.recv(1)
        if not chunk:
            sock.close()
            pytest.fail("secondary backend closed before returning the HTTP result")
        header_bytes.extend(chunk)
        if len(header_bytes) > 65536:
            sock.close()
            pytest.fail("secondary backend returned oversized HTTP headers")
    lines = bytes(header_bytes).decode("iso-8859-1").split("\r\n")
    try:
        status = int(lines[0].split(" ", 2)[1])
    except (IndexError, ValueError):
        sock.close()
        pytest.fail("secondary backend returned an invalid HTTP status line")
    headers = {}
    for line in lines[1:]:
        if ":" in line:
            name, value = line.split(":", 1)
            headers[name.strip().casefold()] = value.strip()
    if "content-length" not in headers:
        sock.close()
        pytest.fail("secondary backend response omitted Content-Length")
    try:
        remaining = int(headers["content-length"])
    except ValueError:
        sock.close()
        pytest.fail("secondary backend returned invalid Content-Length")
    body_bytes = bytearray()
    while len(body_bytes) < remaining:
        chunk = sock.recv(remaining - len(body_bytes))
        if not chunk:
            sock.close()
            pytest.fail("secondary backend closed before completing its HTTP body")
        body_bytes.extend(chunk)
    try:
        body = json.loads(body_bytes)
    except (ValueError, json.JSONDecodeError):
        sock.close()
        pytest.fail("secondary backend returned an invalid error envelope")
    if not isinstance(body, dict):
        sock.close()
        pytest.fail("secondary backend response was not a JSON object")
    return sock, status, body
