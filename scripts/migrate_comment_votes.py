#!/usr/bin/env python3
"""Fail-closed preflight and resumable migration for comment vote tables.

The default command is read-only.  Applying changes requires an approved
snapshot hash, an explicit write-freeze assertion, a checksummed and
restore-verified backup, an explicit count policy, and a JSON mapping for any
same-direction duplicates or primary-key collisions.  The old table is never
dropped or overwritten; partial copies can be resumed from a fresh preflight.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


LEGACY_TABLE = "comment_vote"
CANONICAL_TABLE = "comment_votes"
VOTE_TABLES = (LEGACY_TABLE, CANONICAL_TABLE)
REQUIRED_COLUMNS = {"id", "commentid", "userid", "vote_type", "createtime"}
INTEGER_TYPES = {"tinyint", "smallint", "mediumint", "int", "bigint"}
MIGRATION_LOCK_NAME = "woniunote.comment_votes.migration"


class MigrationBlocked(RuntimeError):
    """Raised when the inspected state is not safe for an automatic change."""


def classify_table_state(present_tables: Iterable[str]) -> str:
    present = set(present_tables)
    has_legacy = LEGACY_TABLE in present
    has_canonical = CANONICAL_TABLE in present
    if has_legacy and has_canonical:
        return "both"
    if has_legacy:
        return "legacy_only"
    if has_canonical:
        return "canonical_only"
    return "none"


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


def _normal_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": _json_value(row.get("id")),
        "commentid": _json_value(row.get("commentid")),
        "userid": _json_value(row.get("userid")),
        "vote_type": _json_value(row.get("vote_type")),
        "createtime": _json_value(row.get("createtime")),
    }


def _pair(row: Mapping[str, Any]) -> tuple[Any, Any]:
    return row.get("commentid"), row.get("userid")


def _pair_json(pair: tuple[Any, Any]) -> dict[str, Any]:
    return {"commentid": pair[0], "userid": pair[1]}


def _count_map(rows: Sequence[Mapping[str, Any]]) -> dict[tuple[Any, Any], list[dict[str, Any]]]:
    groups: dict[tuple[Any, Any], list[dict[str, Any]]] = defaultdict(list)
    for original in rows:
        row = _normal_row(original)
        groups[_pair(row)].append(row)
    for group in groups.values():
        group.sort(key=lambda row: (row["id"] is None, row["id"]))
    return groups


def analyze_snapshot(
    present_tables: Iterable[str],
    rows_by_table: Mapping[str, Sequence[Mapping[str, Any]]],
    comment_counts: Mapping[Any, tuple[Any, Any]],
    valid_comment_ids: set[Any],
    valid_user_ids: set[Any],
    schema_issues: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, Any]:
    """Analyze a database snapshot without changing it; also used by unit tests."""
    present = set(present_tables).intersection(VOTE_TABLES)
    state = classify_table_state(present)
    issues = schema_issues or {}
    blocking: set[str] = set()
    hard_blocking: set[str] = set()
    table_reports: dict[str, Any] = {}
    normalized_rows: dict[str, list[dict[str, Any]]] = {}
    groups_by_table: dict[str, dict[tuple[Any, Any], list[dict[str, Any]]]] = {}

    for table in VOTE_TABLES:
        if table not in present:
            continue
        rows = [_normal_row(row) for row in rows_by_table.get(table, [])]
        normalized_rows[table] = rows
        groups = _count_map(rows)
        groups_by_table[table] = groups
        duplicate_business_keys: list[dict[str, Any]] = []
        same_table_opposite_conflicts: list[dict[str, Any]] = []
        invalid_vote_types: list[dict[str, Any]] = []
        orphan_comments: list[dict[str, Any]] = []
        orphan_users: list[dict[str, Any]] = []
        invalid_rows: list[dict[str, Any]] = []

        agree_by_comment: dict[Any, int] = defaultdict(int)
        oppose_by_comment: dict[Any, int] = defaultdict(int)
        for pair, group in groups.items():
            types = {row["vote_type"] for row in group}
            if len(group) > 1:
                duplicate_business_keys.append(
                    {
                        **_pair_json(pair),
                        "vote_types": sorted(types, key=lambda value: str(value)),
                        "rows": [{"id": row["id"], "vote_type": row["vote_type"]} for row in group],
                    }
                )
                blocking.add("duplicate_business_key")
                if len(types) > 1:
                    same_table_opposite_conflicts.append(
                        {**_pair_json(pair), "rows": [{"id": row["id"], "vote_type": row["vote_type"]} for row in group]}
                    )
                    blocking.add("opposite_direction_conflict")
                    hard_blocking.add("opposite_direction_conflict")

        for row in rows:
            if row["vote_type"] not in (1, -1):
                invalid_vote_types.append({"id": row["id"], **_pair_json(_pair(row)), "vote_type": row["vote_type"]})
                blocking.add("invalid_vote_type")
                hard_blocking.add("invalid_vote_type")
            elif row["commentid"] is not None:
                if row["vote_type"] == 1:
                    agree_by_comment[row["commentid"]] += 1
                else:
                    oppose_by_comment[row["commentid"]] += 1

            if row["commentid"] not in valid_comment_ids:
                orphan_comments.append({"id": row["id"], **_pair_json(_pair(row))})
                blocking.add("orphan_record")
                hard_blocking.add("orphan_record")
            if row["userid"] not in valid_user_ids:
                orphan_users.append({"id": row["id"], **_pair_json(_pair(row))})
                blocking.add("orphan_record")
                hard_blocking.add("orphan_record")
            if any(row[field] is None for field in ("id", "commentid", "userid", "vote_type")):
                invalid_rows.append({"id": row["id"], **_pair_json(_pair(row))})
                blocking.add("invalid_row")
                hard_blocking.add("invalid_row")
            elif not all(isinstance(row[field], int) for field in ("id", "commentid", "userid", "vote_type")):
                invalid_rows.append({"id": row["id"], **_pair_json(_pair(row))})
                blocking.add("invalid_row")
                hard_blocking.add("invalid_row")
            elif row["id"] <= 0 or row["commentid"] <= 0 or row["userid"] <= 0:
                invalid_rows.append({"id": row["id"], **_pair_json(_pair(row))})
                blocking.add("invalid_row")
                hard_blocking.add("invalid_row")

        count_differences: list[dict[str, Any]] = []
        for comment_id, (stored_agree, stored_oppose) in comment_counts.items():
            vote_agree = agree_by_comment.get(comment_id, 0)
            vote_oppose = oppose_by_comment.get(comment_id, 0)
            if stored_agree is None or stored_oppose is None or stored_agree < 0 or stored_oppose < 0:
                blocking.add("invalid_comment_count")
                hard_blocking.add("invalid_comment_count")
            agree_delta = None if stored_agree is None else stored_agree - vote_agree
            oppose_delta = None if stored_oppose is None else stored_oppose - vote_oppose
            if agree_delta != 0 or oppose_delta != 0:
                count_differences.append(
                    {
                        "commentid": comment_id,
                        "stored_agreecount": stored_agree,
                        "stored_opposecount": stored_oppose,
                        "vote_agree_count": vote_agree,
                        "vote_oppose_count": vote_oppose,
                        "agree_delta": agree_delta,
                        "oppose_delta": oppose_delta,
                    }
                )
                blocking.add("count_difference")

        if issues.get(table):
            blocking.add("schema_issue")
            if table == CANONICAL_TABLE:
                hard_blocking.add("schema_issue")

        table_reports[table] = {
            "row_count": len(rows),
            "schema_issues": sorted(issues.get(table, [])),
            "duplicate_business_keys": duplicate_business_keys,
            "opposite_direction_conflicts": same_table_opposite_conflicts,
            "invalid_vote_types": invalid_vote_types,
            "invalid_rows": invalid_rows,
            "orphan_comments": orphan_comments,
            "orphan_users": orphan_users,
            "count_differences": count_differences,
        }

    cross_duplicates: list[dict[str, Any]] = []
    opposite_conflicts: list[dict[str, Any]] = []
    primary_key_collisions: list[dict[str, Any]] = []
    if state == "both":
        legacy = groups_by_table[LEGACY_TABLE]
        canonical = groups_by_table[CANONICAL_TABLE]
        for pair in sorted(set(legacy).intersection(canonical), key=lambda value: (str(value[0]), str(value[1]))):
            legacy_types = {row["vote_type"] for row in legacy[pair]}
            canonical_types = {row["vote_type"] for row in canonical[pair]}
            item = {
                **_pair_json(pair),
                "legacy_vote_types": sorted(legacy_types, key=lambda value: str(value)),
                "canonical_vote_types": sorted(canonical_types, key=lambda value: str(value)),
                "legacy_ids": [row["id"] for row in legacy[pair]],
                "canonical_ids": [row["id"] for row in canonical[pair]],
            }
            if legacy_types == canonical_types and len(legacy_types) == 1:
                cross_duplicates.append(item)
            else:
                opposite_conflicts.append(item)
                blocking.add("opposite_direction_conflict")
                hard_blocking.add("opposite_direction_conflict")

        canonical_by_id = {
            row["id"]: row for row in normalized_rows[CANONICAL_TABLE] if row["id"] is not None
        }
        for row in normalized_rows[LEGACY_TABLE]:
            current = canonical_by_id.get(row["id"])
            if current is not None and _pair(current) != _pair(row):
                primary_key_collisions.append(
                    {
                        "source_table": LEGACY_TABLE,
                        "source_id": row["id"],
                        "source_commentid": row["commentid"],
                        "source_userid": row["userid"],
                        "canonical_commentid": current["commentid"],
                        "canonical_userid": current["userid"],
                    }
                )

    if cross_duplicates:
        blocking.add("duplicate_business_key")
    if primary_key_collisions:
        blocking.add("primary_key_collision")

    logical_count_differences: list[dict[str, Any]] = []
    logical_count_state = "available"
    if state == "both":
        canonical_rows = normalized_rows.get(CANONICAL_TABLE, [])
        canonical_pairs = {_pair(row) for row in canonical_rows}
        logical_rows = list(canonical_rows)
        for pair, group in groups_by_table.get(LEGACY_TABLE, {}).items():
            if pair in canonical_pairs:
                continue
            types = {row["vote_type"] for row in group}
            if len(types) != 1:
                logical_count_state = "blocked_by_vote_direction_conflict"
                continue
            # The planned duplicate mapping keeps the minimum source ID for an
            # otherwise valid same-direction group, so count that business vote once.
            logical_rows.append(group[0])
    elif state == "legacy_only":
        logical_rows = normalized_rows.get(LEGACY_TABLE, [])
    elif state == "canonical_only":
        logical_rows = normalized_rows.get(CANONICAL_TABLE, [])
    else:
        logical_rows = []

    if logical_count_state == "available":
        logical_agree: dict[Any, int] = defaultdict(int)
        logical_oppose: dict[Any, int] = defaultdict(int)
        for row in logical_rows:
            if row["vote_type"] == 1:
                logical_agree[row["commentid"]] += 1
            elif row["vote_type"] == -1:
                logical_oppose[row["commentid"]] += 1
            else:
                logical_count_state = "blocked_by_invalid_vote_type"
        if logical_count_state == "available":
            for comment_id, (stored_agree, stored_oppose) in comment_counts.items():
                agree_count = logical_agree.get(comment_id, 0)
                oppose_count = logical_oppose.get(comment_id, 0)
                if stored_agree != agree_count or stored_oppose != oppose_count:
                    logical_count_differences.append(
                        {
                            "commentid": comment_id,
                            "stored_agreecount": stored_agree,
                            "stored_opposecount": stored_oppose,
                            "logical_vote_agree_count": agree_count,
                            "logical_vote_oppose_count": oppose_count,
                            "agree_delta": None if stored_agree is None else stored_agree - agree_count,
                            "oppose_delta": None if stored_oppose is None else stored_oppose - oppose_count,
                        }
                    )

    # The mapping template is advisory and deterministic. Operators must bind
    # an edited copy to the exact fingerprint before applying it.
    deduplicate_template: list[dict[str, Any]] = []
    if state == "legacy_only":
        for pair, group in sorted(groups_by_table[LEGACY_TABLE].items(), key=lambda item: (str(item[0][0]), str(item[0][1]))):
            if len(group) > 1 and len({row["vote_type"] for row in group}) == 1:
                deduplicate_template.append(
                    {
                        **_pair_json(pair),
                        "keep_table": LEGACY_TABLE,
                        "keep_id": group[0]["id"],
                    }
                )
    elif state == "both":
        for pair, group in sorted(groups_by_table[LEGACY_TABLE].items(), key=lambda item: (str(item[0][0]), str(item[0][1]))):
            if len(group) > 1 and len({row["vote_type"] for row in group}) != 1:
                continue
            current_group = groups_by_table[CANONICAL_TABLE].get(pair, [])
            if current_group and len({row["vote_type"] for row in group + current_group}) == 1:
                deduplicate_template.append(
                    {
                        **_pair_json(pair),
                        "keep_table": CANONICAL_TABLE,
                        "keep_id": current_group[0]["id"],
                    }
                )
            elif len(group) > 1 and len({row["vote_type"] for row in group}) == 1:
                deduplicate_template.append(
                    {
                        **_pair_json(pair),
                        "keep_table": LEGACY_TABLE,
                        "keep_id": group[0]["id"],
                    }
                )

    approval_template = {
        "preflight_sha256": None,
        "deduplicate": deduplicate_template,
        "remap_ids": [],
        "count_policy": "preserve_existing",
        "source_schema_policy": "validated_source_rows",
    }
    return {
        "state": state,
        "tables": table_reports,
        "cross_table": {
            "same_direction_duplicates": cross_duplicates,
            "opposite_direction_conflicts": opposite_conflicts,
            "primary_key_collisions": primary_key_collisions,
            "logical_count_state": logical_count_state,
            "logical_count_differences": logical_count_differences,
        },
        "blocking_findings": sorted(blocking),
        "hard_blocking_findings": sorted(hard_blocking),
        "approval_template": approval_template,
        "write_actions": [],
        "migration_policy": {
            "read_only_by_default": True,
            "source_table_retained": True,
            "comment_counts": "preserve existing; report deltas; never recompute",
            "write_freeze_required": True,
            "backup_checksum_and_restore_attestation_required_for_apply": True,
            "partial_copy_recovery": "re-run preflight and apply an approved current snapshot",
        },
    }


def _digest_rows(rows: Sequence[Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        encoded = json.dumps(_normal_row(row), sort_keys=True, separators=(",", ":"))
        digest.update(encoded.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=_json_value)


def _table_layout(cursor: Any, database: str, table: str) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], str | None]:
    cursor.execute(
        "SELECT column_name AS column_name, data_type AS data_type, "
        "column_type AS column_type, is_nullable AS is_nullable, extra AS extra "
        "FROM information_schema.columns WHERE table_schema=%s AND table_name=%s",
        (database, table),
    )
    columns = {row["column_name"]: row for row in cursor.fetchall()}
    cursor.execute(
        "SELECT index_name AS index_name, non_unique AS non_unique, "
        "seq_in_index AS seq_in_index, column_name AS column_name "
        "FROM information_schema.statistics WHERE table_schema=%s AND table_name=%s "
        "ORDER BY index_name, seq_in_index",
        (database, table),
    )
    indexes = cursor.fetchall()
    cursor.execute(
        "SELECT constraint_name AS constraint_name, column_name AS column_name, "
        "referenced_table_name AS referenced_table_name, "
        "referenced_column_name AS referenced_column_name "
        "FROM information_schema.key_column_usage "
        "WHERE table_schema=%s AND table_name=%s AND referenced_table_name IS NOT NULL",
        (database, table),
    )
    foreign_keys = cursor.fetchall()
    cursor.execute(
        "SELECT engine AS engine FROM information_schema.tables "
        "WHERE table_schema=%s AND table_name=%s",
        (database, table),
    )
    table_row = cursor.fetchone()
    return columns, indexes, foreign_keys, table_row["engine"] if table_row else None


def _schema_issues(
    table: str,
    columns: Mapping[str, Mapping[str, Any]],
    indexes: Sequence[Mapping[str, Any]],
    foreign_keys: Sequence[Mapping[str, Any]],
    engine: str | None,
    canonical: bool,
) -> list[str]:
    issues: list[str] = []
    missing_columns = sorted(REQUIRED_COLUMNS.difference(columns))
    if missing_columns:
        issues.append("missing_columns:" + ",".join(missing_columns))
        return issues
    for name in ("id", "commentid", "userid", "vote_type"):
        if columns[name]["data_type"].lower() not in INTEGER_TYPES:
            issues.append("non_integer_column:" + name)
    if "unsigned" in columns["vote_type"]["column_type"].lower():
        issues.append("unsigned_vote_type")
    if "auto_increment" not in columns["id"]["extra"].lower():
        issues.append("id_not_auto_increment")
    if engine is None or engine.lower() != "innodb":
        issues.append("engine_not_innodb")

    index_columns: dict[str, list[str]] = defaultdict(list)
    non_unique: dict[str, int] = {}
    for index in indexes:
        index_columns[index["index_name"]].append(index["column_name"])
        non_unique[index["index_name"]] = int(index["non_unique"])
    if index_columns.get("PRIMARY") != ["id"]:
        issues.append("primary_key_not_id")
    has_pair_unique = any(
        non_unique.get(name) == 0 and tuple(names) == ("commentid", "userid")
        for name, names in index_columns.items()
    )
    if not has_pair_unique:
        issues.append("missing_unique_comment_user")

    foreign_key_pairs = {
        (row["column_name"], row["referenced_table_name"], row["referenced_column_name"])
        for row in foreign_keys
    }
    if ("commentid", "comment", "commentid") not in foreign_key_pairs:
        issues.append("missing_comment_foreign_key")
    if ("userid", "users", "userid") not in foreign_key_pairs:
        issues.append("missing_user_foreign_key")
    # A source table can lack constraints and still be copied after full orphan
    # checks. The canonical table must have the complete standard constraints.
    if not canonical:
        issues = [issue for issue in issues if issue not in {
            "missing_unique_comment_user", "missing_comment_foreign_key", "missing_user_foreign_key",
        }]
    return issues


def _read_snapshot(cursor: Any, database: str) -> tuple[dict[str, Any], set[str]]:
    cursor.execute(
        "SELECT table_name AS table_name FROM information_schema.tables "
        "WHERE table_schema=%s AND table_name IN (%s, %s)",
        (database, LEGACY_TABLE, CANONICAL_TABLE),
    )
    present = {row["table_name"] for row in cursor.fetchall()}
    state = classify_table_state(present)
    rows_by_table: dict[str, list[dict[str, Any]]] = {}
    layouts: dict[str, Any] = {}
    schema_issues: dict[str, list[str]] = {}
    table_fingerprints: dict[str, str] = {}

    for table in VOTE_TABLES:
        if table not in present:
            continue
        columns, indexes, foreign_keys, engine = _table_layout(cursor, database, table)
        issues = _schema_issues(table, columns, indexes, foreign_keys, engine, table == CANONICAL_TABLE)
        schema_issues[table] = issues
        layouts[table] = {
            "columns": {
                name: {key: row[key] for key in ("data_type", "column_type", "is_nullable", "extra")}
                for name, row in sorted(columns.items())
            },
            "indexes": [
                {key: row[key] for key in ("index_name", "non_unique", "seq_in_index", "column_name")}
                for row in indexes
            ],
            "foreign_keys": [
                {key: row[key] for key in ("column_name", "referenced_table_name", "referenced_column_name")}
                for row in foreign_keys
            ],
            "engine": engine,
        }
        if REQUIRED_COLUMNS.issubset(columns):
            cursor.execute(
                f"SELECT id, commentid, userid, vote_type, createtime FROM `{table}` ORDER BY id"
            )
            rows = list(cursor.fetchall())
        else:
            rows = []
        rows_by_table[table] = rows
        table_fingerprints[table] = _digest_rows(rows)

    base_tables = _base_tables(cursor, database)
    base_layouts: dict[str, Any] = {}
    base_issues: list[str] = []
    for base_table, needed in (("comment", {"commentid", "agreecount", "opposecount"}), ("users", {"userid"})):
        if base_table not in base_tables:
            base_issues.append("missing_base_table:" + base_table)
            continue
        columns, _, _, engine = _table_layout(cursor, database, base_table)
        missing = sorted(needed.difference(columns))
        base_layouts[base_table] = {
            "columns": {
                name: {key: row[key] for key in ("data_type", "column_type", "is_nullable", "extra")}
                for name, row in sorted(columns.items())
            },
            "engine": engine,
        }
        if missing:
            base_issues.append("missing_base_columns:" + base_table + ":" + ",".join(missing))

    if "comment" in base_tables and not any(issue.startswith("missing_base_columns:comment:") for issue in base_issues):
        cursor.execute("SELECT commentid, agreecount, opposecount FROM `comment` ORDER BY commentid")
        comment_counts = {
            row["commentid"]: (row["agreecount"], row["opposecount"])
            for row in cursor.fetchall()
        }
        cursor.execute("SELECT commentid FROM `comment` ORDER BY commentid")
        comment_ids = {row["commentid"] for row in cursor.fetchall()}
    else:
        comment_counts = {}
        comment_ids = set()
    comment_fingerprint = hashlib.sha256(_canonical_json(comment_counts).encode("utf-8")).hexdigest()
    if "users" in base_tables and not any(issue.startswith("missing_base_columns:users:") for issue in base_issues):
        cursor.execute("SELECT userid FROM `users` ORDER BY userid")
        user_ids = {row["userid"] for row in cursor.fetchall()}
    else:
        user_ids = set()
    if "comment" in base_layouts and "comment" in base_tables:
        comment_type = base_layouts["comment"]["columns"].get("commentid", {}).get("column_type", "")
        if comment_type.lower() != "int":
            base_issues.append("commentid_type_must_match_standard_int")
    if "users" in base_layouts and "users" in base_tables:
        user_type = base_layouts["users"]["columns"].get("userid", {}).get("column_type", "")
        if user_type.lower() != "int":
            base_issues.append("userid_type_must_match_standard_int")
    if base_issues:
        base_issue_digest = hashlib.sha256(_canonical_json(base_issues).encode("utf-8")).hexdigest()
    else:
        base_issue_digest = hashlib.sha256(b"[]").hexdigest()

    cursor.execute("SELECT DATABASE() AS database_name, @@version AS server_version")
    server = cursor.fetchone()
    report = analyze_snapshot(present, rows_by_table, comment_counts, comment_ids, user_ids, schema_issues)
    report["database"] = server["database_name"]
    report["server_version"] = server["server_version"]
    report["table_layouts"] = layouts
    report["base_table_layouts"] = base_layouts
    report["base_schema_issues"] = base_issues
    report["table_sha256"] = table_fingerprints
    report["comment_counts_sha256"] = comment_fingerprint
    report["user_ids_sha256"] = hashlib.sha256(_canonical_json(sorted(user_ids)).encode("utf-8")).hexdigest()
    report["base_schema_issues_sha256"] = base_issue_digest
    report["source_table_sha256"] = table_fingerprints.get(LEGACY_TABLE)

    hard = set(report["hard_blocking_findings"])
    for table in present:
        if schema_issues.get(table):
            missing_columns = any(issue.startswith("missing_columns:") for issue in schema_issues[table])
            other_hard_source = any(issue in {"primary_key_not_id", "non_integer_column:id", "non_integer_column:commentid", "non_integer_column:userid", "non_integer_column:vote_type", "unsigned_vote_type", "id_not_auto_increment", "engine_not_innodb"} for issue in schema_issues[table])
            if missing_columns or other_hard_source:
                hard.add("schema_issue")
    if base_issues:
        hard.add("referenced_table_missing")
        report["blocking_findings"] = sorted(set(report["blocking_findings"]) | {"referenced_table_missing"})
    cursor.execute(
        "SELECT table_name AS table_name, column_name AS column_name, "
        "constraint_name AS constraint_name "
        "FROM information_schema.key_column_usage "
        "WHERE constraint_schema=%s AND referenced_table_name=%s ORDER BY table_name, column_name",
        (database, LEGACY_TABLE),
    )
    incoming_foreign_keys = cursor.fetchall()
    report["legacy_incoming_foreign_keys"] = incoming_foreign_keys
    if incoming_foreign_keys and report["cross_table"]["primary_key_collisions"]:
        hard.add("primary_key_collision_has_references")
        report["blocking_findings"] = sorted(set(report["blocking_findings"]) | {"primary_key_collision_has_references"})
    report["hard_blocking_findings"] = sorted(hard)
    report["snapshot_sha256"] = hashlib.sha256(
        _canonical_json(
            {
                "state": state,
                "layouts": layouts,
                "table_sha256": table_fingerprints,
                "comment_counts_sha256": comment_fingerprint,
                "user_ids_sha256": report["user_ids_sha256"],
                "base_schema_issues_sha256": base_issue_digest,
                "base_table_layouts": base_layouts,
                "base_schema_issues": base_issues,
                "legacy_incoming_foreign_keys": incoming_foreign_keys,
                "schema_issues": schema_issues,
                "blocking_findings": report["blocking_findings"],
            }
        ).encode("utf-8")
    ).hexdigest()
    report["approval_template"]["preflight_sha256"] = report["snapshot_sha256"]
    report["approval_template"]["remap_ids"] = _template_remaps(report, rows_by_table)
    report["source_rows"] = rows_by_table.get(LEGACY_TABLE, [])
    report["canonical_rows"] = rows_by_table.get(CANONICAL_TABLE, [])
    report["comment_counts"] = comment_counts
    report["valid_comment_ids"] = comment_ids
    report["valid_user_ids"] = user_ids
    return report, present


def _base_tables(cursor: Any, database: str) -> set[str]:
    cursor.execute(
        "SELECT table_name AS table_name FROM information_schema.tables WHERE table_schema=%s "
        "AND table_name IN ('comment', 'users')",
        (database,),
    )
    return {row["table_name"] for row in cursor.fetchall()}


def _template_remaps(report: Mapping[str, Any], rows_by_table: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[dict[str, Any]]:
    if report["state"] != "both":
        return []
    canonical_by_id = {row["id"]: row for row in rows_by_table.get(CANONICAL_TABLE, [])}
    canonical_pairs = {_pair(row) for row in rows_by_table.get(CANONICAL_TABLE, [])}
    duplicate_choices = {
        (entry["commentid"], entry["userid"]): (entry["keep_table"], entry["keep_id"])
        for entry in report["approval_template"]["deduplicate"]
    }
    legacy_groups = _count_map(rows_by_table.get(LEGACY_TABLE, []))
    remaps: list[dict[str, Any]] = []
    for pair, group in legacy_groups.items():
        if pair in canonical_pairs:
            continue
        selected_id = duplicate_choices.get(pair, (LEGACY_TABLE, group[0]["id"]))[1]
        source_row = next(row for row in group if row["id"] == selected_id)
        current = canonical_by_id.get(source_row["id"])
        if current is not None and _pair(current) != pair:
            remaps.append(
                {
                    "source_table": LEGACY_TABLE,
                    "source_id": source_row["id"],
                    "commentid": source_row["commentid"],
                    "userid": source_row["userid"],
                    "action": "allocate_new_id",
                }
            )
    return sorted(remaps, key=lambda row: (row["source_id"], row["commentid"], row["userid"]))


def _lock_tables(cursor: Any, present: set[str], base_tables: set[str]) -> None:
    locks = [f"`{table}` WRITE" for table in VOTE_TABLES if table in present]
    locks.extend(f"`{table}` READ" for table in ("comment", "users") if table in base_tables)
    if locks:
        cursor.execute("LOCK TABLES " + ", ".join(locks))


def _create_canonical_table(cursor: Any, database: str) -> None:
    cursor.execute(
        "SELECT constraint_name AS constraint_name FROM information_schema.referential_constraints "
        "WHERE constraint_schema=%s",
        (database,),
    )
    used_names = {row["constraint_name"] for row in cursor.fetchall()}

    def unique_name(base: str) -> str:
        name = base
        suffix = 1
        while name in used_names:
            name = f"{base}_{suffix}"
            suffix += 1
        used_names.add(name)
        return name

    comment_fk = unique_name("fk_vote_comment")
    user_fk = unique_name("fk_vote_user")
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS `comment_votes` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `commentid` INT NOT NULL COMMENT '评论ID',
            `userid` INT NOT NULL COMMENT '用户ID',
            `vote_type` TINYINT NOT NULL COMMENT '投票类型: 1-赞, -1-踩',
            `createtime` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            PRIMARY KEY (`id`),
            UNIQUE KEY `uk_comment_user` (`commentid`, `userid`),
            KEY `idx_userid` (`userid`),
            CONSTRAINT `{comment_fk}` FOREIGN KEY (`commentid`) REFERENCES `comment` (`commentid`) ON DELETE CASCADE,
            CONSTRAINT `{user_fk}` FOREIGN KEY (`userid`) REFERENCES `users` (`userid`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评论投票表'"""
    )


def _approval_map_for_report(path: Path, report: Mapping[str, Any], rows_by_table: Mapping[str, Sequence[Mapping[str, Any]]]) -> tuple[set[tuple[int, int]], dict[tuple[int, int], int], set[int]]:
    try:
        approval = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationBlocked("无法读取审批映射 JSON") from exc
    if not isinstance(approval, dict):
        raise MigrationBlocked("审批映射必须是 JSON 对象")
    if approval.get("preflight_sha256") != report["snapshot_sha256"]:
        raise MigrationBlocked("审批映射与当前锁定快照哈希不匹配")
    if approval.get("count_policy") != "preserve_existing":
        raise MigrationBlocked("计数策略必须明确为 preserve_existing")
    if approval.get("source_schema_policy") != "validated_source_rows":
        raise MigrationBlocked("源表约束策略必须明确为 validated_source_rows")

    canonical_by_pair = {
        _pair(row): row for row in rows_by_table.get(CANONICAL_TABLE, [])
    }
    legacy_groups = _count_map(rows_by_table.get(LEGACY_TABLE, []))
    dedup_expected: dict[tuple[int, int], tuple[str, set[int], int | None]] = {}
    for pair, group in legacy_groups.items():
        current = canonical_by_pair.get(pair)
        types = {row["vote_type"] for row in group}
        if current is not None:
            if current["vote_type"] not in types or len(types) != 1:
                raise MigrationBlocked("赞/踩方向冲突，禁止自动选择")
            dedup_expected[pair] = (CANONICAL_TABLE, set(), current["id"])
        elif len(group) > 1:
            if len(types) != 1:
                raise MigrationBlocked("同一业务键存在反向重复票，禁止自动选择")
            dedup_expected[pair] = (LEGACY_TABLE, {row["id"] for row in group}, None)

    provided_dedup: dict[tuple[int, int], dict[str, Any]] = {}
    for entry in approval.get("deduplicate", []):
        if not isinstance(entry, dict):
            raise MigrationBlocked("deduplicate 映射条目格式错误")
        pair = (entry.get("commentid"), entry.get("userid"))
        if pair in provided_dedup:
            raise MigrationBlocked("deduplicate 映射含重复业务键")
        provided_dedup[pair] = entry
    if set(provided_dedup) != set(dedup_expected):
        raise MigrationBlocked("deduplicate 映射必须恰好覆盖当前所有重复/重叠业务键")

    kept_ids: dict[tuple[int, int], int] = {}
    for pair, (keep_table, allowed_ids, fixed_id) in dedup_expected.items():
        entry = provided_dedup[pair]
        if entry.get("keep_table") != keep_table:
            raise MigrationBlocked("deduplicate keep_table 与数据状态不匹配")
        keep_id = entry.get("keep_id")
        if fixed_id is not None:
            if keep_id != fixed_id:
                raise MigrationBlocked("目标表已有同方向记录，必须保留该 canonical 行")
        elif keep_id != min(allowed_ids):
            raise MigrationBlocked("keep_id 必须指向该业务键下 ID 最小的源记录")
        if keep_table == LEGACY_TABLE:
            kept_ids[pair] = keep_id

    expected_remaps = {
        (entry["source_id"], entry["commentid"], entry["userid"])
        for entry in _template_remaps(report, rows_by_table)
    }
    provided_remaps: set[tuple[int, int, int]] = set()
    for entry in approval.get("remap_ids", []):
        if not isinstance(entry, dict) or entry.get("action") != "allocate_new_id" or entry.get("source_table") != LEGACY_TABLE:
            raise MigrationBlocked("remap_ids 映射条目格式错误")
        key = (entry.get("source_id"), entry.get("commentid"), entry.get("userid"))
        if key in provided_remaps:
            raise MigrationBlocked("remap_ids 映射含重复来源 ID")
        provided_remaps.add(key)
    if provided_remaps != expected_remaps:
        raise MigrationBlocked("remap_ids 映射必须恰好覆盖当前被选中的主键碰撞")
    remap_ids = {source_id for source_id, _, _ in provided_remaps}
    return set(dedup_expected), kept_ids, remap_ids


def _selected_source_rows(
    rows: Sequence[Mapping[str, Any]],
    canonical_rows: Sequence[Mapping[str, Any]],
    duplicate_pairs: set[tuple[int, int]],
    kept_ids: Mapping[tuple[int, int], int],
) -> list[dict[str, Any]]:
    canonical_pairs = {_pair(row) for row in canonical_rows}
    selected: list[dict[str, Any]] = []
    groups = _count_map(rows)
    for pair, group in groups.items():
        if pair in canonical_pairs:
            continue
        if pair in duplicate_pairs:
            chosen_id = kept_ids[pair]
            selected.append(next(row for row in group if row["id"] == chosen_id))
        else:
            selected.extend(group)
    return selected


def _apply_rows(cursor: Any, source_rows: Sequence[Mapping[str, Any]], canonical_rows: Sequence[Mapping[str, Any]], duplicate_pairs: set[tuple[int, int]], kept_ids: Mapping[tuple[int, int], int], remap_ids: set[int]) -> list[dict[str, Any]]:
    existing_ids = {row["id"]: row for row in canonical_rows}
    mapping: list[dict[str, Any]] = []
    for row in _selected_source_rows(source_rows, canonical_rows, duplicate_pairs, kept_ids):
        collided = existing_ids.get(row["id"])
        if collided is not None and _pair(collided) != _pair(row):
            if row["id"] not in remap_ids:
                raise MigrationBlocked("来源主键碰撞缺少批准的自动重分配映射")
            cursor.execute(
                "INSERT INTO `comment_votes` (commentid, userid, vote_type, createtime) VALUES (%s, %s, %s, %s)",
                (row["commentid"], row["userid"], row["vote_type"], row["createtime"]),
            )
            mapping.append(
                {
                    "source_table": LEGACY_TABLE,
                    "source_id": row["id"],
                    "target_id": cursor.lastrowid,
                    "commentid": row["commentid"],
                    "userid": row["userid"],
                    "action": "reassigned",
                }
            )
        else:
            cursor.execute(
                "INSERT INTO `comment_votes` (id, commentid, userid, vote_type, createtime) VALUES (%s, %s, %s, %s, %s)",
                (row["id"], row["commentid"], row["userid"], row["vote_type"], row["createtime"]),
            )
            mapping.append(
                {
                    "source_table": LEGACY_TABLE,
                    "source_id": row["id"],
                    "target_id": row["id"],
                    "commentid": row["commentid"],
                    "userid": row["userid"],
                    "action": "preserved",
                }
            )
    return mapping


def _verify_merge_result(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    mappings: Sequence[Mapping[str, Any]],
) -> None:
    """Verify a locked post-copy snapshot without repairing counters or source data."""
    for digest_name in ("source_table_sha256", "comment_counts_sha256", "user_ids_sha256"):
        if before.get(digest_name) != after.get(digest_name):
            raise MigrationBlocked(f"迁移后 {digest_name} 变化；保留现场并重新预检")
    if after.get("hard_blocking_findings"):
        raise MigrationBlocked("迁移后硬阻断项未清除: " + ", ".join(after["hard_blocking_findings"]))

    old_canonical = [_normal_row(row) for row in before.get("canonical_rows", [])]
    source_rows = [_normal_row(row) for row in before.get("source_rows", [])]
    new_canonical = [_normal_row(row) for row in after.get("canonical_rows", [])]
    old_by_id = {row["id"]: row for row in old_canonical}
    new_by_id = {row["id"]: row for row in new_canonical}
    if len(old_by_id) != len(old_canonical) or len(new_by_id) != len(new_canonical):
        raise MigrationBlocked("迁移后 canonical 主键重复")

    mapped_ids: set[int] = set()
    for entry in mappings:
        target_id = entry.get("target_id")
        if not isinstance(target_id, int) or target_id in mapped_ids:
            raise MigrationBlocked("迁移返回的目标 ID 映射无效")
        mapped_ids.add(target_id)
        target = new_by_id.get(target_id)
        if target is None:
            raise MigrationBlocked("迁移后的 canonical 缺少已复制记录")
        if (target["commentid"], target["userid"]) != (entry.get("commentid"), entry.get("userid")):
            raise MigrationBlocked("迁移后的目标业务键与映射不一致")
        source = next(
            (row for row in source_rows if row["id"] == entry.get("source_id") and
             (row["commentid"], row["userid"]) == (entry.get("commentid"), entry.get("userid"))),
            None,
        )
        if source is None or any(
            target[field] != source[field]
            for field in ("commentid", "userid", "vote_type", "createtime")
        ):
            raise MigrationBlocked("迁移后的记录内容与来源不一致")

    expected_ids = set(old_by_id) | mapped_ids
    if set(new_by_id) != expected_ids:
        raise MigrationBlocked("迁移后的 canonical 含缺失或未批准的额外记录")
    for row_id, old_row in old_by_id.items():
        if new_by_id.get(row_id) != old_row:
            raise MigrationBlocked("迁移修改了迁移前已存在的 canonical 记录")

    old_groups = _count_map(old_canonical)
    source_groups = _count_map(source_rows)
    new_groups = _count_map(new_canonical)
    if set(new_groups) != set(old_groups) | set(source_groups):
        raise MigrationBlocked("迁移后的 canonical 业务键集合与来源不一致")
    for pair, source_group in source_groups.items():
        source_types = {row["vote_type"] for row in source_group}
        target_group = new_groups[pair]
        if len(source_types) != 1 or len(target_group) != 1:
            raise MigrationBlocked("迁移后的业务键重复或赞踩方向不一致")
        if target_group[0]["vote_type"] != next(iter(source_types)):
            raise MigrationBlocked("迁移后的业务键投票方向与来源不一致")
        if pair in old_groups and old_groups[pair][0] != target_group[0]:
            raise MigrationBlocked("同业务键的既有 canonical 记录被更改")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_apply_arguments(args: argparse.Namespace) -> None:
    if not args.run_id or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", args.run_id):
        raise MigrationBlocked("--run-id 必须是 1–64 位字母、数字、点、下划线或连字符")
    if args.writes_frozen_run_id != args.run_id:
        raise MigrationBlocked("--writes-frozen-run-id 必须与 --run-id 完全一致")
    if not args.backup_file or not args.backup_sha256:
        raise MigrationBlocked("apply 必须提供备份文件和 SHA-256")
    backup_path = Path(args.backup_file)
    if not backup_path.is_file() or backup_path.stat().st_size == 0:
        raise MigrationBlocked("备份文件不存在或为空")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", args.backup_sha256):
        raise MigrationBlocked("--backup-sha256 必须是 64 位十六进制摘要")
    actual = _sha256_file(backup_path)
    if actual.lower() != args.backup_sha256.lower():
        raise MigrationBlocked("备份文件 SHA-256 不匹配")
    if not args.backup_restore_verified:
        raise MigrationBlocked("apply 必须明确确认备份已通过恢复验证")
    if not args.preserve_comment_counts:
        raise MigrationBlocked("apply 必须明确确认保留原评论计数，不重算")
    if not args.approved_preflight_sha256 or not re.fullmatch(r"[0-9a-fA-F]{64}", args.approved_preflight_sha256):
        raise MigrationBlocked("apply 必须提供批准的预检 snapshot SHA-256")
    if not args.approval_file:
        raise MigrationBlocked("apply 必须提供绑定预检哈希的审批映射 JSON")


def _safe_report(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"source_rows", "canonical_rows", "comment_counts", "valid_comment_ids", "valid_user_ids"}
    }


def _new_connection(args: argparse.Namespace, read_only: bool) -> Any:
    try:
        import pymysql
    except ImportError as exc:  # pragma: no cover - depends on runtime setup
        raise MigrationBlocked("缺少 PyMySQL；请在 Anaconda base 环境安装项目 requirements.txt") from exc
    user = args.user or os.environ.get("DB_USER")
    if not user:
        raise MigrationBlocked("需要 --user 或 DB_USER 环境变量；不会从命令参数接受密码")
    database = args.database or os.environ.get("DB_NAME", "woniunote")
    connection = pymysql.connect(
        host=args.host or os.environ.get("DB_HOST", "localhost"),
        port=args.port or int(os.environ.get("DB_PORT", "3306")),
        user=user,
        password=os.environ.get("DB_PASS", ""),
        database=database,
        charset="utf8mb4",
        autocommit=True,
        connect_timeout=10,
        read_timeout=60,
        write_timeout=60,
        cursorclass=pymysql.cursors.DictCursor,
    )
    if read_only:
        with connection.cursor() as cursor:
            cursor.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY")
    return connection


def _run_preflight(args: argparse.Namespace) -> dict[str, Any]:
    connection = _new_connection(args, read_only=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE() AS selected_database")
            selected_database = cursor.fetchone()["selected_database"]
            report, _ = _read_snapshot(cursor, selected_database)
        return report
    finally:
        connection.rollback()
        connection.close()


def _run_apply(args: argparse.Namespace) -> dict[str, Any]:
    _validate_apply_arguments(args)
    connection = _new_connection(args, read_only=False)
    mapping_path = Path(args.approval_file)
    run_record: dict[str, Any] = {"run_id": args.run_id, "applied": False, "id_mappings": []}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT GET_LOCK(%s, 10) AS acquired", (MIGRATION_LOCK_NAME,))
            if cursor.fetchone()["acquired"] != 1:
                raise MigrationBlocked("无法在 10 秒内取得迁移互斥锁")

            cursor.execute("SELECT DATABASE() AS selected_database")
            database = cursor.fetchone()["selected_database"]
            present = _vote_tables(cursor, database)
            base_tables = _base_tables(cursor, database)
            _lock_tables(cursor, present, base_tables)

            report, locked_present = _read_snapshot(cursor, database)
            if present != locked_present:
                raise MigrationBlocked("获取写锁后表状态变化；重新运行只读预检")
            if report["snapshot_sha256"].lower() != args.approved_preflight_sha256.lower():
                raise MigrationBlocked("当前锁定快照与批准的预检哈希不同；没有数据被修改")
            if report["hard_blocking_findings"]:
                raise MigrationBlocked("硬阻断项未清除: " + ", ".join(report["hard_blocking_findings"]))

            rows_by_table = {
                LEGACY_TABLE: report.get("source_rows", []),
                CANONICAL_TABLE: report.get("canonical_rows", []),
            }
            pre_migration_report = report
            duplicate_pairs, kept_ids, remap_ids = _approval_map_for_report(mapping_path, report, rows_by_table)
            _validate_reference_ids(report)
            if report["state"] == "canonical_only":
                run_record.update({"applied": True, "action": "already_canonical", "snapshot_sha256": report["snapshot_sha256"]})
            elif report["state"] == "none":
                cursor.execute("UNLOCK TABLES")
                _create_canonical_table(cursor, database)
                present = _vote_tables(cursor, database)
                base_tables = _base_tables(cursor, database)
                _lock_tables(cursor, present, base_tables)
                after_create, present = _read_snapshot(cursor, database)
                if present != {CANONICAL_TABLE} or after_create["canonical_rows"]:
                    raise MigrationBlocked("创建空 canonical 后状态变化；重新预检")
                if (after_create["comment_counts_sha256"] != report["comment_counts_sha256"] or
                        after_create["user_ids_sha256"] != report["user_ids_sha256"]):
                    raise MigrationBlocked("创建 canonical 表期间引用数据变化；重新预检")
                if after_create["hard_blocking_findings"]:
                    raise MigrationBlocked("新建表核验失败: " + ", ".join(after_create["hard_blocking_findings"]))
                run_record.update({
                    "applied": True,
                    "action": "created_empty_canonical_table",
                    "snapshot_sha256": report["snapshot_sha256"],
                    "verified_snapshot_sha256": after_create["snapshot_sha256"],
                })
            else:
                if report["state"] == "legacy_only":
                    # DDL releases MySQL table locks. The external freeze and
                    # source digest check below guard the gap before relocking.
                    source_digest = report["source_table_sha256"]
                    comment_digest = report["comment_counts_sha256"]
                    cursor.execute("UNLOCK TABLES")
                    _create_canonical_table(cursor, database)
                    present = _vote_tables(cursor, database)
                    base_tables = _base_tables(cursor, database)
                    _lock_tables(cursor, present, base_tables)
                    after_create, present = _read_snapshot(cursor, database)
                    if present != {LEGACY_TABLE, CANONICAL_TABLE}:
                        raise MigrationBlocked("创建 canonical 后表状态不一致")
                    if after_create["source_table_sha256"] != source_digest or after_create["comment_counts_sha256"] != comment_digest:
                        raise MigrationBlocked("建表间隙源票/评论计数发生变化；已保留原表，请重新预检")
                    if after_create["user_ids_sha256"] != report["user_ids_sha256"]:
                        raise MigrationBlocked("建表间隙用户 ID 集合发生变化；已保留原表，请重新预检")
                    if after_create["canonical_rows"]:
                        raise MigrationBlocked("建表间隙 canonical 已出现新写入；重新预检并审批")
                    if after_create["hard_blocking_findings"]:
                        raise MigrationBlocked("新建表核验失败: " + ", ".join(after_create["hard_blocking_findings"]))
                    # The source-only approval hash remains valid because the
                    # only state change is this script's empty target table.
                    report = after_create

                if report["state"] != "both":
                    raise MigrationBlocked("迁移前置状态不是可合并的双表状态")
                source_rows = report["source_rows"]
                canonical_rows = report["canonical_rows"]
                id_mappings = _apply_rows(cursor, source_rows, canonical_rows, duplicate_pairs, kept_ids, remap_ids)
                after_merge, after_present = _read_snapshot(cursor, database)
                if after_present != {LEGACY_TABLE, CANONICAL_TABLE}:
                    raise MigrationBlocked("迁移后双表状态变化；保留现场并重新预检")
                _verify_merge_result(pre_migration_report, after_merge, id_mappings)
                run_record.update(
                    {
                        "applied": True,
                        "action": "merged_into_canonical_source_retained",
                        "snapshot_sha256": pre_migration_report["snapshot_sha256"],
                        "verified_snapshot_sha256": after_merge["snapshot_sha256"],
                        "id_mappings": id_mappings,
                    }
                )
            cursor.execute("UNLOCK TABLES")
            cursor.execute("SELECT RELEASE_LOCK(%s) AS released", (MIGRATION_LOCK_NAME,))
        return run_record
    except Exception:
        try:
            with connection.cursor() as cursor:
                cursor.execute("UNLOCK TABLES")
                cursor.execute("SELECT RELEASE_LOCK(%s)", (MIGRATION_LOCK_NAME,))
        except Exception:
            pass
        raise
    finally:
        connection.close()


def _vote_tables(cursor: Any, database: str) -> set[str]:
    cursor.execute(
        "SELECT table_name AS table_name FROM information_schema.tables WHERE table_schema=%s "
        "AND table_name IN (%s, %s)",
        (database, LEGACY_TABLE, CANONICAL_TABLE),
    )
    return {row["table_name"] for row in cursor.fetchall()}


def _validate_reference_ids(report: Mapping[str, Any]) -> None:
    rows = report.get("source_rows", []) + report.get("canonical_rows", [])
    # A database FK normally prevents these, but the explicit orphan check is
    # required for legacy schemas without constraints and for race diagnostics.
    for row in rows:
        if row["commentid"] not in report["valid_comment_ids"] or row["userid"] not in report["valid_user_ids"]:
            raise MigrationBlocked("存在孤儿票记录；不得迁移")


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", help="MySQL host (default: DB_HOST or localhost)")
    parser.add_argument("--port", type=int, help="MySQL port (default: DB_PORT or 3306)")
    parser.add_argument("--user", help="MySQL user (default: DB_USER); password is read only from DB_PASS")
    parser.add_argument("--database", help="database name (default: DB_NAME or woniunote)")
    parser.add_argument("--apply", action="store_true", help="apply an approved, resumable migration")
    parser.add_argument("--run-id", help="operator run identifier for this migration")
    parser.add_argument("--writes-frozen-run-id", help="explicit write-freeze assertion; must equal --run-id")
    parser.add_argument("--backup-file", help="non-empty backup artifact to checksum before apply")
    parser.add_argument("--backup-sha256", help="expected SHA-256 of --backup-file")
    parser.add_argument("--backup-restore-verified", action="store_true", help="assert that this backup was restored successfully in isolation")
    parser.add_argument("--preserve-comment-counts", action="store_true", help="approve preserving existing counts and reporting, not repairing, deltas")
    parser.add_argument("--approved-preflight-sha256", help="snapshot SHA-256 approved after reviewing a read-only preflight")
    parser.add_argument("--approval-file", help="JSON file with exact duplicate and ID-remap decisions")
    args = parser.parse_args(argv)
    args.host = args.host or os.environ.get("DB_HOST", "localhost")
    args.port = args.port or int(os.environ.get("DB_PORT", "3306"))
    args.database = args.database or os.environ.get("DB_NAME", "woniunote")
    args.user = args.user or os.environ.get("DB_USER")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        if args.apply:
            result = _run_apply(args)
            print(_canonical_json(result))
            return 0
        report = _run_preflight(args)
        print(_canonical_json(_safe_report(report)))
        return 2 if report["hard_blocking_findings"] else 0
    except MigrationBlocked as exc:
        print(_canonical_json({"status": "BLOCKED", "reason": str(exc)}), file=sys.stderr)
        return 2
    except Exception as exc:
        # Driver exceptions can contain connection details; only emit the type.
        print(_canonical_json({"status": "ERROR", "error_type": type(exc).__name__}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
