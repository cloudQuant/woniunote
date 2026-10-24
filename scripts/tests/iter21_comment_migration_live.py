#!/usr/bin/env python3
"""Exercise the comment-vote migration against this run's isolated MySQL service.

The script refuses to connect until iter21_support verifies the exact labeled
runner container and loopback mapping. All writes are limited to scratch
databases derived from the runner's run ID; no host MySQL fallback exists.
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "scripts" / "migrate_comment_votes.py"
INTEGRATION_DIR = ROOT / "backend_cpp" / "tests" / "integration"
sys.path.insert(0, str(INTEGRATION_DIR))

import iter21_support  # noqa: E402


def _run_identity() -> tuple[str, str]:
    run_id = os.environ.get("WONIUNOTE_TEST_RUN_ID", "")
    container_id = os.environ.get("WONIUNOTE_TEST_MYSQL_CONTAINER", "")
    if not run_id or not container_id:
        raise RuntimeError("runner-owned MySQL identity is unavailable")
    return run_id, container_id


def _validate_scratch_name(database: str) -> None:
    run_id, _ = _run_identity()
    allowed_prefix = f"w_i21v_{run_id.replace('-', '')}_"
    if not database.startswith(allowed_prefix) or len(database) > 64:
        raise RuntimeError("refusing a database outside this run's vote-migration scratch scope")
    suffix = database[len(allowed_prefix):]
    if not suffix or any(not (char.isalnum() or char == "_") for char in suffix):
        raise RuntimeError("invalid run-owned scratch database name")


def _verified_connection(database: str | None = None):
    """Return a connection only after checking the exact runner-owned service."""
    if database is not None:
        _validate_scratch_name(database)
    connection = iter21_support.owned_mysql_connection()
    # This standalone live harness consumes rows by column name. Keep the
    # shared integration helper's default tuple cursor unchanged for its tests.
    from pymysql.cursors import DictCursor

    connection.cursorclass = DictCursor
    connection.autocommit(True)
    if database is not None:
        connection.select_db(database)
    return connection


def _scratch_name(suffix: str) -> str:
    run_id, _ = _run_identity()
    safe_suffix = "".join(char for char in suffix.lower() if char.isalnum() or char == "_")
    if not safe_suffix:
        raise RuntimeError("invalid scratch database suffix")
    name = f"w_i21v_{run_id.replace('-', '')}_{safe_suffix}"
    if len(name) > 64:
        raise RuntimeError("scratch database name exceeds MySQL's limit")
    return name


def _create_database(name: str) -> None:
    _validate_scratch_name(name)
    connection = _verified_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    finally:
        connection.close()


def _drop_database(name: str) -> None:
    _validate_scratch_name(name)
    connection = _verified_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{name}`")
    finally:
        connection.close()


def _connect_scratch(name: str):
    _validate_scratch_name(name)
    connection = _verified_connection()
    try:
        connection.select_db(name)
        return connection
    except Exception:
        connection.close()
        raise


def _create_base_tables(connection: Any) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "CREATE TABLE comment ("
            "commentid INT NOT NULL, agreecount INT NOT NULL DEFAULT 0, "
            "opposecount INT NOT NULL DEFAULT 0, PRIMARY KEY (commentid)"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        )
        cursor.execute(
            "CREATE TABLE users (userid INT NOT NULL, PRIMARY KEY (userid)) "
            "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        )


def _create_vote_table(connection: Any, table: str) -> None:
    if table not in {"comment_vote", "comment_votes"}:
        raise RuntimeError("invalid vote table name")
    with connection.cursor() as cursor:
        if table == "comment_votes":
            cursor.execute(
                "CREATE TABLE comment_votes ("
                "id INT NOT NULL AUTO_INCREMENT, commentid INT NOT NULL, userid INT NOT NULL, "
                "vote_type TINYINT NOT NULL, createtime DATETIME DEFAULT CURRENT_TIMESTAMP, "
                "PRIMARY KEY (id), UNIQUE KEY uk_comment_user (commentid, userid), "
                "KEY idx_userid (userid), "
                "CONSTRAINT fk_i21_comment FOREIGN KEY (commentid) REFERENCES comment(commentid) ON DELETE CASCADE, "
                "CONSTRAINT fk_i21_user FOREIGN KEY (userid) REFERENCES users(userid) ON DELETE CASCADE"
                ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
            )
        else:
            cursor.execute(
                "CREATE TABLE comment_vote ("
                "id INT NOT NULL AUTO_INCREMENT, commentid INT NOT NULL, userid INT NOT NULL, "
                "vote_type TINYINT NOT NULL, createtime DATETIME DEFAULT CURRENT_TIMESTAMP, "
                "PRIMARY KEY (id)"
                ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
            )


def _seed_base(connection: Any, *, counts: dict[int, tuple[int, int]], user_ids: set[int]) -> None:
    with connection.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO comment (commentid, agreecount, opposecount) VALUES (%s, %s, %s)",
            [(comment_id, agree, oppose) for comment_id, (agree, oppose) in sorted(counts.items())],
        )
        cursor.executemany("INSERT INTO users (userid) VALUES (%s)", [(user_id,) for user_id in sorted(user_ids)])


def _seed_votes(connection: Any, table: str, rows: list[tuple[int, int, int, int]]) -> None:
    if table not in {"comment_vote", "comment_votes"}:
        raise RuntimeError("invalid vote table name")
    with connection.cursor() as cursor:
        cursor.executemany(
            f"INSERT INTO `{table}` (id, commentid, userid, vote_type, createtime) "
            "VALUES (%s, %s, %s, %s, '2026-10-23 12:00:00')",
            rows,
        )


def _encode_backup_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, bytes):
        return {"__bytes_hex__": value.hex()}
    return value


def _decode_backup_value(value: Any) -> Any:
    if isinstance(value, dict) and set(value) == {"__bytes_hex__"}:
        return bytes.fromhex(value["__bytes_hex__"])
    return value


def _make_backup(connection: Any, path: Path) -> str:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT table_name AS table_name FROM information_schema.tables "
            "WHERE table_schema=DATABASE() AND table_name IN "
            "('comment', 'users', 'comment_vote', 'comment_votes') ORDER BY table_name"
        )
        table_names = [row["table_name"] for row in cursor.fetchall()]
        backup: dict[str, Any] = {"format": "iter21-json-logical-backup-v1", "tables": {}}
        for table in table_names:
            cursor.execute(f"SHOW CREATE TABLE `{table}`")
            create_row = cursor.fetchone()
            create_sql = create_row.get("Create Table") or create_row.get("Create View")
            if not create_sql:
                raise RuntimeError("could not read scratch table DDL for backup")
            primary_key = "userid" if table == "users" else "commentid" if table == "comment" else "id"
            cursor.execute(f"SELECT * FROM `{table}` ORDER BY `{primary_key}`")
            rows = [
                {key: _encode_backup_value(value) for key, value in row.items()}
                for row in cursor.fetchall()
            ]
            columns = list(rows[0]) if rows else _column_names(cursor, table)
            backup["tables"][table] = {"create_sql": create_sql, "columns": columns, "rows": rows}
    path.write_text(json.dumps(backup, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _column_names(cursor: Any, table: str) -> list[str]:
    cursor.execute(
        "SELECT column_name AS column_name FROM information_schema.columns "
        "WHERE table_schema=DATABASE() AND table_name=%s ORDER BY ordinal_position",
        (table,),
    )
    return [row["column_name"] for row in cursor.fetchall()]


def _restore_and_verify(backup_path: Path, restore_database: str) -> None:
    backup = json.loads(backup_path.read_text(encoding="utf-8"))
    if backup.get("format") != "iter21-json-logical-backup-v1":
        raise RuntimeError("unexpected logical backup format")
    _create_database(restore_database)
    connection = _connect_scratch(restore_database)
    try:
        tables = backup["tables"]
        order = [table for table in ("comment", "users", "comment_vote", "comment_votes") if table in tables]
        with connection.cursor() as cursor:
            for table in order:
                cursor.execute(tables[table]["create_sql"])
            for table in order:
                table_backup = tables[table]
                columns = table_backup["columns"]
                if not table_backup["rows"]:
                    continue
                names = ", ".join(f"`{name}`" for name in columns)
                placeholders = ", ".join(["%s"] * len(columns))
                values = [
                    tuple(_decode_backup_value(row[name]) for name in columns)
                    for row in table_backup["rows"]
                ]
                cursor.executemany(f"INSERT INTO `{table}` ({names}) VALUES ({placeholders})", values)

        restored: dict[str, list[dict[str, Any]]] = {}
        with connection.cursor() as cursor:
            for table in order:
                primary_key = "userid" if table == "users" else "commentid" if table == "comment" else "id"
                cursor.execute(f"SELECT * FROM `{table}` ORDER BY `{primary_key}`")
                restored[table] = [
                    {key: _encode_backup_value(value) for key, value in row.items()}
                    for row in cursor.fetchall()
                ]
        if restored != {table: tables[table]["rows"] for table in order}:
            raise RuntimeError("logical backup restore did not reproduce all fixture rows")
    finally:
        connection.close()


def _migration_env(database: str) -> dict[str, str]:
    run_id, _ = _run_identity()
    environment = os.environ.copy()
    environment.update(
        {
            "DB_HOST": os.environ["WONIUNOTE_TEST_DB_HOST"],
            "DB_PORT": os.environ["WONIUNOTE_TEST_DB_PORT"],
            "DB_NAME": database,
            "DB_USER": os.environ["WONIUNOTE_TEST_DB_USER"],
            "DB_PASS": os.environ["WONIUNOTE_TEST_DB_PASSWORD"],
        }
    )
    environment["WONIUNOTE_TEST_RUN_ID"] = run_id
    return environment


def _command(database: str, args: list[str]) -> list[str]:
    return [
        sys.executable,
        str(MIGRATION),
        "--host",
        os.environ["WONIUNOTE_TEST_DB_HOST"],
        "--port",
        os.environ["WONIUNOTE_TEST_DB_PORT"],
        "--database",
        database,
        "--user",
        os.environ["WONIUNOTE_TEST_DB_USER"],
        *args,
    ]


def _preflight(database: str, *, allow_hard_block: bool = False) -> dict[str, Any]:
    _verified_connection().close()
    result = subprocess.run(
        _command(database, []),
        env=_migration_env(database),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in ({0, 2} if allow_hard_block else {0}):
        raise RuntimeError(f"migration preflight failed for {database}; see CLI status {result.returncode}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("migration preflight did not return JSON") from exc


def _apply(database: str, report: dict[str, Any], backup_path: Path,
           backup_sha256: str, approval_path: Path, migration_run_id: str) -> dict[str, Any]:
    approval_path.write_text(
        json.dumps(report["approval_template"], sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    _verified_connection().close()
    command = _command(
        database,
        [
            "--apply",
            "--run-id",
            migration_run_id,
            "--writes-frozen-run-id",
            migration_run_id,
            "--backup-file",
            str(backup_path),
            "--backup-sha256",
            backup_sha256,
            "--backup-restore-verified",
            "--preserve-comment-counts",
            "--approved-preflight-sha256",
            report["snapshot_sha256"],
            "--approval-file",
            str(approval_path),
        ],
    )
    result = subprocess.run(command, env=_migration_env(database), capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"migration apply failed for {database}; CLI status {result.returncode}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("migration apply did not return JSON") from exc


def _table_rows(connection: Any, table: str) -> list[dict[str, Any]]:
    if table not in {"comment_vote", "comment_votes"}:
        raise RuntimeError("invalid vote table name")
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT id, commentid, userid, vote_type FROM `{table}` ORDER BY id")
        return list(cursor.fetchall())


def _table_exists(connection: Any, table: str) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) AS n FROM information_schema.tables "
            "WHERE table_schema=DATABASE() AND table_name=%s",
            (table,),
        )
        return cursor.fetchone()["n"] == 1


def _comment_counts(connection: Any) -> dict[int, tuple[int, int]]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT commentid, agreecount, opposecount FROM comment ORDER BY commentid")
        return {row["commentid"]: (row["agreecount"], row["opposecount"]) for row in cursor.fetchall()}


def _prepare_case(name: str, *, counts: dict[int, tuple[int, int]], user_ids: set[int],
                  legacy: list[tuple[int, int, int, int]] | None = None,
                  canonical: list[tuple[int, int, int, int]] | None = None) -> str:
    database = _scratch_name(name)
    _create_database(database)
    connection = _connect_scratch(database)
    try:
        _create_base_tables(connection)
        _seed_base(connection, counts=counts, user_ids=user_ids)
        if legacy is not None:
            _create_vote_table(connection, "comment_vote")
            _seed_votes(connection, "comment_vote", legacy)
        if canonical is not None:
            _create_vote_table(connection, "comment_votes")
            _seed_votes(connection, "comment_votes", canonical)
    finally:
        connection.close()
    return database


def _prepare_approval_artifacts(
    database: str, temp_dir: Path, case: str, *, allow_hard_block: bool = False
) -> tuple[dict[str, Any], Path, str, Path]:
    backup_path = temp_dir / f"{case}.backup.json"
    approval_path = temp_dir / f"{case}.approval.json"
    connection = _connect_scratch(database)
    try:
        backup_sha256 = _make_backup(connection, backup_path)
    finally:
        connection.close()
    restore_database = _scratch_name(f"restore_{case}")
    _restore_and_verify(backup_path, restore_database)
    connection = _connect_scratch(restore_database)
    try:
        if not _table_exists(connection, "comment") or not _table_exists(connection, "users"):
            raise RuntimeError("backup restore omitted base reference tables")
    finally:
        connection.close()
    _drop_database(restore_database)
    report = _preflight(database, allow_hard_block=allow_hard_block)
    return report, backup_path, backup_sha256, approval_path


def _migration_run_id(case: str) -> str:
    run_id, _ = _run_identity()
    return f"{run_id}-comment-votes-{case}"


def _exercise_four_states(temp_dir: Path, evidence: dict[str, Any]) -> None:
    cases = [
        ("none", {}, set(), None, None, "none"),
        ("legacy", {10: (1, 0), 20: (0, 1)}, {1, 2}, [(1, 10, 1, 1), (2, 20, 2, -1)], None, "legacy_only"),
        ("canonical", {10: (1, 0)}, {1}, None, [(1, 10, 1, 1)], "canonical_only"),
        # Same-direction duplicate source records remain intact in the legacy
        # table; the approved copy keeps one logical vote and reallocates the
        # selected source ID that collides with a different canonical vote.
        ("both", {10: (1, 0), 20: (0, 1), 30: (1, 0)}, {1, 2, 3},
         [(1, 20, 2, -1), (2, 20, 2, -1)],
         [(1, 10, 1, 1), (2, 30, 3, 1)], "both"),
    ]
    summaries = []
    for name, counts, users, legacy, canonical, expected_state in cases:
        database = _prepare_case(name, counts=counts, user_ids=users, legacy=legacy, canonical=canonical)
        evidence["scratch_databases"].append(database)
        report, backup, backup_sha, approval = _prepare_approval_artifacts(database, temp_dir, name)
        if report["state"] != expected_state:
            raise RuntimeError(f"four-state fixture {name} reported {report['state']}, expected {expected_state}")
        if report["hard_blocking_findings"]:
            raise RuntimeError(f"four-state fixture {name} unexpectedly has hard blocks")
        count_connection = _connect_scratch(database)
        try:
            original_counts = _comment_counts(count_connection)
        finally:
            count_connection.close()
        applied = _apply(database, report, backup, backup_sha, approval, _migration_run_id(name))
        connection = _connect_scratch(database)
        try:
            after_counts = _comment_counts(connection)
            if after_counts != original_counts:
                raise RuntimeError(f"migration changed comment counters in {name}")
            if not _table_exists(connection, "comment_votes"):
                raise RuntimeError(f"migration did not create canonical table for {name}")
            if legacy is not None and _table_rows(connection, "comment_vote") != [
                {"id": row[0], "commentid": row[1], "userid": row[2], "vote_type": row[3]}
                for row in sorted(legacy)
            ]:
                raise RuntimeError(f"migration modified retained source rows for {name}")
            canonical_rows = _table_rows(connection, "comment_votes")
            if name == "none" and canonical_rows:
                raise RuntimeError("none-state migration did not create an empty canonical table")
            if name == "both":
                source_remaps = [row for row in applied["id_mappings"] if row["action"] == "reassigned"]
                if len(source_remaps) != 1 or source_remaps[0]["source_id"] != 1:
                    raise RuntimeError("approved source ID collision was not remapped exactly once")
                if not any(row["commentid"] == 20 and row["userid"] == 2 for row in canonical_rows):
                    raise RuntimeError("approved legacy vote was lost during collision remap")
                if len(canonical_rows) != 3:
                    raise RuntimeError("same-direction source duplicates were not consolidated as approved")
        finally:
            connection.close()
        summaries.append({"case": name, "state": expected_state, "action": applied["action"]})
    evidence["four_state_cases"] = summaries


def _exercise_opposite_conflict(temp_dir: Path, evidence: dict[str, Any]) -> None:
    database = _prepare_case(
        "opposite_conflict",
        counts={10: (1, 1)},
        user_ids={1},
        legacy=[(1, 10, 1, -1)],
        canonical=[(1, 10, 1, 1)],
    )
    evidence["scratch_databases"].append(database)
    report, backup, backup_sha, approval = _prepare_approval_artifacts(
        database, temp_dir, "opposite_conflict", allow_hard_block=True
    )
    if "opposite_direction_conflict" not in report["hard_blocking_findings"]:
        raise RuntimeError("opposite-direction conflict was not hard blocked")
    before_connection = _connect_scratch(database)
    try:
        before_legacy = _table_rows(before_connection, "comment_vote")
        before_canonical = _table_rows(before_connection, "comment_votes")
    finally:
        before_connection.close()
    approval.write_text(json.dumps(report["approval_template"], sort_keys=True), encoding="utf-8")
    _verified_connection().close()
    result = subprocess.run(
        _command(
            database,
            [
                "--apply", "--run-id", _migration_run_id("opposite"),
                "--writes-frozen-run-id", _migration_run_id("opposite"),
                "--backup-file", str(backup), "--backup-sha256", backup_sha,
                "--backup-restore-verified", "--preserve-comment-counts",
                "--approved-preflight-sha256", report["snapshot_sha256"],
                "--approval-file", str(approval),
            ],
        ),
        env=_migration_env(database), capture_output=True, text=True, check=False,
    )
    if result.returncode != 2:
        raise RuntimeError("opposite-direction conflict apply did not fail closed")
    after_connection = _connect_scratch(database)
    try:
        if _table_rows(after_connection, "comment_vote") != before_legacy:
            raise RuntimeError("conflict rejection modified the source vote table")
        if _table_rows(after_connection, "comment_votes") != before_canonical:
            raise RuntimeError("conflict rejection modified the canonical vote table")
    finally:
        after_connection.close()
    evidence["opposite_conflict"] = "blocked_without_vote_changes"


def _process_rows(connection: Any, database: str) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT ID AS id, DB AS db_name, USER AS user_name, HOST AS host_name, "
            "COMMAND AS command, STATE AS state, INFO AS info "
            "FROM information_schema.PROCESSLIST WHERE DB=%s AND INFO IS NOT NULL",
            (database,),
        )
        return list(cursor.fetchall())


def _process_row_by_id(connection: Any, process_id: int) -> dict[str, Any] | None:
    if process_id <= 0:
        raise RuntimeError("refusing to inspect an invalid MySQL connection id")
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT ID AS id, DB AS db_name, USER AS user_name, HOST AS host_name, "
            "COMMAND AS command, STATE AS state, INFO AS info "
            "FROM information_schema.PROCESSLIST WHERE ID=%s",
            (process_id,),
        )
        return cursor.fetchone()


def _matches_migration_query(
    row: dict[str, Any], database: str, query_prefix: str, state_marker: str
) -> bool:
    if (
        row.get("db_name") != database
        or row.get("user_name") != os.environ["WONIUNOTE_TEST_DB_USER"]
        or not row.get("host_name")
        or str(row.get("command", "")).upper() != "QUERY"
        or state_marker.casefold() not in str(row.get("state") or "").casefold()
    ):
        return False
    normalized_query = " ".join(str(row.get("info") or "").split()).upper()
    return normalized_query.startswith(" ".join(query_prefix.split()).upper())


def _matching_migration_processes(
    connection: Any, database: str, query_prefix: str, state_marker: str
) -> list[dict[str, Any]]:
    return [
        row for row in _process_rows(connection, database)
        if _matches_migration_query(row, database, query_prefix, state_marker)
    ]


def _kill_verified_migration_connection(
    database: str, process_id: int, query_prefix: str, state_marker: str
) -> dict[str, Any]:
    """Kill only the still-matching migration query and wait for server cleanup."""
    if process_id <= 0:
        raise RuntimeError("refusing to kill an invalid MySQL connection id")
    observer = _connect_scratch(database)
    try:
        row = _process_row_by_id(observer, process_id)
        if row is None or not _matches_migration_query(row, database, query_prefix, state_marker):
            raise RuntimeError("migration connection no longer matches the verified run/schema/query")
        identity = {
            "connection_id": process_id,
            "database": row["db_name"],
            "user": row["user_name"],
            "host": row["host_name"],
            "query_sha256": hashlib.sha256(str(row["info"]).encode("utf-8")).hexdigest(),
            "state": row["state"],
        }
        with observer.cursor() as cursor:
            # MySQL KILL uses a connection id as a literal; it is validated as
            # a positive integer above and was re-read from PROCESSLIST here.
            cursor.execute(f"KILL CONNECTION {process_id}")
    finally:
        observer.close()

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        observer = _connect_scratch(database)
        try:
            row = _process_row_by_id(observer, process_id)
        finally:
            observer.close()
        if row is None:
            identity["server_connection_cleanup"] = "processlist_id_absent_after_kill_connection"
            return identity
        if row.get("db_name") != database or row.get("user_name") != os.environ["WONIUNOTE_TEST_DB_USER"]:
            raise RuntimeError("MySQL connection id changed identity while awaiting KILL cleanup")
        time.sleep(0.1)
    raise RuntimeError("KILL CONNECTION did not remove the verified migration connection in time")


def _pause_kill_client(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        raise RuntimeError("migration client exited before the controlled process kill")
    process.send_signal(signal.SIGSTOP)
    if process.poll() is not None:
        raise RuntimeError("migration client exited while being paused")


def _sigkill_paused_client(process: subprocess.Popen[str]) -> int:
    if process.poll() is not None:
        raise RuntimeError("paused migration client exited before SIGKILL")
    process.send_signal(signal.SIGKILL)
    process.communicate(timeout=10)
    if process.returncode != -signal.SIGKILL:
        raise RuntimeError("migration client did not terminate from the expected OS SIGKILL")
    return process.returncode


def _exercise_killed_ddl(temp_dir: Path, evidence: dict[str, Any]) -> None:
    database = _prepare_case("ddl_kill", counts={10: (0, 0)}, user_ids={1})
    evidence["scratch_databases"].append(database)
    report, backup, backup_sha, approval = _prepare_approval_artifacts(database, temp_dir, "ddl_kill")
    if report["state"] != "none":
        raise RuntimeError("DDL-kill fixture did not start in the none state")
    approval.write_text(json.dumps(report["approval_template"], sort_keys=True), encoding="utf-8")

    lock_connection = _connect_scratch(database)
    process: subprocess.Popen[str] | None = None
    locked = False
    migration_connection_id: int | None = None
    server_connection_killed = False
    os_kill_returncode: int | None = None
    ddl_prefix = "CREATE TABLE IF NOT EXISTS `comment_votes` ("
    try:
        with lock_connection.cursor() as cursor:
            cursor.execute("LOCK INSTANCE FOR BACKUP")
            locked = True
        _verified_connection().close()
        process = subprocess.Popen(
            _command(
                database,
                [
                    "--apply", "--run-id", _migration_run_id("ddl_kill"),
                    "--writes-frozen-run-id", _migration_run_id("ddl_kill"),
                    "--backup-file", str(backup), "--backup-sha256", backup_sha,
                    "--backup-restore-verified", "--preserve-comment-counts",
                    "--approved-preflight-sha256", report["snapshot_sha256"],
                    "--approval-file", str(approval),
                ],
            ),
            env=_migration_env(database), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        deadline = time.monotonic() + 20
        observed_ddl_wait: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            observer = _connect_scratch(database)
            try:
                matches = _matching_migration_processes(
                    observer, database, ddl_prefix, "backup lock"
                )
            finally:
                observer.close()
            if len(matches) > 1:
                raise RuntimeError("multiple run-owned migration sessions matched the blocked canonical DDL")
            if matches:
                observed_ddl_wait = matches[0]
                break
            if process.poll() is not None:
                break
            time.sleep(0.1)
        if observed_ddl_wait is None or process.poll() is not None:
            raise RuntimeError("could not observe the migration process blocked on canonical-table DDL")
        migration_connection_id = int(observed_ddl_wait["id"])
        _pause_kill_client(process)
        ddl_connection = _kill_verified_migration_connection(
            database, migration_connection_id, ddl_prefix, "backup lock"
        )
        server_connection_killed = True
        os_kill_returncode = _sigkill_paused_client(process)
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.communicate(timeout=10)
        if locked and (migration_connection_id is None or server_connection_killed):
            try:
                with lock_connection.cursor() as cursor:
                    cursor.execute("UNLOCK INSTANCE")
            except Exception:
                pass
            lock_connection.close()
        elif not locked:
            lock_connection.close()
        # If server-side cancellation could not be confirmed, deliberately
        # keep the backup lock until the runner disposes this labeled container.

    connection = _connect_scratch(database)
    try:
        if _table_exists(connection, "comment_votes"):
            raise RuntimeError("interrupted pre-DDL process unexpectedly created the canonical table")
    finally:
        connection.close()

    retry_report = _preflight(database)
    if retry_report["state"] != "none":
        raise RuntimeError("pre-DDL interruption did not leave a clean resumable none state")
    applied = _apply(database, retry_report, backup, backup_sha, approval, _migration_run_id("ddl_retry"))
    if applied["action"] != "created_empty_canonical_table":
        raise RuntimeError("migration did not recover after the real DDL process kill")
    evidence["killed_ddl"] = {
        "connection": ddl_connection,
        "server_action": "KILL CONNECTION; processlist id confirmed absent before releasing backup lock",
        "os_pid": process.pid,
        "os_signals": ["SIGSTOP", "SIGKILL"],
        "os_sigkill_returncode": os_kill_returncode,
        "recovery": "successful_retry_after_real_blocked_DDL_interruption",
    }


def _create_sleep_trigger(connection: Any, trigger_name: str, delayed_comment_id: int) -> None:
    if not trigger_name.replace("_", "").isalnum() or delayed_comment_id <= 0:
        raise RuntimeError("invalid isolated migration trigger parameters")
    with connection.cursor() as cursor:
        cursor.execute(
            f"CREATE TRIGGER `{trigger_name}` BEFORE INSERT ON comment_votes "
            "FOR EACH ROW SET @iter21_migration_sleep = "
            f"IF(NEW.commentid = {delayed_comment_id}, SLEEP(60), 0)"
        )


def _partial_copy_diagnostics(
    process: subprocess.Popen[str], database: str
) -> dict[str, Any]:
    """Capture why the controlled second-row pause was not observed."""
    diagnostics: dict[str, Any] = {"client_returncode": process.poll()}
    connection = _connect_scratch(database)
    try:
        rows = _process_rows(connection, database)
        diagnostics["processlist_candidates"] = [
            {
                "id": row.get("id"),
                "user": row.get("user_name"),
                "command": row.get("command"),
                "state": row.get("state"),
                "query": str(row.get("info") or "")[:1200],
                "matches_expected_query": _matches_migration_query(
                    row,
                    database,
                    "SET @iter21_migration_sleep = IF(NEW.commentid = 30, SLEEP(60), 0)",
                    "user sleep",
                ),
            }
            for row in rows
        ]
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT action_statement AS action_statement "
                "FROM information_schema.triggers "
                "WHERE trigger_schema=DATABASE() AND trigger_name=%s",
                ("i21_vote_copy_pause",),
            )
            trigger = cursor.fetchone()
        diagnostics["trigger_action"] = trigger["action_statement"] if trigger else None
    finally:
        connection.close()

    if process.poll() is not None:
        stdout, stderr = process.communicate(timeout=5)
        password = os.environ.get("WONIUNOTE_TEST_DB_PASSWORD", "")
        if password:
            stdout = stdout.replace(password, "[REDACTED]")
            stderr = stderr.replace(password, "[REDACTED]")
        diagnostics["client_stdout"] = stdout[-4000:]
        diagnostics["client_stderr"] = stderr[-4000:]
    else:
        diagnostics["client_output"] = "not collected because migration client was still running"
    return diagnostics


def _exercise_partial_copy_kill(temp_dir: Path, evidence: dict[str, Any]) -> None:
    database = _prepare_case(
        "partial_kill",
        counts={10: (1, 0), 20: (0, 1), 30: (0, 1)},
        user_ids={1, 2, 3},
        # Keep these source IDs clear of canonical ID 1 so the fixture reaches
        # the second INSERT; source-ID collision/remapping is covered by the
        # dedicated four-state case above.
        legacy=[(2, 20, 2, -1), (3, 30, 3, -1)],
        canonical=[(1, 10, 1, 1)],
    )
    evidence["scratch_databases"].append(database)
    connection = _connect_scratch(database)
    try:
        _create_sleep_trigger(connection, "i21_vote_copy_pause", 30)
    finally:
        connection.close()
    report, backup, backup_sha, approval = _prepare_approval_artifacts(database, temp_dir, "partial_kill")
    if report["state"] != "both" or report["hard_blocking_findings"]:
        raise RuntimeError("partial-copy fixture did not pass migration preflight")
    approval.write_text(json.dumps(report["approval_template"], sort_keys=True), encoding="utf-8")

    _verified_connection().close()
    process = subprocess.Popen(
        _command(
            database,
            [
                "--apply", "--run-id", _migration_run_id("partial_kill"),
                "--writes-frozen-run-id", _migration_run_id("partial_kill"),
                "--backup-file", str(backup), "--backup-sha256", backup_sha,
                "--backup-restore-verified", "--preserve-comment-counts",
                "--approved-preflight-sha256", report["snapshot_sha256"],
                "--approval-file", str(approval),
            ],
        ),
        env=_migration_env(database), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    migration_connection_id: int | None = None
    server_connection_killed = False
    os_kill_returncode: int | None = None
    # While a row trigger is sleeping, MySQL exposes the active trigger
    # statement as PROCESSLIST.INFO rather than the outer INSERT. The exact
    # statement plus this isolated schema/user and User sleep state proves the
    # migration reached the second source row (commentid 30).
    sleep_query = "SET @iter21_migration_sleep = IF(NEW.commentid = 30, SLEEP(60), 0)"
    observed_second_row_sleep: dict[str, Any] | None = None
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            observer = _connect_scratch(database)
            try:
                matches = _matching_migration_processes(
                    observer, database, sleep_query, "user sleep"
                )
            finally:
                observer.close()
            if len(matches) > 1:
                raise RuntimeError("multiple run-owned migration sessions matched the delayed second vote")
            if matches:
                observed_second_row_sleep = matches[0]
                break
            if process.poll() is not None:
                break
            time.sleep(0.1)
        if observed_second_row_sleep is None or process.poll() is not None:
            diagnostics = _partial_copy_diagnostics(process, database)
            raise RuntimeError(
                "could not observe the real migration process paused on its second source vote; "
                "diagnostics=" + json.dumps(diagnostics, sort_keys=True, separators=(",", ":"))
            )
        migration_connection_id = int(observed_second_row_sleep["id"])
        _pause_kill_client(process)
        vote_connection = _kill_verified_migration_connection(
            database, migration_connection_id, sleep_query, "user sleep"
        )
        server_connection_killed = True
        os_kill_returncode = _sigkill_paused_client(process)
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)
        if server_connection_killed:
            connection = _connect_scratch(database)
            try:
                with connection.cursor() as cursor:
                    cursor.execute("DROP TRIGGER IF EXISTS i21_vote_copy_pause")
            finally:
                connection.close()
        # On an unconfirmed server cancellation, retain the trigger and scratch
        # schema for diagnosis; the runner owns and removes this container.

    connection = _connect_scratch(database)
    try:
        partial_rows = _table_rows(connection, "comment_votes")
        retained_source = _table_rows(connection, "comment_vote")
        if len(partial_rows) != 2 or not any(row["commentid"] == 20 for row in partial_rows):
            raise RuntimeError("killed process did not leave exactly the existing plus first copied vote")
        if any(row["commentid"] == 30 for row in partial_rows):
            raise RuntimeError("delayed second source vote was unexpectedly copied before the kill")
        if len(retained_source) != 2:
            raise RuntimeError("partial-copy interruption changed retained source rows")
    finally:
        connection.close()

    recovery_report = _preflight(database)
    if recovery_report["state"] != "both":
        raise RuntimeError("partial-copy state was not recognized for recovery")
    recovered = _apply(
        database, recovery_report, backup, backup_sha, approval, _migration_run_id("partial_recovery")
    )
    connection = _connect_scratch(database)
    try:
        final_rows = _table_rows(connection, "comment_votes")
        if len(final_rows) != 3 or not any(row["commentid"] == 30 for row in final_rows):
            raise RuntimeError("resumed migration did not complete the partial canonical copy")
        if len(_table_rows(connection, "comment_vote")) != 2:
            raise RuntimeError("resumed migration did not retain all source rows")
        if _comment_counts(connection) != {10: (1, 0), 20: (0, 1), 30: (0, 1)}:
            raise RuntimeError("partial-copy recovery changed historical comment counters")
    finally:
        connection.close()
    evidence["partial_copy_recovery"] = {
        "connection": vote_connection,
        "server_action": "KILL CONNECTION; processlist id confirmed absent before trigger removal",
        "os_pid": process.pid,
        "os_signals": ["SIGSTOP", "SIGKILL"],
        "os_sigkill_returncode": os_kill_returncode,
        "recovery_action": recovered["action"],
        "partial_rows_before_recovery": 2,
        "final_canonical_rows": 3,
    }


def main() -> int:
    run_id, container_id = _run_identity()
    # This call validates labels, ID, loopback mapping, and run-specific schema
    # before any scratch DDL is attempted.
    verified = _verified_connection()
    verified.close()
    evidence: dict[str, Any] = {
        "run_id": run_id,
        "mysql_container_id": container_id,
        "verified_labels": {
            "org.woniunote.iter21.run-id": run_id,
            "org.woniunote.iter21.service": "mysql",
        },
        "scratch_databases": [],
        "backup_restore": "verified_for_each_live_case",
    }
    try:
        with tempfile.TemporaryDirectory(prefix="woniunote-iter21-comment-votes-") as directory:
            temp_dir = Path(directory)
            _exercise_four_states(temp_dir, evidence)
            _exercise_opposite_conflict(temp_dir, evidence)
            _exercise_killed_ddl(temp_dir, evidence)
            _exercise_partial_copy_kill(temp_dir, evidence)
        for database in reversed(evidence["scratch_databases"]):
            _drop_database(database)
        print(json.dumps({"status": "PASS", **evidence}, sort_keys=True, separators=(",", ":")))
        return 0
    except Exception:
        # Preserve this run's scratch schemas in the disposable service for
        # diagnosis. The integration runner owns and removes the container.
        raise


if __name__ == "__main__":
    raise SystemExit(main())
