"""Run one Linux Iteration 21 backend in a run-owned Docker runtime container."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


RUN_ID_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}$")
CONTAINER_ID_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
RESERVED_PORTS = {3306, 6379, 5173, 8888}
BASE_IMAGE_DEFAULT = "woniunote.iter21/system-libs:ubuntu22.04"
ENTRYPOINT = "/usr/local/bin/woniunote-iter21-container-entrypoint"
CONTAINER_BINARY = "/opt/woniunote_backend"
CONTAINER_HOST_ALIAS = "host.docker.internal"


class LaunchError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise LaunchError(message)


def required_env(name: str, *aliases: str) -> str:
    values = [(key, os.environ.get(key, "")) for key in (name, *aliases)]
    present = [(key, value) for key, value in values if value]
    if not present:
        fail(f"required launcher environment setting is missing: {name}")
    first = present[0][1]
    if any(value != first for _key, value in present[1:]):
        fail(f"launcher environment aliases disagree: {name}")
    return first


def private_file(path: Path) -> None:
    try:
        metadata = path.lstat()
    except OSError:
        fail("required private config file is unavailable")
    if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) & 0o077:
        fail("config file must be a regular file with private permissions")


def private_directory(path: Path) -> None:
    try:
        metadata = path.lstat()
    except OSError:
        fail("required private runtime directory is unavailable")
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) & 0o077:
        fail("runtime directories must be private and must not be symlinks")


def safe_resolve_under(path_value: Any, root: Path, description: str) -> Path:
    if not isinstance(path_value, str) or not path_value:
        fail(f"config {description} is missing")
    path = Path(path_value)
    if not path.is_absolute():
        fail(f"config {description} must be an absolute run-owned path")
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError:
        fail(f"config {description} escapes the owned runtime")
    return resolved


def run_command(args: list[str], *, timeout: float = 8.0) -> str:
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        fail("a required bounded Docker or process-inspection command failed")
    if completed.returncode != 0:
        fail("a required Docker or process-inspection command failed")
    return completed.stdout.strip()


def inspect_container(container_id: str) -> dict[str, Any]:
    raw = run_command(
        ["docker", "inspect", "--format", "{{json .}}", container_id], timeout=8.0
    )
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        fail("Docker returned invalid owned-container metadata")
    if not isinstance(data, dict):
        fail("Docker returned invalid owned-container metadata")
    return data


def discover_container(service: str, run_id: str, explicit_id: str) -> str:
    if explicit_id:
        if not CONTAINER_ID_PATTERN.fullmatch(explicit_id):
            fail(f"invalid explicit {service} container ID")
        candidates = [explicit_id]
    else:
        output = run_command(
            [
                "docker",
                "ps",
                "-aq",
                "--no-trunc",
                "--filter",
                f"label=org.woniunote.iter21.run-id={run_id}",
                "--filter",
                f"label=org.woniunote.iter21.service={service}",
            ],
            timeout=8.0,
        )
        candidates = [line.strip() for line in output.splitlines() if line.strip()]
    if len(candidates) != 1 or not CONTAINER_ID_PATTERN.fullmatch(candidates[0]):
        fail(f"expected exactly one run-owned {service} container")
    return candidates[0]


def verify_container(
    service: str,
    run_id: str,
    host_port: int,
    container_id: str,
    explicit_id: str,
) -> None:
    if explicit_id and explicit_id != container_id:
        fail(f"run-owned {service} container identity changed")
    data = inspect_container(container_id)
    if data.get("Id") != container_id:
        fail(f"run-owned {service} container identity mismatch")
    config = data.get("Config") or {}
    labels = config.get("Labels") or {}
    if (
        labels.get("org.woniunote.iter21.run-id") != run_id
        or labels.get("org.woniunote.iter21.service") != service
    ):
        fail(f"refusing a {service} container without exact run ownership labels")
    if (data.get("State") or {}).get("Running") is not True:
        fail(f"run-owned {service} container is not running")
    port_name = "3306/tcp" if service == "mysql" else "6379/tcp"
    bindings = ((data.get("NetworkSettings") or {}).get("Ports") or {}).get(port_name)
    if not isinstance(bindings, list) or len(bindings) != 1:
        fail(f"run-owned {service} container has no unique published port")
    binding = bindings[0]
    if binding.get("HostIp") != "127.0.0.1" or binding.get("HostPort") != str(host_port):
        fail(f"run-owned {service} loopback port mapping does not match the config")


def process_command(pid: int) -> str:
    return run_command(["ps", "-ww", "-p", str(pid), "-o", "command="], timeout=3.0)


def parent_chain() -> set[int]:
    chain: set[int] = set()
    current = os.getppid()
    for _ in range(32):
        if current <= 1 or current in chain:
            break
        chain.add(current)
        raw = run_command(["ps", "-p", str(current), "-o", "ppid="], timeout=3.0)
        try:
            current = int(raw.strip())
        except ValueError:
            break
    return chain


def verify_proxy_listener(port: int, ancestors: set[int]) -> None:
    raw = run_command(
        [
            "lsof",
            "-nP",
            "-Fpn",
            f"-iTCP:{port}",
            "-sTCP:LISTEN",
        ],
        timeout=4.0,
    )
    pids: set[int] = set()
    names: list[str] = []
    for line in raw.splitlines():
        if line.startswith("p"):
            try:
                pids.add(int(line[1:]))
            except ValueError:
                fail("could not identify the test-owned proxy listener process")
        elif line.startswith("n"):
            names.append(line[1:].split(" ", 1)[0])
    if len(pids) != 1 or len(names) != 1:
        fail("proxy port must have exactly one verifiable loopback listener")
    pid = next(iter(pids))
    expected_listener = f"127.0.0.1:{port}"
    if names[0] != expected_listener:
        fail("proxy listener is not bound exclusively to IPv4 loopback")
    if pid not in ancestors:
        fail("proxy listener process is not an ancestor of the launcher")
    if "pytest" not in process_command(pid).lower():
        fail("proxy listener process is not the active pytest process")


def inspect_runtime_image(image: str, base_image: str) -> tuple[str, str, str]:
    raw = run_command(
        [
            "docker",
            "image",
            "inspect",
            "--format",
            "{{.Id}}|{{index .Config.Labels \"com.woniunote.iteration\"}}|"
            "{{index .Config.Labels \"com.woniunote.purpose\"}}|"
            "{{index .Config.Labels \"com.woniunote.runtime.base-image\"}}|"
            "{{index .Config.Labels \"com.woniunote.runtime.base-image-id\"}}|"
            "{{index .Config.Labels \"com.woniunote.runtime.spec-sha256\"}}",
            image,
        ],
        timeout=8.0,
    )
    fields = raw.split("|")
    if len(fields) != 6:
        fail("runtime image metadata is incomplete")
    image_id, iteration, purpose, declared_base, declared_base_id, runtime_spec = fields
    if (
        not SHA256_PATTERN.fullmatch(image_id)
        or iteration != "21"
        or purpose != "backend-runtime"
        or declared_base != base_image
        or not SHA256_PATTERN.fullmatch(declared_base_id)
        or not re.fullmatch(r"[0-9a-f]{64}", runtime_spec)
    ):
        fail("runtime image lacks the expected Iteration 21 ownership metadata")
    base_raw = run_command(
        [
            "docker",
            "image",
            "inspect",
            "--format",
            "{{.Id}}|{{index .Config.Labels \"com.woniunote.iteration\"}}|"
            "{{index .Config.Labels \"com.woniunote.purpose\"}}|"
            "{{index .Config.Labels \"com.woniunote.builder\"}}",
            base_image,
        ],
        timeout=8.0,
    )
    base_fields = base_raw.split("|")
    if (
        len(base_fields) != 4
        or not SHA256_PATTERN.fullmatch(base_fields[0])
        or base_fields[1:] != ["21", "linux-builder", "system-libs"]
        or base_fields[0] != declared_base_id
    ):
        fail("runtime image does not derive from the labeled local system-libs image")
    return image_id, declared_base_id, runtime_spec


def current_runtime_spec_sha256() -> str:
    runtime_dir = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    try:
        digest.update((runtime_dir / "Dockerfile").read_bytes())
        digest.update(b"\n--ENTRYPOINT--\n")
        digest.update((runtime_dir / "container-entrypoint.sh").read_bytes())
    except OSError:
        fail("runtime image source files are unavailable")
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError:
        fail("Linux backend binary could not be read")
    return digest.hexdigest()


def expected_config_path(config_path: Path, run_dir: Path) -> tuple[Path, str]:
    primary = run_dir / "config.integration.json"
    secondary = run_dir / "fault-proxy-runtime" / "config" / "config.json"
    try:
        actual = config_path.resolve(strict=True)
    except OSError:
        fail("requested config path is unavailable")
    if actual == primary:
        return primary, "primary"
    if actual == secondary:
        return secondary, "secondary"
    fail("launcher accepts only the primary or transport-fault run config")
    raise AssertionError("unreachable")


def load_and_validate_config(
    config_path: Path, run_dir: Path, run_id: str
) -> tuple[dict[str, Any], str, int]:
    private_file(config_path)
    canonical_config, instance = expected_config_path(config_path, run_dir)
    private_file(canonical_config)
    if instance == "secondary":
        private_directory(run_dir / "fault-proxy-runtime")
        private_directory(run_dir / "fault-proxy-runtime" / "config")
    try:
        config = json.loads(canonical_config.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        fail("launcher config is unreadable or invalid JSON")
    if not isinstance(config, dict):
        fail("launcher config root must be an object")

    custom = config.get("custom_config") or {}
    if custom.get("app_mode") != "test" or custom.get("test_run_id") != run_id:
        fail("config does not identify this isolated test run")
    app = config.get("app") or {}
    if app.get("run_as_daemon") is not False:
        fail("backend daemonization is disabled for owned runtimes")
    safe_resolve_under(app.get("document_root"), run_dir, "document root")
    safe_resolve_under(app.get("upload_path"), run_dir, "upload path")
    log = app.get("log") or {}
    safe_resolve_under(log.get("log_path"), run_dir, "log path")

    listeners = config.get("listeners")
    if not isinstance(listeners, list) or len(listeners) != 1 or not isinstance(listeners[0], dict):
        fail("exactly one HTTP listener is required")
    listener = listeners[0]
    if listener.get("address") != "127.0.0.1" or listener.get("https") is not False:
        fail("backend listener must be plain HTTP bound to IPv4 loopback")
    try:
        http_port = int(listener.get("port"))
    except (TypeError, ValueError):
        fail("backend HTTP port is invalid")
    if not 1024 <= http_port <= 65535 or http_port in RESERVED_PORTS:
        fail("backend HTTP port is reserved or invalid")

    databases = config.get("db_clients")
    redis_clients = config.get("redis_clients")
    if not isinstance(databases, list) or len(databases) != 1 or not isinstance(databases[0], dict):
        fail("exactly one isolated MySQL client is required")
    if not isinstance(redis_clients, list) or len(redis_clients) != 1 or not isinstance(redis_clients[0], dict):
        fail("exactly one isolated Redis client is required")
    db = databases[0]
    redis = redis_clients[0]
    db_host = required_env("WN_I21_DB_HOST", "WONIUNOTE_TEST_DB_HOST")
    redis_host = required_env("WN_I21_REDIS_HOST", "WONIUNOTE_TEST_REDIS_HOST")
    if db_host != "127.0.0.1" or redis_host != "127.0.0.1":
        fail("owned service endpoints must use IPv4 loopback")
    try:
        db_port = int(required_env("WN_I21_DB_PORT", "WONIUNOTE_TEST_DB_PORT"))
        redis_port = int(required_env("WN_I21_REDIS_PORT", "WONIUNOTE_TEST_REDIS_PORT"))
    except ValueError:
        fail("owned DB or Redis endpoint port is invalid")
    if not 1024 <= db_port <= 65535 or not 1024 <= redis_port <= 65535:
        fail("owned DB or Redis endpoint port is invalid")
    if http_port in {db_port, redis_port}:
        fail("HTTP and dependency host ports must be distinct")
    try:
        config_db_port = int(db.get("port", -1))
        config_redis_port = int(redis.get("port", -1))
        redis_db = int(redis.get("db", -1))
    except (TypeError, ValueError):
        fail("config contains an invalid DB or Redis port")
    if not 1024 <= config_db_port <= 65535 or not 1024 <= config_redis_port <= 65535:
        fail("config contains an invalid DB or Redis port")
    if db.get("host") != "127.0.0.1" or redis.get("host") != "127.0.0.1":
        fail("MySQL and Redis config endpoints must use IPv4 loopback")
    if db.get("dbname") != required_env("WN_I21_DB_NAME", "WONIUNOTE_TEST_DB_NAME"):
        fail("MySQL config database name does not match this test run")
    if db.get("user") != required_env("WN_I21_DB_USER", "WONIUNOTE_TEST_DB_USER"):
        fail("MySQL config user does not match this test run")
    if db.get("passwd") != required_env("WN_I21_DB_PASSWORD", "WONIUNOTE_TEST_DB_PASSWORD"):
        fail("MySQL config credentials do not match this test run")
    if redis.get("passwd") != required_env("WN_I21_REDIS_PASSWORD", "WONIUNOTE_TEST_REDIS_PASSWORD"):
        fail("Redis config credentials do not match this test run")
    if redis_db != 0:
        fail("only the owned Redis database zero is supported")

    run_owned_http_port = os.environ.get("WN_I21_TEST_PORT", "")
    if instance == "primary":
        if db.get("host") != db_host or config_db_port != db_port:
            fail("MySQL config endpoint does not match the run-owned service")
        if redis.get("host") != redis_host or config_redis_port != redis_port:
            fail("Redis config endpoint does not match the run-owned service")
        if run_owned_http_port and int(run_owned_http_port) != http_port:
            fail("primary HTTP port does not match the test-run endpoint")
    else:
        if run_owned_http_port and http_port == int(run_owned_http_port):
            fail("secondary HTTP port collides with the primary backend")
        if config_db_port in {db_port, redis_port} or config_redis_port in {db_port, redis_port}:
            fail("secondary DB and Redis proxy ports must differ from owned service ports")
        if (
            config_db_port in RESERVED_PORTS
            or config_redis_port in RESERVED_PORTS
            or config_db_port == config_redis_port
            or config_db_port == http_port
            or config_redis_port == http_port
        ):
            fail("secondary proxy and backend ports must be distinct")
        ancestors = parent_chain()
        verify_proxy_listener(config_db_port, ancestors)
        verify_proxy_listener(config_redis_port, ancestors)

    return config, instance, http_port


def verify_paths(run_dir: Path, config_path: Path, binary: Path) -> None:
    private_directory(run_dir)
    private_file(config_path)
    try:
        binary_info = binary.stat()
    except OSError:
        fail("Linux backend binary is unavailable")
    if not stat.S_ISREG(binary_info.st_mode) or not os.access(binary, os.X_OK):
        fail("Linux backend binary must be a regular executable file")


def verified_backend_workdir(run_dir: Path) -> Path:
    workdir = run_dir / "backend-runtime"
    if workdir.parent != run_dir or workdir.name != "backend-runtime":
        fail("backend working directory is outside the owned runtime")
    private_directory(workdir)
    try:
        permissions = stat.S_IMODE(workdir.lstat().st_mode)
    except OSError:
        fail("backend working directory is unavailable")
    if permissions != 0o700:
        fail("backend working directory must have mode 0700")
    try:
        resolved = workdir.resolve(strict=True)
    except OSError:
        fail("backend working directory is unavailable")
    if resolved != workdir or resolved.parent != run_dir:
        fail("backend working directory is not the canonical run-owned directory")
    return resolved


def write_private_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temporary = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    except BaseException:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def allocate_instance(run_dir: Path, role: str) -> tuple[str, Path, Path]:
    linux_root = run_dir / "linux-runtime"
    linux_root.mkdir(mode=0o700, exist_ok=True)
    os.chmod(linux_root, 0o700)
    evidence_dir = run_dir / "evidence"
    private_directory(evidence_dir)

    if role == "primary":
        instance = "primary"
        instance_root = linux_root / instance
        metadata_path = evidence_dir / f"backend-runtime-{instance}.json"
        if metadata_path.exists():
            fail("refusing to overwrite existing backend runtime evidence")
        try:
            instance_root.mkdir(mode=0o700)
        except FileExistsError:
            fail("refusing to reuse an existing Linux backend runtime directory")
        return instance, instance_root, metadata_path

    for _ in range(20):
        instance = f"secondary-{secrets.token_hex(6)}"
        instance_root = linux_root / instance
        metadata_path = evidence_dir / f"backend-runtime-{instance}.json"
        if instance_root.exists() or metadata_path.exists():
            continue
        try:
            instance_root.mkdir(mode=0o700)
        except FileExistsError:
            continue
        return instance, instance_root, metadata_path
    fail("could not allocate a unique secondary backend attempt")
    raise AssertionError("unreachable")


def proc_container_id(cidfile: Path, process: subprocess.Popen[bytes]) -> str:
    deadline = time.monotonic() + 5.0
    last_value = ""
    while time.monotonic() < deadline and process.poll() is None:
        try:
            value = cidfile.read_text(encoding="ascii").strip()
        except OSError:
            value = ""
        if CONTAINER_ID_PATTERN.fullmatch(value):
            os.chmod(cidfile, 0o600)
            return value
        if value:
            last_value = value
        time.sleep(0.05)
    if process.poll() is not None:
        try:
            value = cidfile.read_text(encoding="ascii").strip()
        except OSError:
            value = ""
        if CONTAINER_ID_PATTERN.fullmatch(value):
            os.chmod(cidfile, 0o600)
            return value
        if value:
            last_value = value
        if last_value:
            fail("Docker exited after writing an incomplete backend container ID")
        fail("Docker exited before writing the run-owned backend container ID")
    if last_value:
        fail("Docker did not finish writing the backend container ID within the startup bound")
    fail("Docker did not create the backend container within the startup bound")
    raise AssertionError("unreachable")


def verify_backend_container(container_id: str, run_id: str, instance: str) -> None:
    data = inspect_container(container_id)
    if data.get("Id") != container_id:
        fail("backend container identity mismatch")
    expected_name = f"/woniunote-i21-{run_id}-backend-{instance}"
    if data.get("Name") != expected_name:
        fail("backend container name does not match this run-owned instance")
    labels = ((data.get("Config") or {}).get("Labels") or {})
    if (
        labels.get("org.woniunote.iter21.run-id") != run_id
        or labels.get("org.woniunote.iter21.service") != "backend"
        or labels.get("org.woniunote.iter21.instance") != instance
    ):
        fail("backend container is missing exact run ownership labels")


def find_exact_owned_backend_container(name: str, run_id: str, instance: str) -> str:
    """Recover a child created before Docker finishes populating its cidfile."""
    try:
        container_id = run_command(
            ["docker", "inspect", "--format", "{{.Id}}", name], timeout=5.0
        )
    except LaunchError:
        return ""
    if not CONTAINER_ID_PATTERN.fullmatch(container_id):
        return ""
    try:
        verify_backend_container(container_id, run_id, instance)
    except LaunchError:
        return ""
    return container_id


def stop_owned_container(container_id: str, run_id: str, instance: str) -> None:
    try:
        verify_backend_container(container_id, run_id, instance)
    except LaunchError:
        return
    try:
        subprocess.run(
            ["docker", "stop", "--time", "5", container_id],
            capture_output=True,
            text=True,
            timeout=8.0,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        data = inspect_container(container_id)
    except LaunchError:
        return
    if (data.get("State") or {}).get("Running") is True:
        try:
            subprocess.run(
                ["docker", "kill", container_id],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    try:
        data = inspect_container(container_id)
    except LaunchError:
        return
    if (data.get("State") or {}).get("Running") is True:
        return
    try:
        verify_backend_container(container_id, run_id, instance)
        subprocess.run(
            ["docker", "rm", container_id],
            capture_output=True,
            text=True,
            timeout=8.0,
            check=False,
        )
    except (LaunchError, OSError, subprocess.TimeoutExpired):
        pass


def run_backend_container(
    *,
    run_dir: Path,
    workdir: Path,
    config_path: Path,
    cidfile: Path,
    binary: Path,
    image: str,
    run_id: str,
    instance: str,
    port: int,
    metadata_path: Path,
    metadata: dict[str, Any],
) -> int:
    name = f"woniunote-i21-{run_id}-backend-{instance}"
    argv = [
        "docker",
        "run",
        "--rm",
        "--cidfile",
        str(cidfile),
        "--pull=never",
        "--network",
        "bridge",
        "--name",
        name,
        "--label",
        f"org.woniunote.iter21.run-id={run_id}",
        "--label",
        "org.woniunote.iter21.service=backend",
        "--label",
        f"org.woniunote.iter21.instance={instance}",
        "--publish",
        f"127.0.0.1:{port}:{port}/tcp",
        "--workdir",
        str(workdir),
        "--mount",
        f"type=bind,source={run_dir},target={run_dir}",
        "--mount",
        f"type=bind,source={binary},target={CONTAINER_BINARY},readonly",
        "--env",
        "WONIUNOTE_ENV=test",
        "--env",
        f"WONIUNOTE_TEST_RUN_ID={run_id}",
        # The launcher is test-only. This setting is restricted to the
        # backend container after validating this run's TLS-disabled MySQL.
        "--env",
        "MARIADB_TLS_DISABLE_PEER_VERIFICATION=1",
        "--entrypoint",
        ENTRYPOINT,
        image,
        str(port),
        str(config_path),
    ]
    try:
        process: subprocess.Popen[bytes] = subprocess.Popen(argv)
    except OSError:
        fail("could not start the run-owned Linux backend container")
    container_id = ""
    interrupted_signal = 0

    def set_signal(signum: int, _frame: Any) -> None:
        nonlocal interrupted_signal
        interrupted_signal = signum

    previous_term = signal.signal(signal.SIGTERM, set_signal)
    previous_int = signal.signal(signal.SIGINT, set_signal)
    try:
        container_id = proc_container_id(cidfile, process)
        verify_backend_container(container_id, run_id, instance)
        metadata["backend_container_id"] = container_id
        try:
            write_private_json(metadata_path, metadata)
        except OSError:
            fail("could not update redacted backend runtime evidence")
        while process.poll() is None:
            if interrupted_signal:
                stop_owned_container(container_id, run_id, instance)
                break
            time.sleep(0.1)
        try:
            return_code = process.wait(timeout=8.0)
        except subprocess.TimeoutExpired:
            stop_owned_container(container_id, run_id, instance)
            try:
                process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2.0)
            return_code = process.returncode if process.returncode is not None else 124
        if interrupted_signal:
            return 128 + interrupted_signal
        return int(return_code or 0)
    finally:
        signal.signal(signal.SIGTERM, previous_term)
        signal.signal(signal.SIGINT, previous_int)
        if not container_id:
            try:
                candidate_id = cidfile.read_text(encoding="ascii").strip()
            except OSError:
                candidate_id = ""
            if CONTAINER_ID_PATTERN.fullmatch(candidate_id):
                try:
                    verify_backend_container(candidate_id, run_id, instance)
                    container_id = candidate_id
                except LaunchError:
                    pass
            if not container_id:
                container_id = find_exact_owned_backend_container(name, run_id, instance)
        if container_id:
            stop_owned_container(container_id, run_id, instance)
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2.0)
        try:
            cidfile.unlink(missing_ok=True)
        except OSError:
            pass


def launch(config_argument: str) -> int:
    run_id = required_env("WN_I21_RUN_ID", "WONIUNOTE_TEST_RUN_ID")
    if not RUN_ID_PATTERN.fullmatch(run_id):
        fail("test run ID is invalid")
    run_dir_value = required_env("WN_I21_RUN_DIR", "WONIUNOTE_TEST_RUNTIME_DIR")
    run_dir_arg = Path(run_dir_value)
    if not run_dir_arg.is_absolute():
        fail("runtime directory must be absolute")
    run_dir = run_dir_arg.resolve(strict=True)
    if run_dir.name != run_id:
        fail("runtime directory does not match this run ID")
    try:
        if stat.S_ISLNK(run_dir_arg.lstat().st_mode):
            fail("runtime directory must not be a symlink")
    except OSError:
        fail("runtime directory is unavailable")

    requested_config = Path(config_argument)
    if not requested_config.is_absolute():
        fail("backend config path must be absolute")
    config_path = requested_config.absolute()
    config, role, http_port = load_and_validate_config(
        config_path, run_dir, run_id
    )
    binary_value = required_env("WONIUNOTE_LINUX_BACKEND_BINARY")
    binary = Path(binary_value).resolve(strict=True)
    verify_paths(run_dir, config_path, binary)
    workdir = verified_backend_workdir(run_dir)
    image = required_env("WONIUNOTE_LINUX_RUNTIME_IMAGE")
    base_image = os.environ.get("WONIUNOTE_LINUX_BASE_IMAGE", BASE_IMAGE_DEFAULT)
    runtime_image_id, base_image_id, runtime_spec_sha256 = inspect_runtime_image(image, base_image)
    if runtime_spec_sha256 != current_runtime_spec_sha256():
        fail("runtime image was not built from the current runtime source files")

    mysql_explicit_id = os.environ.get("WN_I21_MYSQL_ID", "") or os.environ.get(
        "WONIUNOTE_TEST_MYSQL_CONTAINER_ID", ""
    )
    redis_explicit_id = os.environ.get("WN_I21_REDIS_ID", "") or os.environ.get(
        "WONIUNOTE_TEST_REDIS_CONTAINER_ID", ""
    )
    mysql_container_id = discover_container("mysql", run_id, mysql_explicit_id)
    redis_container_id = discover_container("redis", run_id, redis_explicit_id)
    verify_container(
        "mysql",
        run_id,
        int(required_env("WN_I21_DB_PORT", "WONIUNOTE_TEST_DB_PORT")),
        mysql_container_id,
        mysql_explicit_id,
    )
    verify_container(
        "redis",
        run_id,
        int(required_env("WN_I21_REDIS_PORT", "WONIUNOTE_TEST_REDIS_PORT")),
        redis_container_id,
        redis_explicit_id,
    )
    if os.environ.get("WN_I21_MYSQL_TLS_STATUS") != "DISABLED":
        fail("Linux backend plaintext transport requires the run-owned MySQL TLS-disabled readback")

    instance, instance_root, metadata_path = allocate_instance(run_dir, role)
    config_dir = instance_root / "config"
    config_dir.mkdir(mode=0o700)
    linux_config_path = config_dir / "config.integration.json"
    copied = json.loads(json.dumps(config))
    copied_app = copied["app"]
    copied_app["document_root"] = str(
        safe_resolve_under(copied_app.get("document_root"), run_dir, "document root")
    )
    copied_app["upload_path"] = str(
        safe_resolve_under(copied_app.get("upload_path"), run_dir, "upload path")
    )
    copied_log = copied_app["log"]
    copied_log["log_path"] = str(
        safe_resolve_under(copied_log.get("log_path"), run_dir, "log path")
    )
    copied["db_clients"][0]["host"] = CONTAINER_HOST_ALIAS
    copied["redis_clients"][0]["host"] = CONTAINER_HOST_ALIAS
    write_private_json(linux_config_path, copied)
    cidfile = instance_root / "backend-container.id"

    metadata = {
        "run_id": run_id,
        "instance": instance,
        "backend_container_id": None,
        "binary_sha256": sha256_file(binary),
        "runtime_image": image,
        "runtime_image_id": runtime_image_id,
        "base_image": base_image,
        "base_image_id": base_image_id,
        "runtime_spec_sha256": runtime_spec_sha256,
        "http_port": http_port,
        "credentials_included": False,
    }
    write_private_json(metadata_path, metadata)
    result = run_backend_container(
        run_dir=run_dir,
        workdir=workdir,
        config_path=linux_config_path,
        cidfile=cidfile,
        binary=binary,
        image=runtime_image_id,
        run_id=run_id,
        instance=instance,
        port=http_port,
        metadata_path=metadata_path,
        metadata=metadata,
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--launcher-path", required=True)
    parser.add_argument("config_path")
    args = parser.parse_args()
    launcher_path = Path(args.launcher_path).resolve(strict=True)
    expected_launcher = Path(__file__).with_name("launcher").resolve(strict=True)
    if launcher_path != expected_launcher:
        print("ERROR: launcher identity path mismatch.", file=sys.stderr)
        return 2
    try:
        return launch(args.config_path)
    except LaunchError as error:
        print(f"ERROR: {error}.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
