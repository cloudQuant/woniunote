"""Small, transparent loopback proxies for Iteration 21 transport faults.

The proxy never fabricates a dependency result. It forwards the request to the
owned MySQL/Redis container, then drops or delays the real server response.
Counters deliberately retain rule names and totals only; packet contents are
never logged or written to evidence.
"""

from __future__ import annotations

import ipaddress
import socket
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Optional


MAX_FRAME_BYTES = 64 * 1024 * 1024
MYSQL_CLIENT_SSL = 1 << 11
MYSQL_CLIENT_COMPRESS = 1 << 5
MYSQL_COM_QUERY = 0x03
MYSQL_COM_STMT_PREPARE = 0x16
MYSQL_COM_STMT_EXECUTE = 0x17
MYSQL_COM_STMT_CLOSE = 0x19
MYSQL_COM_RESET_CONNECTION = 0x1F


@dataclass(frozen=True)
class FaultAction:
    mode: str
    delay_seconds: float = 0.0


@dataclass
class ProxyMetrics:
    matched: int = 0
    replies_dropped: int = 0
    dropped_connection_closes: int = 0
    replies_delayed: int = 0
    delayed_replies_forwarded: int = 0
    protocol_gaps: int = 0
    connect_errors: int = 0
    accepted_connections: int = 0
    upstream_connections: int = 0
    mysql_client_packets: int = 0
    mysql_handshake_packets: int = 0
    mysql_tls_connections: int = 0
    mysql_unsupported_connections: int = 0
    mysql_command_packets: int = 0
    mysql_query_packets: int = 0
    mysql_commit_query_packets: int = 0
    mysql_statement_prepare_packets: int = 0
    mysql_statement_execute_packets: int = 0
    mysql_transaction_begin_packets: int = 0
    mysql_vote_comment_lock_packets: int = 0
    mysql_vote_business_write_packets: int = 0
    mysql_commit_candidates: int = 0
    mysql_command_codes: dict[str, int] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        return {
            "matched": self.matched,
            "replies_dropped": self.replies_dropped,
            "dropped_connection_closes": self.dropped_connection_closes,
            "replies_delayed": self.replies_delayed,
            "delayed_replies_forwarded": self.delayed_replies_forwarded,
            "protocol_gaps": self.protocol_gaps,
            "connect_errors": self.connect_errors,
            "accepted_connections": self.accepted_connections,
            "upstream_connections": self.upstream_connections,
            "mysql_client_packets": self.mysql_client_packets,
            "mysql_handshake_packets": self.mysql_handshake_packets,
            "mysql_tls_connections": self.mysql_tls_connections,
            "mysql_unsupported_connections": self.mysql_unsupported_connections,
            "mysql_command_packets": self.mysql_command_packets,
            "mysql_query_packets": self.mysql_query_packets,
            "mysql_commit_query_packets": self.mysql_commit_query_packets,
            "mysql_statement_prepare_packets": self.mysql_statement_prepare_packets,
            "mysql_statement_execute_packets": self.mysql_statement_execute_packets,
            "mysql_transaction_begin_packets": self.mysql_transaction_begin_packets,
            "mysql_vote_comment_lock_packets": self.mysql_vote_comment_lock_packets,
            "mysql_vote_business_write_packets": self.mysql_vote_business_write_packets,
            "mysql_commit_candidates": self.mysql_commit_candidates,
            "mysql_command_codes": dict(self.mysql_command_codes),
        }


@dataclass
class _Rule:
    name: str
    mode: str
    delay_seconds: float
    remaining: int = 1


@dataclass
class _Connection:
    client: socket.socket
    upstream: socket.socket
    closed: threading.Event = field(default_factory=threading.Event)
    state_lock: threading.Lock = field(default_factory=threading.Lock)
    redis_actions: Deque[Optional[FaultAction]] = field(default_factory=deque)
    mysql_actions: Deque[FaultAction] = field(default_factory=deque)
    mysql_handshake_seen: bool = False
    mysql_tls: bool = False
    mysql_unsupported: bool = False
    mysql_prepared_commits: "MysqlPreparedCommitTracker" = field(
        default_factory=lambda: MysqlPreparedCommitTracker()
    )
    mysql_prepared_vote_comment_locks: "MysqlPreparedVoteCommentLockTracker" = field(
        default_factory=lambda: MysqlPreparedVoteCommentLockTracker()
    )
    redis_unsupported: bool = False

    def close(self) -> None:
        if self.closed.is_set():
            return
        self.closed.set()
        for sock in (self.client, self.upstream):
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass


class TransparentFaultProxy:
    """A bounded, packet-aware proxy restricted to a loopback upstream."""

    def __init__(self, protocol: str, upstream_host: str, upstream_port: int):
        if protocol not in {"mysql", "redis"}:
            raise ValueError("protocol must be mysql or redis")
        try:
            upstream_ip = ipaddress.ip_address(upstream_host)
        except ValueError as error:
            raise ValueError("upstream must be a numeric loopback address") from error
        if not upstream_ip.is_loopback:
            raise ValueError("upstream must be loopback")
        if not 1 <= int(upstream_port) <= 65535:
            raise ValueError("upstream port is invalid")

        self.protocol = protocol
        self.upstream_host = str(upstream_ip)
        self.upstream_port = int(upstream_port)
        self.host = "127.0.0.1"
        self.port = 0
        self.metrics = ProxyMetrics()
        # Keep a second, non-resetting view so test setup traffic can establish
        # whether the application connected through this proxy before a fault
        # rule was armed. In particular, resetting per-case counters must not
        # erase evidence that an existing MySQL connection switched to TLS or
        # another unsupported wire mode.
        self.lifetime_metrics = ProxyMetrics()
        self._metrics_lock = threading.Lock()
        self._rule_lock = threading.Lock()
        self._rule: Optional[_Rule] = None
        self._stop = threading.Event()
        self._listener: Optional[socket.socket] = None
        self._accept_thread: Optional[threading.Thread] = None
        self._threads: list[threading.Thread] = []
        self._sockets: set[socket.socket] = set()
        self._socket_lock = threading.Lock()

    def start(self) -> "TransparentFaultProxy":
        if self._listener is not None:
            raise RuntimeError("proxy already started")
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self.host, 0))
        listener.listen(32)
        listener.settimeout(0.2)
        self.port = listener.getsockname()[1]
        self._listener = listener
        thread = threading.Thread(
            target=self._accept_loop,
            name=f"iter21-{self.protocol}-accept",
            daemon=False,
        )
        self._accept_thread = thread
        thread.start()
        return self

    def arm(self, name: str, mode: str, *, delay_seconds: float = 0.0) -> None:
        if mode not in {"drop", "delay"}:
            raise ValueError("fault mode must be drop or delay")
        if mode == "delay" and not 0 < delay_seconds <= 4.0:
            raise ValueError("delay must be greater than zero and at most four seconds")
        with self._rule_lock:
            if self._rule is not None and self._rule.remaining:
                raise RuntimeError("an armed fault rule is already pending")
            self._rule = _Rule(name=name, mode=mode, delay_seconds=delay_seconds)

    def snapshot(self) -> dict[str, Any]:
        with self._metrics_lock:
            current = self.metrics.snapshot()
            current["lifetime"] = self.lifetime_metrics.snapshot()
            return current

    def reset_metrics(self) -> None:
        with self._metrics_lock:
            self.metrics = ProxyMetrics()

    def stop(self) -> None:
        if self._stop.is_set():
            return
        self._stop.set()
        listener = self._listener
        if listener is not None:
            try:
                listener.close()
            except OSError:
                pass
        accept_thread = self._accept_thread
        if accept_thread is not None:
            accept_thread.join(timeout=2.0)

        with self._socket_lock:
            sockets = list(self._sockets)
        for sock in sockets:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass

        for thread in list(self._threads):
            thread.join(timeout=5.0)

    def _add_metric(self, field_name: str, amount: int = 1) -> None:
        with self._metrics_lock:
            setattr(self.metrics, field_name, getattr(self.metrics, field_name) + amount)
            setattr(
                self.lifetime_metrics,
                field_name,
                getattr(self.lifetime_metrics, field_name) + amount,
            )

    def _add_command_code(self, command: int) -> None:
        # MySQL command IDs are protocol categories only; never retain SQL or
        # packet payloads in metrics.
        key = f"0x{command:02x}"
        with self._metrics_lock:
            self.metrics.mysql_command_codes[key] = (
                self.metrics.mysql_command_codes.get(key, 0) + 1
            )
            self.lifetime_metrics.mysql_command_codes[key] = (
                self.lifetime_metrics.mysql_command_codes.get(key, 0) + 1
            )

    def _accept_loop(self) -> None:
        listener = self._listener
        if listener is None:
            return
        while not self._stop.is_set():
            try:
                client, _peer = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            client.settimeout(0.25)
            try:
                upstream = socket.create_connection(
                    (self.upstream_host, self.upstream_port), timeout=2.0
                )
                upstream.settimeout(0.25)
            except OSError:
                self._add_metric("connect_errors")
                client.close()
                continue

            self._add_metric("accepted_connections")
            self._add_metric("upstream_connections")

            connection = _Connection(client=client, upstream=upstream)
            with self._socket_lock:
                self._sockets.update((client, upstream))
            for target, name in (
                (self._client_to_upstream, "client-to-upstream"),
                (self._upstream_to_client, "upstream-to-client"),
            ):
                thread = threading.Thread(
                    target=self._pump_guarded,
                    args=(connection, target),
                    name=f"iter21-{self.protocol}-{name}",
                    daemon=False,
                )
                self._threads.append(thread)
                thread.start()

    def _pump_guarded(self, connection: _Connection, pump) -> None:
        try:
            pump(connection)
        finally:
            connection.close()

    def _client_to_upstream(self, connection: _Connection) -> None:
        pending = bytearray()
        while not self._stop.is_set() and not connection.closed.is_set():
            try:
                chunk = connection.client.recv(65536)
            except socket.timeout:
                continue
            except OSError:
                return
            if not chunk:
                return

            if self.protocol == "mysql" and (
                connection.mysql_tls or connection.mysql_unsupported
            ):
                self._send(connection.upstream, chunk)
                continue
            if self.protocol == "redis" and connection.redis_unsupported:
                self._send(connection.upstream, chunk)
                continue

            pending.extend(chunk)
            try:
                if self.protocol == "mysql":
                    ready_size, packets = extract_mysql_packets(pending)
                    for payload in packets:
                        self._add_metric("mysql_client_packets")
                        if not connection.mysql_handshake_seen:
                            connection.mysql_handshake_seen = True
                            self._add_metric("mysql_handshake_packets")
                            capabilities = mysql_client_capabilities(payload)
                            if is_mysql_ssl_request(payload):
                                connection.mysql_tls = True
                                self._add_metric("protocol_gaps")
                                self._add_metric("mysql_tls_connections")
                            elif capabilities & MYSQL_CLIENT_COMPRESS:
                                connection.mysql_unsupported = True
                                self._add_metric("protocol_gaps")
                                self._add_metric("mysql_unsupported_connections")
                        elif not connection.mysql_tls and not connection.mysql_unsupported:
                            action = None
                            command = payload[0] if payload else -1
                            self._add_metric("mysql_command_packets")
                            self._add_command_code(command)
                            if command == MYSQL_COM_QUERY:
                                self._add_metric("mysql_query_packets")
                                if is_mysql_commit(payload):
                                    self._add_metric("mysql_commit_query_packets")
                                    self._add_metric("mysql_commit_candidates")
                                    action = self._consume_rule("mysql.commit")
                                elif is_mysql_transaction_begin(payload):
                                    self._add_metric("mysql_transaction_begin_packets")
                                    action = self._consume_rule("mysql.begin")
                                elif is_mysql_vote_comment_lock_query(payload[1:]):
                                    self._add_metric("mysql_vote_comment_lock_packets")
                                    action = self._consume_rule("mysql.vote.comment_lock")
                                elif is_mysql_vote_business_write_query(payload[1:]):
                                    self._add_metric("mysql_vote_business_write_packets")
                                    action = self._consume_rule("mysql.vote.business_write")
                            elif command == MYSQL_COM_STMT_PREPARE:
                                self._add_metric("mysql_statement_prepare_packets")
                                with connection.state_lock:
                                    connection.mysql_prepared_vote_comment_locks.track_prepare(payload)
                                    is_commit_prepare = connection.mysql_prepared_commits.track_prepare(
                                        payload
                                    )
                                if is_commit_prepare:
                                    self._add_metric("mysql_commit_candidates")
                            elif command == MYSQL_COM_STMT_EXECUTE:
                                self._add_metric("mysql_statement_execute_packets")
                                with connection.state_lock:
                                    is_commit_execute = (
                                        connection.mysql_prepared_commits.is_commit_execute(payload)
                                    )
                                    is_vote_comment_lock_execute = (
                                        connection.mysql_prepared_vote_comment_locks
                                        .is_vote_comment_lock_execute(payload)
                                    )
                                if is_commit_execute:
                                    self._add_metric("mysql_commit_candidates")
                                    action = self._consume_rule("mysql.commit")
                                if is_vote_comment_lock_execute:
                                    self._add_metric("mysql_vote_comment_lock_packets")
                                    action = self._consume_rule("mysql.vote.comment_lock")
                            elif command == MYSQL_COM_STMT_CLOSE and len(payload) >= 5:
                                statement_id = int.from_bytes(payload[1:5], "little")
                                with connection.state_lock:
                                    connection.mysql_prepared_commits.close_statement(statement_id)
                                    connection.mysql_prepared_vote_comment_locks.close_statement(
                                        statement_id
                                    )
                            elif command == MYSQL_COM_RESET_CONNECTION:
                                with connection.state_lock:
                                    connection.mysql_prepared_commits.reset()
                                    connection.mysql_prepared_vote_comment_locks.reset()
                            if action is not None:
                                with connection.state_lock:
                                    connection.mysql_actions.append(action)
                    if ready_size:
                        ready = bytes(pending[:ready_size])
                        del pending[:ready_size]
                        self._send(connection.upstream, ready)
                    if (connection.mysql_tls or connection.mysql_unsupported) and pending:
                        self._send(connection.upstream, bytes(pending))
                        pending.clear()
                else:
                    ready_size, commands = extract_resp_commands(pending)
                    for args in commands:
                        action = None
                        if is_redis_auth_write(args):
                            action = self._consume_rule(redis_rule_name(args))
                        with connection.state_lock:
                            connection.redis_actions.append(action)
                    if ready_size:
                        ready = bytes(pending[:ready_size])
                        del pending[:ready_size]
                        self._send(connection.upstream, ready)
            except (ValueError, OverflowError):
                if self.protocol == "redis":
                    connection.redis_unsupported = True
                    self._add_metric("protocol_gaps")
                    self._send(connection.upstream, bytes(pending))
                    pending.clear()
                else:
                    connection.mysql_unsupported = True
                    self._add_metric("protocol_gaps")
                    self._add_metric("mysql_unsupported_connections")
                    self._send(connection.upstream, bytes(pending))
                    pending.clear()

    def _upstream_to_client(self, connection: _Connection) -> None:
        pending = bytearray()
        while not self._stop.is_set() and not connection.closed.is_set():
            try:
                chunk = connection.upstream.recv(65536)
            except socket.timeout:
                continue
            except OSError:
                return
            if not chunk:
                return

            if self.protocol == "mysql" and (
                connection.mysql_tls or connection.mysql_unsupported
            ):
                self._send(connection.client, chunk)
                continue

            pending.extend(chunk)
            try:
                if self.protocol == "mysql":
                    ready_size, frames = extract_mysql_frames(pending)
                    for frame in frames:
                        self._observe_mysql_prepare_reply(connection, frame)
                        action = None
                        with connection.state_lock:
                            if connection.mysql_actions:
                                action = connection.mysql_actions.popleft()
                        if self._apply_reply_action(connection, frame, action):
                            return
                    if ready_size:
                        del pending[:ready_size]
                else:
                    ready_size, frames = extract_resp_frames(pending)
                    for frame in frames:
                        with connection.state_lock:
                            action = connection.redis_actions.popleft() if connection.redis_actions else None
                        if self._apply_reply_action(connection, frame, action):
                            return
                    if ready_size:
                        del pending[:ready_size]
            except (ValueError, OverflowError):
                if self.protocol == "redis":
                    connection.redis_unsupported = True
                    self._add_metric("protocol_gaps")
                    self._send(connection.client, bytes(pending))
                    pending.clear()
                else:
                    connection.mysql_unsupported = True
                    self._add_metric("protocol_gaps")
                    self._send(connection.client, bytes(pending))
                    pending.clear()

    def _observe_mysql_prepare_reply(self, connection: _Connection, frame: bytes) -> None:
        with connection.state_lock:
            connection.mysql_prepared_commits.observe_prepare_reply(frame)
            connection.mysql_prepared_vote_comment_locks.observe_prepare_reply(frame)

    def _apply_reply_action(
        self, connection: _Connection, frame: bytes, action: Optional[FaultAction]
    ) -> bool:
        client = connection.client
        if action is None:
            self._send(client, frame)
            return False
        if action.mode == "drop":
            self._add_metric("replies_dropped")
            self._add_metric("dropped_connection_closes")
            # The server already executed the command and sent this response.
            # Close the stream so a pooled client cannot reuse a connection
            # whose ordered reply sequence now has a hole.
            connection.close()
            return True
        if action.mode == "delay":
            self._add_metric("replies_delayed")
            time.sleep(action.delay_seconds)
            if self._stop.is_set():
                return False
            if self._send(client, frame):
                self._add_metric("delayed_replies_forwarded")
        return False

    def _send(self, sock: socket.socket, payload: bytes) -> bool:
        if not payload or self._stop.is_set():
            return False
        try:
            sock.sendall(payload)
            return True
        except OSError:
            return False

    def _consume_rule(self, expected_name: str) -> Optional[FaultAction]:
        with self._rule_lock:
            rule = self._rule
            if rule is None or rule.remaining <= 0 or rule.name != expected_name:
                return None
            rule.remaining -= 1
            action = FaultAction(rule.mode, rule.delay_seconds)
        self._add_metric("matched")
        return action


def extract_mysql_packets(buffer: bytearray) -> tuple[int, list[bytes]]:
    """Return the complete prefix length and its classic MySQL payloads."""
    offset = 0
    payloads: list[bytes] = []
    while len(buffer) - offset >= 4:
        packet_length = (
            buffer[offset]
            | (buffer[offset + 1] << 8)
            | (buffer[offset + 2] << 16)
        )
        if packet_length > MAX_FRAME_BYTES:
            raise ValueError("MySQL packet is larger than the inspection limit")
        end = offset + 4 + packet_length
        if end > len(buffer):
            break
        payloads.append(bytes(buffer[offset + 4 : end]))
        offset = end
    return offset, payloads


def extract_mysql_frames(buffer: bytearray) -> tuple[int, list[bytes]]:
    size, _payloads = extract_mysql_packets(buffer)
    frames: list[bytes] = []
    offset = 0
    while offset < size:
        packet_length = buffer[offset] | (buffer[offset + 1] << 8) | (buffer[offset + 2] << 16)
        end = offset + 4 + packet_length
        frames.append(bytes(buffer[offset:end]))
        offset = end
    return size, frames


def is_mysql_ssl_request(payload: bytes) -> bool:
    # The classic protocol SSLRequest is the 32-byte capability header. It is
    # not a COM_* command; CLIENT_SSL is bit 11 of its 4-byte flag field.
    return len(payload) == 32 and bool(mysql_client_capabilities(payload) & MYSQL_CLIENT_SSL)


def mysql_client_capabilities(payload: bytes) -> int:
    if len(payload) < 4:
        return 0
    return int.from_bytes(payload[:4], byteorder="little")


def is_mysql_commit(payload: bytes) -> bool:
    if not payload or payload[0] != MYSQL_COM_QUERY:
        return False
    return is_mysql_commit_query(payload[1:])


def is_mysql_transaction_begin(payload: bytes) -> bool:
    if not payload or payload[0] != MYSQL_COM_QUERY:
        return False
    try:
        query = " ".join(payload[1:].decode("ascii").strip().rstrip(";").split())
    except UnicodeDecodeError:
        return False
    return query.casefold() in {
        "begin",
        "begin work",
        "start transaction",
        "start transaction read write",
    }


def is_mysql_vote_comment_lock_query(query: bytes) -> bool:
    try:
        normalized = " ".join(query.decode("ascii").strip().rstrip(";").split())
    except UnicodeDecodeError:
        return False
    normalized = normalized.casefold()
    prefix = "select articleid, replyid, hidden from comment where commentid = "
    suffix = " for update"
    if not normalized.startswith(prefix) or not normalized.endswith(suffix):
        return False
    comment_id = normalized[len(prefix) : -len(suffix)].strip()
    return comment_id == "?" or comment_id.isdecimal()


def is_mysql_vote_business_write_query(query: bytes) -> bool:
    try:
        normalized = " ".join(query.decode("ascii").strip().rstrip(";").split())
    except UnicodeDecodeError:
        return False
    normalized = normalized.casefold()
    prefix = (
        "insert into comment_votes "
        "(commentid, userid, vote_type, createtime) values ("
    )
    suffix = ", now())"
    if not normalized.startswith(prefix) or not normalized.endswith(suffix):
        return False
    values = [value.strip() for value in normalized[len(prefix) : -len(suffix)].split(",")]
    return (
        len(values) == 3
        and values[0].isdecimal()
        and values[1].isdecimal()
        and (values[2].isdecimal() or values[2] == "-1")
    )


def is_mysql_commit_prepare(payload: bytes) -> bool:
    return bool(payload) and payload[0] == MYSQL_COM_STMT_PREPARE and is_mysql_commit_query(
        payload[1:]
    )


def is_mysql_vote_comment_lock_prepare(payload: bytes) -> bool:
    return (
        bool(payload)
        and payload[0] == MYSQL_COM_STMT_PREPARE
        and is_mysql_vote_comment_lock_query(payload[1:])
    )


def mysql_commit_execute_statement_id(payload: bytes) -> Optional[int]:
    if len(payload) < 5 or payload[0] != MYSQL_COM_STMT_EXECUTE:
        return None
    return int.from_bytes(payload[1:5], "little")


def mysql_prepare_response_statement_id(frame: bytes) -> Optional[int]:
    if len(frame) < 16:
        return None
    payload = frame[4:]
    if payload[0] != 0x00:
        return None
    return int.from_bytes(payload[1:5], "little")


@dataclass
class MysqlPreparedCommitTracker:
    """Correlate prepared COMMIT statements without retaining SQL text."""

    pending_prepares: int = 0
    statement_ids: set[int] = field(default_factory=set)

    def track_prepare(self, payload: bytes) -> bool:
        if not is_mysql_commit_prepare(payload):
            return False
        self.pending_prepares += 1
        return True

    def observe_prepare_reply(self, frame: bytes) -> None:
        if self.pending_prepares <= 0:
            return
        payload = frame[4:] if len(frame) >= 4 else b""
        if payload[:1] == b"\xFF":  # ERR packet: this statement was not prepared.
            self.pending_prepares -= 1
            return
        statement_id = mysql_prepare_response_statement_id(frame)
        if statement_id is not None:
            self.statement_ids.add(statement_id)
            self.pending_prepares -= 1

    def is_commit_execute(self, payload: bytes) -> bool:
        statement_id = mysql_commit_execute_statement_id(payload)
        return statement_id is not None and statement_id in self.statement_ids

    def close_statement(self, statement_id: int) -> None:
        self.statement_ids.discard(statement_id)

    def reset(self) -> None:
        self.statement_ids.clear()
        self.pending_prepares = 0


@dataclass
class MysqlPreparedVoteCommentLockTracker:
    """Track prepared comment-lock SELECTs without retaining query text."""

    pending_prepares: Deque[bool] = field(default_factory=deque)
    statement_ids: set[int] = field(default_factory=set)

    def track_prepare(self, payload: bytes) -> None:
        if payload and payload[0] == MYSQL_COM_STMT_PREPARE:
            self.pending_prepares.append(is_mysql_vote_comment_lock_prepare(payload))

    def observe_prepare_reply(self, frame: bytes) -> None:
        if not self.pending_prepares:
            return
        is_vote_comment_lock = self.pending_prepares.popleft()
        if not is_vote_comment_lock:
            return
        payload = frame[4:] if len(frame) >= 4 else b""
        if payload[:1] == b"\xFF":
            return
        statement_id = mysql_prepare_response_statement_id(frame)
        if statement_id is not None:
            self.statement_ids.add(statement_id)

    def is_vote_comment_lock_execute(self, payload: bytes) -> bool:
        statement_id = mysql_commit_execute_statement_id(payload)
        return statement_id is not None and statement_id in self.statement_ids

    def close_statement(self, statement_id: int) -> None:
        self.statement_ids.discard(statement_id)

    def reset(self) -> None:
        self.statement_ids.clear()
        self.pending_prepares.clear()


def is_mysql_commit_query(query_bytes: bytes) -> bool:
    try:
        query = query_bytes.decode("ascii").strip().rstrip(";").strip()
    except UnicodeDecodeError:
        return False
    return query.casefold() in {"commit", "commit work"}


class _NeedMoreData(Exception):
    pass


def _read_resp_line(data: bytearray, offset: int) -> tuple[int, bytes]:
    end = data.find(b"\r\n", offset)
    if end < 0:
        raise _NeedMoreData
    return end + 2, bytes(data[offset:end])


def _parse_resp_value(data: bytearray, offset: int = 0):
    if offset >= len(data):
        raise _NeedMoreData
    prefix = bytes(data[offset : offset + 1])
    if prefix == b">":
        # Push messages do not correspond to a queued command response. Keep
        # the stream transparent and fail the integration case as a GAP.
        raise ValueError("RESP push frames are outside the inspected command path")
    if prefix in {b"+", b"-", b":", b",", b"#", b"(", b"_"}:
        line_end, line = _read_resp_line(data, offset + 1)
        if prefix == b":":
            try:
                return line_end, int(line), False
            except ValueError as error:
                raise ValueError("invalid RESP integer") from error
        return line_end, line, False
    if prefix in {b"$", b"=", b"!", b"*", b"~", b">", b"%", b"|"}:
        line_end, line = _read_resp_line(data, offset + 1)
        try:
            count = int(line)
        except ValueError as error:
            raise ValueError("invalid RESP length") from error
        if count == -1:
            return line_end, None, False
        if count < -1 or count > MAX_FRAME_BYTES:
            raise ValueError("RESP length is outside the inspection limit")
        if prefix in {b"$", b"=", b"!"}:
            end = line_end + count + 2
            if end > len(data):
                raise _NeedMoreData
            if data[end - 2 : end] != b"\r\n":
                raise ValueError("invalid RESP bulk terminator")
            return end, bytes(data[line_end : line_end + count]), False
        child_count = count * 2 if prefix in {b"%", b"|"} else count
        if child_count > MAX_FRAME_BYTES:
            raise ValueError("RESP aggregate is outside the inspection limit")
        values = []
        cursor = line_end
        for _ in range(child_count):
            cursor, value, _ = _parse_resp_value(data, cursor)
            values.append(value)
        if prefix == b"|":
            cursor, value, _ = _parse_resp_value(data, cursor)
            return cursor, value, False
        return cursor, values, False
    raise ValueError("unsupported RESP frame")


def extract_resp_commands(buffer: bytearray) -> tuple[int, list[list[bytes]]]:
    offset = 0
    commands: list[list[bytes]] = []
    while offset < len(buffer):
        try:
            end, value, _ = _parse_resp_value(buffer, offset)
        except _NeedMoreData:
            break
        if not isinstance(value, list) or not all(isinstance(arg, bytes) for arg in value):
            raise ValueError("Redis request is not a flat RESP array")
        commands.append(value)
        offset = end
    return offset, commands


def extract_resp_frames(buffer: bytearray) -> tuple[int, list[bytes]]:
    offset = 0
    frames: list[bytes] = []
    while offset < len(buffer):
        try:
            end, _value, _ = _parse_resp_value(buffer, offset)
        except _NeedMoreData:
            break
        frames.append(bytes(buffer[offset:end]))
        offset = end
    return offset, frames


def is_redis_auth_write(args: list[bytes]) -> bool:
    if len(args) < 2:
        return False
    command = args[0].upper()
    if command == b"SET":
        return args[1].startswith(b"refresh_jti:")
    if command == b"EVAL" and len(args) >= 4:
        try:
            key_count = int(args[2])
        except ValueError:
            return False
        return key_count == 1 and args[3].startswith(b"refresh_jti:")
    return False


def redis_rule_name(args: list[bytes]) -> str:
    return "redis.login_set" if args and args[0].upper() == b"SET" else "redis.refresh_eval"
