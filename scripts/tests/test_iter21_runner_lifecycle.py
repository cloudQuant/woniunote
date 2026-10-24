"""Bounded two-run TERM/isolation check for the Iteration 21 harness.

Run only against an explicitly frozen checkout and backend executable. The
driver starts the normal disposable-service runner twice, holds its tracked
pytest child at a private marker, then sends TERM only to each runner main PID.
The driver never signals or removes a child, container, volume, or file.

Invoke through the user's Anaconda base environment, for example:
conda run -n base python scripts/tests/test_iter21_runner_lifecycle.py
  --repo /absolute/frozen/checkout
  --backend-bin /absolute/frozen/backend
  --artifact-root /absolute/new/evidence-root
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import re
import shlex
import signal
import socket
import stat
import struct
import subprocess
import sys
import time
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


RUN_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}$")
CONTAINER_ID_RE = re.compile(r"^[0-9a-f]{64}$")
RESERVED_PORTS = {80, 443, 3306, 6379, 5173, 8888}
RUN_LABEL = "org.woniunote.iter21.run-id"
SERVICE_LABEL = "org.woniunote.iter21.service"
INSTANCE_LABEL = "org.woniunote.iter21.instance"
STARTUP_TIMEOUT = 300.0
STOP_TIMEOUT = 35.0
GATE_TIMEOUT_TENTHS = 4200


class LifecycleFailure(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass
class ProcessInfo:
    pid: int
    ppid: int
    started: str
    command: str


@dataclass
class RunState:
    slot: str
    temp_root: Path
    result_root: Path
    gate_path: Path
    gate_ready: Path
    gate_release: Path
    log_path: Path
    process: subprocess.Popen[bytes] | None = None
    log_stream: Any = None
    run_id: str = ""
    run_dir: Path | None = None
    config_path: Path | None = None
    config: dict[str, Any] = field(default_factory=dict, repr=False)
    base_url: str = ""
    ports: dict[str, int] = field(default_factory=dict)
    container_ids: dict[str, str] = field(default_factory=dict)
    volume_name: str = ""
    mysql_sentinel: str = ""
    redis_key: str = ""
    redis_sentinel: str = ""
    authenticated_user: Any = field(default=None, repr=False)
    upload_records: list[dict[str, str]] = field(default_factory=list)
    term_sent: bool = False
    term_returncode: int | None = None
    term_elapsed: float | None = None
    descendants_before_term: list[ProcessInfo] = field(default_factory=list, repr=False)
    resource_snapshot: dict[str, Any] = field(default_factory=dict, repr=False)


def _run(args: list[str], *, timeout: float = 8.0, check: bool = True) -> str:
    try:
        completed = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LifecycleFailure("bounded_command_failed") from exc
    if check and completed.returncode != 0:
        raise LifecycleFailure("bounded_command_failed")
    return completed.stdout


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _mkdir_private(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=False)
    os.chmod(path, 0o700)


def _check_private(path: Path, *, directory: bool) -> None:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise LifecycleFailure("owned_path_unavailable") from exc
    correct_kind = stat.S_ISDIR(metadata.st_mode) if directory else stat.S_ISREG(metadata.st_mode)
    if not correct_kind or stat.S_IMODE(metadata.st_mode) & 0o077:
        raise LifecycleFailure("owned_path_permissions_invalid")
    if metadata.st_uid != os.geteuid():
        raise LifecycleFailure("owned_path_owner_invalid")


def _docker_context_is_local() -> str:
    docker_host = os.environ.get("DOCKER_HOST", "")
    if docker_host and not docker_host.startswith("unix://"):
        raise LifecycleFailure("non_local_docker_host_refused")
    context = _run(["docker", "context", "show"]).strip()
    if not context:
        raise LifecycleFailure("docker_context_unavailable")
    host = _run(
        ["docker", "context", "inspect", context, "--format", "{{.Endpoints.docker.Host}}"]
    ).strip()
    if not (docker_host or host).startswith("unix://"):
        raise LifecycleFailure("non_local_docker_context_refused")
    _run(["docker", "info"], timeout=15.0)
    return context


def _new_artifact_root(value: str) -> Path:
    requested = Path(value).expanduser()
    if not requested.is_absolute():
        raise LifecycleFailure("artifact_root_must_be_absolute")
    root = requested.resolve(strict=False)
    if root.exists():
        raise LifecycleFailure("artifact_root_already_exists")
    previous_umask = os.umask(0o077)
    try:
        root.mkdir(mode=0o700, parents=True, exist_ok=False)
    finally:
        os.umask(previous_umask)
    os.chmod(root, 0o700)
    for name in ("raw", "safe", "control", "runtime"):
        _mkdir_private(root / name)
    return root


def _create_gate(script_path: Path, ready_path: Path, release_path: Path) -> None:
    if any(character.isspace() for character in str(script_path)):
        raise LifecycleFailure("artifact_path_whitespace_not_supported_by_runner")
    script = "\n".join(
        [
            "#!/bin/sh",
            "set -eu",
            f": > {shlex.quote(str(ready_path))}",
            "i=0",
            f"while [ ! -e {shlex.quote(str(release_path))} ]; do",
            "  i=$((i + 1))",
            f'  [ "$i" -lt {GATE_TIMEOUT_TENTHS} ] || exit 124',
            "  sleep 0.1",
            "done",
            "",
        ]
    )
    descriptor = os.open(script_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(script)
    os.chmod(script_path, 0o700)


def _runner_env(base_env: dict[str, str], run: RunState, backend: Path) -> dict[str, str]:
    allowed = (
        "PATH",
        "HOME",
        "LANG",
        "LC_ALL",
        "DOCKER_HOST",
        "DOCKER_CONTEXT",
        "DOCKER_CONFIG",
        "DYLD_LIBRARY_PATH",
        "LD_LIBRARY_PATH",
    )
    env = {key: base_env[key] for key in allowed if key in base_env}
    env["NO_PROXY"] = "127.0.0.1,localhost"
    env["no_proxy"] = env["NO_PROXY"]
    env["TMPDIR"] = str(run.temp_root)
    env["WONIUNOTE_BACKEND_BIN"] = str(backend)
    env["WONIUNOTE_TEST_ARTIFACT_ROOT"] = str(run.result_root)
    env["WONIUNOTE_TEST_REAL_E2E"] = "0"
    # Keep the private config present through the observation window. TERM
    # still follows the normal failure cleanup path and deletes it.
    env["WONIUNOTE_TEST_KEEP_SERVICES"] = "1"
    env["WONIUNOTE_TEST_STRICT"] = "1"
    env["WONIUNOTE_TEST_SCENARIO"] = "functional"
    env["PYTEST_CMD"] = str(run.gate_path)
    if Path(env["TMPDIR"]).resolve() != run.temp_root.resolve():
        raise LifecycleFailure("run_temp_root_mismatch")
    return env


def _start_runner(run: RunState, runner: Path, repo: Path, backend: Path, base_env: dict[str, str]) -> None:
    _mkdir_private(run.temp_root)
    _mkdir_private(run.result_root)
    _create_gate(run.gate_path, run.gate_ready, run.gate_release)
    descriptor = os.open(run.log_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    run.log_stream = os.fdopen(descriptor, "wb", buffering=0)
    try:
        run.process = subprocess.Popen(
            ["bash", str(runner)],
            cwd=repo,
            env=_runner_env(base_env, run, backend),
            stdin=subprocess.DEVNULL,
            stdout=run.log_stream,
            stderr=subprocess.STDOUT,
            close_fds=True,
        )
    except OSError as exc:
        run.log_stream.close()
        run.log_stream = None
        raise LifecycleFailure("runner_start_failed") from exc


def _load_config(run: RunState) -> bool:
    run_root = run.temp_root / "woniunote-iter21"
    if not run_root.is_dir() or run_root.is_symlink():
        return False
    _check_private(run_root, directory=True)
    candidates = [item for item in run_root.iterdir() if item.is_dir()]
    if not candidates:
        return False
    if len(candidates) != 1 or not RUN_ID_RE.fullmatch(candidates[0].name):
        raise LifecycleFailure("unexpected_runtime_directory_layout")
    run_dir = candidates[0]
    _check_private(run_dir, directory=True)
    if run_dir.resolve(strict=True) != run_dir.resolve(strict=False):
        raise LifecycleFailure("runtime_path_not_canonical")
    for name in ("uploads", "backend-runtime", "logs", "evidence"):
        child = run_dir / name
        if not child.is_dir() or child.is_symlink():
            return False
        _check_private(child, directory=True)
    config_path = run_dir / "config.integration.json"
    if not config_path.exists():
        return False
    if config_path.is_symlink():
        raise LifecycleFailure("config_path_is_symlink")
    _check_private(config_path, directory=False)
    if stat.S_IMODE(config_path.stat().st_mode) != 0o600:
        raise LifecycleFailure("config_permissions_invalid")
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LifecycleFailure("config_invalid") from exc
    if not isinstance(config, dict):
        raise LifecycleFailure("config_invalid")
    run_id = run_dir.name
    if (config.get("custom_config") or {}).get("test_run_id") != run_id:
        raise LifecycleFailure("config_run_identity_mismatch")
    listeners = config.get("listeners")
    databases = config.get("db_clients")
    redis_clients = config.get("redis_clients")
    if not (isinstance(listeners, list) and len(listeners) == 1):
        raise LifecycleFailure("listener_config_invalid")
    if not (isinstance(databases, list) and len(databases) == 1):
        raise LifecycleFailure("mysql_config_invalid")
    if not (isinstance(redis_clients, list) and len(redis_clients) == 1):
        raise LifecycleFailure("redis_config_invalid")
    listener, db, redis_config = listeners[0], databases[0], redis_clients[0]
    if listener.get("address") != "127.0.0.1" or listener.get("https") is not False:
        raise LifecycleFailure("http_listener_not_loopback")
    if db.get("host") != "127.0.0.1" or redis_config.get("host") != "127.0.0.1":
        raise LifecycleFailure("service_endpoint_not_loopback")
    try:
        ports = {
            "http": int(listener["port"]),
            "mysql": int(db["port"]),
            "redis": int(redis_config["port"]),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise LifecycleFailure("port_config_invalid") from exc
    if len(set(ports.values())) != 3:
        raise LifecycleFailure("run_ports_not_distinct")
    if any(port < 1024 or port > 65535 or port in RESERVED_PORTS for port in ports.values()):
        raise LifecycleFailure("reserved_or_invalid_port_refused")
    if db.get("dbname") != f"woniunote_test_{run_id.replace('-', '')}" or db.get("user") != "root":
        raise LifecycleFailure("database_identity_mismatch")
    app = config.get("app") or {}
    if Path(app.get("document_root", "")) != run_dir / "uploads":
        raise LifecycleFailure("document_root_not_run_owned")
    if Path(app.get("upload_path", "")) != run_dir / "uploads" / "uploads":
        raise LifecycleFailure("upload_path_not_nested_run_owned")

    run.run_id = run_id
    run.run_dir = run_dir
    run.config_path = config_path
    run.config = config
    run.ports = ports
    run.base_url = f"http://127.0.0.1:{ports['http']}"
    return True


def _docker_container_info(container_id: str) -> dict[str, Any]:
    identity = _run(
        [
            "docker",
            "inspect",
            "--format",
            f'{{{{.Id}}}}|{{{{.Name}}}}|{{{{.State.Status}}}}|'
            f'{{{{index .Config.Labels "{RUN_LABEL}"}}}}|'
            f'{{{{index .Config.Labels "{SERVICE_LABEL}"}}}}|'
            f'{{{{index .Config.Labels "{INSTANCE_LABEL}"}}}}',
            container_id,
        ]
    ).strip()
    fields = identity.split("|")
    if len(fields) != 6 or fields[0] != container_id:
        raise LifecycleFailure("docker_container_identity_mismatch")
    return {
        "Id": fields[0],
        "Name": fields[1],
        "State": {"Status": fields[2]},
        "Config": {
            "Labels": {
                RUN_LABEL: fields[3],
                SERVICE_LABEL: fields[4],
                INSTANCE_LABEL: "" if fields[5] == "<no value>" else fields[5],
            }
        },
        "Mounts": _container_mounts(container_id),
    }


def _container_mounts(container_id: str) -> list[dict[str, str]]:
    raw = _run(["docker", "inspect", "--format", "{{json .Mounts}}", container_id])
    try:
        mounts = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LifecycleFailure("docker_mount_metadata_invalid") from exc
    if not isinstance(mounts, list):
        raise LifecycleFailure("docker_mount_metadata_invalid")
    return mounts


def _owned_container_ids(run_id: str) -> list[str]:
    output = _run(
        ["docker", "ps", "-aq", "--no-trunc", "--filter", f"label={RUN_LABEL}={run_id}"]
    )
    ids = [line.strip() for line in output.splitlines() if line.strip()]
    if any(not CONTAINER_ID_RE.fullmatch(container_id) for container_id in ids):
        raise LifecycleFailure("short_or_invalid_container_id")
    return ids


def _owned_volume_names(run_id: str) -> list[str]:
    output = _run(["docker", "volume", "ls", "-q", "--filter", f"label={RUN_LABEL}={run_id}"])
    return [line.strip() for line in output.splitlines() if line.strip()]


def _container_identity(info: dict[str, Any]) -> tuple[str, str, str, str, str]:
    labels = (info.get("Config") or {}).get("Labels") or {}
    return (
        str(info.get("Id", "")),
        str(info.get("Name", "")),
        str(labels.get(RUN_LABEL, "")),
        str(labels.get(SERVICE_LABEL, "")),
        str(labels.get(INSTANCE_LABEL, "")),
    )


def _validate_port_mapping(container_id: str, exposed_port: int, host_port: int) -> None:
    output = _run(["docker", "port", container_id, f"{exposed_port}/tcp"])
    mappings = [line.strip() for line in output.splitlines() if line.strip()]
    if mappings != [f"127.0.0.1:{host_port}"]:
        raise LifecycleFailure("container_port_mapping_mismatch")


def _inspect_run_resources(run: RunState) -> dict[str, Any]:
    assert run.run_id and run.run_dir is not None
    ids = _owned_container_ids(run.run_id)
    expected_names = {
        "mysql": f"/woniunote-i21-{run.run_id}-mysql",
        "redis": f"/woniunote-i21-{run.run_id}-redis",
    }
    found: dict[str, tuple[str, dict[str, Any]]] = {}
    backend_ids: list[str] = []
    for container_id in ids:
        info = _docker_container_info(container_id)
        actual_id, name, actual_run, service, instance = _container_identity(info)
        if actual_id != container_id or actual_run != run.run_id:
            raise LifecycleFailure("container_run_identity_mismatch")
        if service in {"mysql", "redis"}:
            if name != expected_names[service] or instance:
                raise LifecycleFailure("service_container_identity_mismatch")
            if service in found:
                raise LifecycleFailure("duplicate_owned_service_container")
            if (info.get("State") or {}).get("Status") != "running":
                raise LifecycleFailure("owned_service_not_running")
            found[service] = (container_id, info)
        elif service == "backend":
            if name != f"/woniunote-i21-{run.run_id}-backend-{instance}" or instance != "primary":
                raise LifecycleFailure("unexpected_backend_container_identity")
            if (info.get("State") or {}).get("Status") != "running":
                raise LifecycleFailure("owned_backend_container_not_running")
            backend_ids.append(container_id)
        else:
            raise LifecycleFailure("unexpected_run_owned_container_service")
    if set(found) != {"mysql", "redis"} or len(backend_ids) > 1:
        raise LifecycleFailure("owned_service_set_incomplete")

    expected_volume = f"woniunote-i21-{run.run_id}-mysql-data"
    volume_names = _owned_volume_names(run.run_id)
    if volume_names != [expected_volume]:
        raise LifecycleFailure("owned_volume_set_mismatch")
    volume_output = _run(
        [
            "docker",
            "volume",
            "inspect",
            "--format",
            f'{{{{.Name}}}}|{{{{.Driver}}}}|{{{{index .Labels "{RUN_LABEL}"}}}}|'
            f'{{{{index .Labels "{SERVICE_LABEL}"}}}}',
            expected_volume,
        ]
    ).strip()
    if volume_output != f"{expected_volume}|local|{run.run_id}|mysql":
        raise LifecycleFailure("mysql_volume_identity_mismatch")
    mysql_id, mysql_info = found["mysql"]
    redis_id, _redis_info = found["redis"]
    _validate_port_mapping(mysql_id, 3306, run.ports["mysql"])
    _validate_port_mapping(redis_id, 6379, run.ports["redis"])
    if not any(
        mount.get("Type") == "volume"
        and mount.get("Name") == expected_volume
        and mount.get("Destination") == "/var/lib/mysql"
        for mount in mysql_info["Mounts"]
    ):
        raise LifecycleFailure("mysql_volume_mount_mismatch")
    backend_id = ""
    if backend_ids:
        backend_id = backend_ids[0]
        _validate_port_mapping(backend_id, run.ports["http"], run.ports["http"])
    run.container_ids = {"mysql": mysql_id, "redis": redis_id}
    if backend_id:
        run.container_ids["backend"] = backend_id
    run.volume_name = expected_volume
    return {
        "container_ids": dict(run.container_ids),
        "volume_name": expected_volume,
        "ports": dict(run.ports),
    }


def _assert_resources_removed(run: RunState) -> None:
    assert run.run_dir is not None
    if _owned_container_ids(run.run_id):
        raise LifecycleFailure("owned_containers_remain_after_term")
    if _owned_volume_names(run.run_id):
        raise LifecycleFailure("owned_volume_remains_after_term")
    for container_id in run.container_ids.values():
        try:
            completed = subprocess.run(
                ["docker", "inspect", container_id],
                capture_output=True,
                text=True,
                timeout=8.0,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise LifecycleFailure("container_removal_observation_failed") from exc
        if completed.returncode == 0:
            raise LifecycleFailure("previously_owned_container_id_still_exists")
        expected_missing = f"Error: No such object: {container_id}"
        if completed.stderr.strip() not in {expected_missing, expected_missing.removeprefix("Error: ")}:
            raise LifecycleFailure("container_removal_observation_failed")
    for path in (run.run_dir / "uploads", run.run_dir / "backend-runtime"):
        if path.exists() or path.is_symlink():
            raise LifecycleFailure("run_upload_or_backend_directory_remains")
    if any(_tcp_connects(port) for port in run.ports.values()):
        raise LifecycleFailure("run_loopback_listener_remains_after_term")


def _tcp_connects(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(0.25)
        return connection.connect_ex(("127.0.0.1", port)) == 0


def _process_table() -> dict[int, ProcessInfo]:
    output = _run(["ps", "-ww", "-axo", "pid=,ppid=,lstart=,command="], timeout=8.0)
    result: dict[int, ProcessInfo] = {}
    for line in output.splitlines():
        parts = line.strip().split(None, 7)
        if len(parts) < 8:
            continue
        try:
            pid, ppid = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        result[pid] = ProcessInfo(pid, ppid, " ".join(parts[2:7]), parts[7])
    return result


def _descendants(root_pid: int) -> list[ProcessInfo]:
    table = _process_table()
    if root_pid not in table:
        raise LifecycleFailure("runner_main_pid_missing")
    children: dict[int, list[int]] = {}
    for item in table.values():
        children.setdefault(item.ppid, []).append(item.pid)
    found: set[int] = set()
    pending = list(children.get(root_pid, []))
    while pending:
        child = pending.pop()
        if child in found:
            continue
        found.add(child)
        pending.extend(children.get(child, []))
    return [table[pid] for pid in sorted(found) if pid in table]


def _process_identity_alive(record: ProcessInfo) -> bool:
    try:
        completed = subprocess.run(
            ["ps", "-ww", "-p", str(record.pid), "-o", "pid=,lstart=,command="],
            capture_output=True,
            text=True,
            timeout=3.0,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LifecycleFailure("process_state_observation_failed") from exc
    output = completed.stdout
    if completed.returncode != 0:
        if completed.stderr.strip() or output.strip():
            raise LifecycleFailure("process_state_observation_failed")
        return False
    if not output.strip():
        return False
    parts = output.strip().split(None, 6)
    if len(parts) < 7:
        raise LifecycleFailure("process_state_observation_invalid")
    try:
        current_pid = int(parts[0])
    except ValueError:
        raise LifecycleFailure("process_state_observation_invalid")
    if current_pid != record.pid:
        raise LifecycleFailure("process_state_observation_invalid")
    return " ".join(parts[1:6]) == record.started


def _assert_process_tree_gone(run: RunState) -> None:
    if any(_process_identity_alive(item) for item in run.descendants_before_term):
        raise LifecycleFailure("runner_child_processes_remain_after_term")
    if any(run.run_id in item.command for item in _process_table().values()):
        raise LifecycleFailure("run_identity_remains_in_process_command")


def _set_support_environment(run: RunState) -> Any:
    assert run.run_dir is not None
    db = run.config["db_clients"][0]
    redis_config = run.config["redis_clients"][0]
    values = {
        "WONIUNOTE_TEST_BASE_URL": run.base_url,
        "WONIUNOTE_TEST_RUN_ID": run.run_id,
        "WONIUNOTE_TEST_RUNTIME_DIR": str(run.run_dir),
        "WONIUNOTE_TEST_DB_HOST": "127.0.0.1",
        "WONIUNOTE_TEST_DB_PORT": str(run.ports["mysql"]),
        "WONIUNOTE_TEST_DB_NAME": str(db["dbname"]),
        "WONIUNOTE_TEST_DB_USER": str(db["user"]),
        "WONIUNOTE_TEST_DB_PASSWORD": str(db["passwd"]),
        "WONIUNOTE_TEST_REDIS_HOST": "127.0.0.1",
        "WONIUNOTE_TEST_REDIS_PORT": str(run.ports["redis"]),
        "WONIUNOTE_TEST_REDIS_PASSWORD": str(redis_config["passwd"]),
        "WONIUNOTE_TEST_MYSQL_CONTAINER": run.container_ids["mysql"],
        "WONIUNOTE_TEST_MYSQL_CONTAINER_ID": run.container_ids["mysql"],
        "WONIUNOTE_TEST_REDIS_CONTAINER": run.container_ids["redis"],
        "WONIUNOTE_TEST_REDIS_CONTAINER_ID": run.container_ids["redis"],
    }
    os.environ.update(values)
    module = importlib.import_module("iter21_support")
    module = importlib.reload(module)
    if module.BASE_URL != run.base_url or module.RUN_ID != run.run_id:
        raise LifecycleFailure("integration_support_identity_mismatch")
    return module


def _png_bytes(color: tuple[int, int, int]) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        content = kind + payload
        return (
            struct.pack(">I", len(payload))
            + content
            + struct.pack(">I", zlib.crc32(content) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes((0, *color, 255))))
        + chunk(b"IEND", b"")
    )


def _assert_upload_download(support: Any, path: str, expected: bytes) -> None:
    import requests

    if not path.startswith("/") or path.startswith("//"):
        raise LifecycleFailure("upload_url_invalid")
    response = requests.get(support.url(path), timeout=8)
    if response.status_code != 200:
        raise LifecycleFailure("uploaded_file_http_readback_failed")
    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    if content_type != "image/png" or response.content != expected:
        raise LifecycleFailure("uploaded_file_http_content_mismatch")


def _upload_sentinels(run: RunState, support: Any, user: Any, color: tuple[int, int, int]) -> None:
    import requests

    assert run.run_dir is not None
    png = _png_bytes(color)
    sha = hashlib.sha256(png).hexdigest()
    document_root = run.run_dir / "uploads"
    backend_runtime = run.run_dir / "backend-runtime"

    image_response = requests.post(
        support.url("/api/upload/image"),
        headers=user.headers,
        files={"file": (f"lifecycle-{run.slot}.png", png, "image/png")},
        timeout=10,
    )
    if image_response.status_code != 200:
        raise LifecycleFailure("upload_controller_request_failed")
    try:
        image_body = image_response.json()
        image_path = image_body["data"]["url"]
    except (ValueError, KeyError, TypeError) as exc:
        raise LifecycleFailure("upload_controller_response_invalid") from exc
    parsed = urlsplit(image_path)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        raise LifecycleFailure("upload_controller_url_not_local")
    if not re.fullmatch(r"/uploads/uploads/images/\d{4}/\d{2}/\d+_\d{4}\.png", parsed.path):
        raise LifecycleFailure("upload_controller_url_path_invalid")
    relative = Path(*parsed.path.lstrip("/").split("/"))
    image_file = document_root.joinpath(*relative.parts)
    upload_relative = Path(*parsed.path.removeprefix("/uploads/").split("/"))
    expected_image_file = run.run_dir / "uploads" / "uploads" / upload_relative
    if image_file != expected_image_file:
        raise LifecycleFailure("upload_controller_document_root_geometry_mismatch")
    if image_file.is_symlink() or not image_file.is_file():
        raise LifecycleFailure("upload_controller_file_path_invalid")
    try:
        image_file.resolve(strict=True).relative_to(run.run_dir)
    except ValueError as exc:
        raise LifecycleFailure("upload_controller_file_escaped_run_root") from exc
    if image_file.resolve(strict=True).read_bytes() != png:
        raise LifecycleFailure("upload_controller_file_bytes_mismatch")
    if image_body.get("code") != 200:
        raise LifecycleFailure("upload_controller_response_unsuccessful")
    _assert_upload_download(support, parsed.path, png)
    run.upload_records.append(
        {
            "kind": "upload-controller",
            "relative_path": str(image_file.relative_to(run.run_dir)),
            "url_path": parsed.path,
            "sha256": sha,
        }
    )

    editor_response = requests.post(
        support.url("/api/uedit"),
        params={"action": "uploadimage"},
        headers=user.headers,
        files={"upfile": (f"lifecycle-{run.slot}.png", png, "image/png")},
        timeout=10,
    )
    if editor_response.status_code != 200:
        raise LifecycleFailure("ueditor_upload_request_failed")
    try:
        editor_body = editor_response.json()
        editor_url = editor_body["url"]
    except (ValueError, KeyError, TypeError) as exc:
        raise LifecycleFailure("ueditor_upload_response_invalid") from exc
    if editor_body.get("state") != "SUCCESS" or not isinstance(editor_url, str):
        raise LifecycleFailure("ueditor_upload_response_unsuccessful")
    parsed_editor = urlsplit(editor_url)
    if parsed_editor.scheme or parsed_editor.netloc or parsed_editor.query or parsed_editor.fragment:
        raise LifecycleFailure("ueditor_upload_url_not_local")
    match = re.fullmatch(r"/api/uploads/([A-Za-z0-9_.-]+\.png)", parsed_editor.path)
    if not match:
        raise LifecycleFailure("ueditor_upload_url_path_invalid")
    editor_file = run.run_dir / "uploads" / match.group(1)
    if editor_file.is_symlink() or not editor_file.is_file():
        raise LifecycleFailure("ueditor_file_not_in_run_uploads")
    if editor_file.resolve(strict=True).read_bytes() != png:
        raise LifecycleFailure("ueditor_file_bytes_mismatch")
    if (backend_runtime / "uploads" / match.group(1)).exists():
        raise LifecycleFailure("ueditor_file_under_backend_runtime")
    if (run.run_dir.parent / "uploads" / match.group(1)).exists():
        raise LifecycleFailure("ueditor_file_under_shared_parent")
    _assert_upload_download(support, parsed_editor.path, png)
    run.upload_records.append(
        {
            "kind": "ueditor",
            "relative_path": str(editor_file.relative_to(run.run_dir)),
            "url_path": parsed_editor.path,
            "sha256": sha,
        }
    )


def _write_sentinels_and_http(run: RunState, repo: Path, color: tuple[int, int, int]) -> None:
    import redis
    import requests

    assert run.run_dir is not None
    health = requests.get(f"{run.base_url}/health", timeout=5)
    if health.status_code != 200 or health.json().get("status") != "healthy":
        raise LifecycleFailure("backend_health_check_failed")
    support_dir = repo / "backend_cpp" / "tests" / "integration"
    if str(support_dir) not in sys.path:
        sys.path.insert(0, str(support_dir))
    support = _set_support_environment(run)
    connection = support.owned_mysql_connection()
    sentinel = hashlib.sha256(f"{run.run_id}:mysql".encode()).hexdigest()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS i21_runner_lifecycle_sentinel "
                "(run_id VARCHAR(40) PRIMARY KEY, sentinel CHAR(64) NOT NULL) ENGINE=InnoDB"
            )
            cursor.execute(
                "INSERT INTO i21_runner_lifecycle_sentinel (run_id, sentinel) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE sentinel=VALUES(sentinel)",
                (run.run_id, sentinel),
            )
            connection.commit()
            cursor.execute(
                "SELECT sentinel FROM i21_runner_lifecycle_sentinel WHERE run_id=%s",
                (run.run_id,),
            )
            row = cursor.fetchone()
        if not row or row[0] != sentinel:
            raise LifecycleFailure("mysql_sentinel_readback_failed")
    finally:
        connection.close()
    run.mysql_sentinel = sentinel

    redis_config = run.config["redis_clients"][0]
    client = redis.Redis(
        host="127.0.0.1",
        port=run.ports["redis"],
        password=redis_config["passwd"],
        db=0,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
    run.redis_key = f"i21:runner-lifecycle:{run.run_id}"
    run.redis_sentinel = hashlib.sha256(f"{run.run_id}:redis".encode()).hexdigest()
    if not client.ping() or not client.set(run.redis_key, run.redis_sentinel, ex=1800):
        raise LifecycleFailure("redis_sentinel_write_failed")
    if client.get(run.redis_key) != run.redis_sentinel:
        raise LifecycleFailure("redis_sentinel_readback_failed")
    client.close()

    credentials = support.register_user()
    user = support.login(credentials)
    authenticated = requests.get(support.url("/api/auth/me"), headers=user.headers, timeout=8)
    if authenticated.status_code != 200:
        raise LifecycleFailure("authenticated_http_sentinel_failed")
    run.authenticated_user = user
    _upload_sentinels(run, support, user, color)


def _verify_run_sentinels(run: RunState, *, include_uploads: bool) -> None:
    import redis
    import requests

    assert run.run_dir is not None
    if run.process is None or run.process.poll() is not None:
        raise LifecycleFailure("runner_exited_before_checkpoint")
    support = _set_support_environment(run)
    health = requests.get(f"{run.base_url}/health", timeout=5)
    if health.status_code != 200 or health.json().get("status") != "healthy":
        raise LifecycleFailure("backend_health_sentinel_lost")
    auth = requests.get(
        support.url("/api/auth/me"),
        headers=run.authenticated_user.headers,
        timeout=8,
    )
    if auth.status_code != 200:
        raise LifecycleFailure("authenticated_http_sentinel_lost")
    connection = support.owned_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT sentinel FROM i21_runner_lifecycle_sentinel WHERE run_id=%s",
                (run.run_id,),
            )
            row = cursor.fetchone()
        if not row or row[0] != run.mysql_sentinel:
            raise LifecycleFailure("mysql_sentinel_lost")
    finally:
        connection.close()
    redis_config = run.config["redis_clients"][0]
    client = redis.Redis(
        host="127.0.0.1",
        port=run.ports["redis"],
        password=redis_config["passwd"],
        db=0,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
    try:
        if client.get(run.redis_key) != run.redis_sentinel:
            raise LifecycleFailure("redis_sentinel_lost")
    finally:
        client.close()
    if include_uploads:
        for record in run.upload_records:
            path = run.run_dir / record["relative_path"]
            if path.is_symlink() or not path.is_file():
                raise LifecycleFailure("upload_sentinel_lost")
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != record["sha256"]:
                raise LifecycleFailure("upload_sentinel_changed")
            _assert_upload_download(support, record["url_path"], data)


def _gate_ready(run: RunState) -> bool:
    if run.process is None:
        raise LifecycleFailure("runner_not_started")
    if run.process.poll() is not None:
        raise LifecycleFailure("runner_exited_before_gate")
    return run.gate_ready.is_file()


def _load_until_ready(runs: list[RunState], timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for run in runs:
            if run.process is None or run.process.poll() is not None:
                raise LifecycleFailure("runner_exited_during_startup")
        if all(run.gate_ready.is_file() and not run.gate_ready.is_symlink() for run in runs):
            # The runner writes its config before entering the tracked pytest
            # child. Read it only after both private gates confirm that setup
            # is complete, so a partially-written JSON file is never observed.
            for run in runs:
                if not _load_config(run):
                    raise LifecycleFailure("runner_gate_reached_without_config")
            if all(_gate_ready(run) for run in runs):
                for run in runs:
                    if not any(run.gate_path.name in item.command for item in _descendants(run.process.pid)):
                        raise LifecycleFailure("tracked_gate_process_missing")
                return
        time.sleep(0.1)
    raise LifecycleFailure("runner_startup_timeout")


def _term_runner(run: RunState, timeout: float) -> None:
    if run.process is None:
        raise LifecycleFailure("runner_not_started")
    if run.process.poll() is not None:
        raise LifecycleFailure("runner_exited_before_term")
    descendants = _descendants(run.process.pid)
    if not any(run.gate_path.name in item.command for item in descendants):
        raise LifecycleFailure("tracked_gate_not_running_at_term")
    run.descendants_before_term = descendants
    started = time.monotonic()
    os.kill(run.process.pid, signal.SIGTERM)
    run.term_sent = True
    try:
        run.term_returncode = run.process.wait(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        run.term_elapsed = time.monotonic() - started
        raise LifecycleFailure("runner_term_cleanup_timeout") from exc
    run.term_elapsed = time.monotonic() - started
    if run.term_returncode != 143:
        raise LifecycleFailure("runner_did_not_exit_with_term_status_143")
    _assert_process_tree_gone(run)


def _safe_run_summary(run: RunState) -> dict[str, Any]:
    return {
        "run_id": run.run_id or None,
        "runner_pid": run.process.pid if run.process else None,
        "returncode": run.term_returncode,
        "term_elapsed_seconds": round(run.term_elapsed, 3) if run.term_elapsed is not None else None,
        "ports": dict(run.ports),
        "container_ids": dict(run.container_ids),
        "mysql_volume": run.volume_name or None,
        "mysql_sentinel_verified": bool(run.mysql_sentinel),
        "redis_sentinel_verified": bool(run.redis_sentinel),
        "upload_sentinels": [
            {
                "kind": item["kind"],
                "relative_path": item["relative_path"],
                "sha256": item["sha256"],
            }
            for item in run.upload_records
        ],
    }


def _write_summary(root: Path, summary: dict[str, Any]) -> None:
    destination = root / "safe" / "summary.json"
    temporary = destination.with_suffix(".json.tmp")
    data = json.dumps(summary, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, destination)
    os.chmod(destination, 0o600)


def _validate_args(args: argparse.Namespace) -> tuple[Path, Path, Path, str, str, str]:
    repo_value = Path(args.repo).expanduser()
    backend_value = Path(args.backend_bin).expanduser()
    if not repo_value.is_absolute() or not backend_value.is_absolute():
        raise LifecycleFailure("repo_and_backend_paths_must_be_absolute")
    repo = repo_value.resolve(strict=True)
    backend = backend_value.resolve(strict=True)
    runner = repo / "backend_cpp" / "tests" / "integration" / "run_integration.sh"
    if not runner.is_file() or not os.access(runner, os.X_OK):
        raise LifecycleFailure("frozen_runner_unavailable")
    if not backend.is_file() or not os.access(backend, os.X_OK):
        raise LifecycleFailure("frozen_backend_unavailable")
    runner_hash = _sha256_file(runner)
    backend_hash = _sha256_file(backend)
    if args.expected_runner_sha256 and runner_hash != args.expected_runner_sha256.lower():
        raise LifecycleFailure("runner_sha256_mismatch")
    if args.expected_backend_sha256 and backend_hash != args.expected_backend_sha256.lower():
        raise LifecycleFailure("backend_sha256_mismatch")
    if not (repo / "backend_cpp" / "tests" / "integration" / "iter21_support.py").is_file():
        raise LifecycleFailure("integration_support_missing")
    context = _docker_context_is_local()
    return repo, backend, runner, runner_hash, backend_hash, context


def _cleanup_started_runners(runs: list[RunState], timeout: float) -> None:
    for run in runs:
        process = run.process
        if process is None or process.poll() is not None:
            if run.log_stream is not None:
                run.log_stream.close()
                run.log_stream = None
            continue
        if not run.term_sent:
            try:
                os.kill(process.pid, signal.SIGTERM)
                run.term_sent = True
            except OSError:
                pass
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # No SIGKILL or child signal here. A runner that misses its trap is
            # an explicit incomplete result and retains its owned diagnostics.
            pass
        if run.log_stream is not None:
            run.log_stream.close()
            run.log_stream = None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="absolute frozen repository checkout")
    parser.add_argument("--backend-bin", required=True, help="absolute frozen test backend executable")
    parser.add_argument("--artifact-root", required=True, help="new absolute private output directory")
    parser.add_argument("--expected-runner-sha256")
    parser.add_argument("--expected-backend-sha256")
    parser.add_argument("--startup-timeout", type=float, default=STARTUP_TIMEOUT)
    parser.add_argument("--stop-timeout", type=float, default=STOP_TIMEOUT)
    args = parser.parse_args(argv)

    artifact_root: Path | None = None
    runs: list[RunState] = []
    summary: dict[str, Any] = {
        "status": "INCOMPLETE",
        "experiment": "two-run-runner-main-pid-term-isolation-with-live-uploads",
        "term_target": "runner-main-pid-only",
        "child_gate_signals_sent_by_driver": 0,
        "runs": {},
    }
    failure_code = "not_started"
    exit_status = 2
    try:
        if not (5.0 <= args.startup_timeout <= 600.0 and 3.0 <= args.stop_timeout <= 90.0):
            raise LifecycleFailure("timeout_outside_safe_bounds")
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            os.environ.pop(key, None)
        os.environ["NO_PROXY"] = "127.0.0.1,localhost"
        os.environ["no_proxy"] = os.environ["NO_PROXY"]

        repo, backend, runner, runner_hash, backend_hash, docker_context = _validate_args(args)
        artifact_root = _new_artifact_root(args.artifact_root)
        git_commit = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        summary["source"] = {
            "repo_commit": git_commit.stdout.strip() if git_commit.returncode == 0 else None,
            "runner_sha256": runner_hash,
            "backend_sha256": backend_hash,
        }
        summary["docker_context"] = docker_context
        base_env = os.environ.copy()
        for slot in ("a", "b"):
            control_root = artifact_root / "control"
            run = RunState(
                slot=slot,
                temp_root=artifact_root / "runtime" / slot,
                result_root=artifact_root / "safe" / f"runner-{slot}",
                gate_path=control_root / f"gate-{slot}.sh",
                gate_ready=control_root / f"gate-{slot}.ready",
                gate_release=control_root / f"gate-{slot}.release",
                log_path=artifact_root / "raw" / f"runner-{slot}.log",
            )
            runs.append(run)
            _start_runner(run, runner, repo, backend, base_env)
        _write_summary(
            artifact_root,
            {**summary, "status": "RUNNING", "runs": {run.slot: _safe_run_summary(run) for run in runs}},
        )

        _load_until_ready(runs, args.startup_timeout)
        if runs[0].run_id == runs[1].run_id:
            raise LifecycleFailure("runner_ids_not_unique")
        if set(runs[0].ports.values()) & set(runs[1].ports.values()):
            raise LifecycleFailure("run_ports_not_isolated")
        for run in runs:
            run.resource_snapshot = _inspect_run_resources(run)
        for run, color in zip(runs, ((210, 30, 40), (20, 70, 210))):
            _write_sentinels_and_http(run, repo, color)
            run.resource_snapshot = _inspect_run_resources(run)
            _verify_run_sentinels(run, include_uploads=True)
        hashes_a = {item["sha256"] for item in runs[0].upload_records}
        hashes_b = {item["sha256"] for item in runs[1].upload_records}
        if not hashes_a.isdisjoint(hashes_b):
            raise LifecycleFailure("run_upload_contents_not_distinct")

        b_container_baseline = dict(runs[1].container_ids)
        b_volume_baseline = runs[1].volume_name
        b_upload_baseline = [
            _sha256_file(runs[1].run_dir / item["relative_path"])
            for item in runs[1].upload_records
        ]

        _term_runner(runs[0], args.stop_timeout)
        _assert_resources_removed(runs[0])
        _write_summary(
            artifact_root,
            {
                **summary,
                "status": "RUNNING",
                "a_term_cleanup_verified": True,
                "runs": {run.slot: _safe_run_summary(run) for run in runs},
            },
        )

        if runs[1].process is None or runs[1].process.poll() is not None:
            raise LifecycleFailure("run_b_stopped_with_run_a")
        resources_after_a = _inspect_run_resources(runs[1])
        if runs[1].container_ids != b_container_baseline or runs[1].volume_name != b_volume_baseline:
            raise LifecycleFailure("run_b_resource_identity_changed_after_run_a_term")
        if resources_after_a["container_ids"] != b_container_baseline:
            raise LifecycleFailure("run_b_containers_changed_after_run_a_term")
        _verify_run_sentinels(runs[1], include_uploads=True)
        b_upload_after_a = [
            _sha256_file(runs[1].run_dir / item["relative_path"])
            for item in runs[1].upload_records
        ]
        if b_upload_after_a != b_upload_baseline:
            raise LifecycleFailure("run_b_upload_changed_after_run_a_term")

        _term_runner(runs[1], args.stop_timeout)
        _assert_resources_removed(runs[1])
        summary["status"] = "PASS"
        summary["a_term_cleanup_verified"] = True
        summary["b_survived_a_term"] = True
        summary["b_term_cleanup_verified"] = True
        summary["run_b_upload_hashes_unchanged_after_a_term"] = True
        summary["runs"] = {run.slot: _safe_run_summary(run) for run in runs}
        failure_code = ""
        exit_status = 0
    except LifecycleFailure as exc:
        failure_code = exc.code
    except Exception as exc:
        failure_code = f"unexpected_{type(exc).__name__}"
    finally:
        if artifact_root is not None:
            if failure_code:
                summary["status"] = "FAIL_OR_INCOMPLETE"
                summary["failure_code"] = failure_code
            summary["runs"] = {run.slot: _safe_run_summary(run) for run in runs}
            _cleanup_started_runners(runs, args.stop_timeout)
            try:
                _write_summary(artifact_root, summary)
            except Exception:
                exit_status = 2
        else:
            print(json.dumps({"status": "INCOMPLETE", "failure_code": failure_code}, sort_keys=True))
    if artifact_root is not None:
        print(json.dumps({"status": summary["status"], "summary": str(artifact_root / "safe" / "summary.json")}, sort_keys=True))
    return exit_status


if __name__ == "__main__":
    raise SystemExit(main())
