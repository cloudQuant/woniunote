"""Real MySQL and HTTP acceptance tests for the Iteration 21 math API."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import pytest
import requests

from iter21_support import RUN_ID, TIMEOUT, create_user, require_status, url


def valid_record_payload():
    return {
        "difficulty": 2,
        "total_questions": 5,
        "correct_count": 1,
        "wrong_count": 4,
        "accuracy": 99.0,  # The backend must derive the authoritative value.
        "start_time": "2026-10-23T10:00:00.000Z",
        "end_time": "2026-10-23T10:00:10.000Z",
        "duration_seconds": 10,
        "wrong_answers": [
            {
                "question": "题" * 100,
                "correct_answer": 3,
                "user_answer": None,
                "operation": "/",
            },
            {
                "question": "1.5 + 2.0",
                "correct_answer": 4,
                "user_answer": 3.75,
                "operation": "+",
            },
            {
                "question": "1 - 2",
                "correct_answer": -1,
                "user_answer": -0.25,
                "operation": "-",
            },
            {
                "question": "6 * 7",
                "correct_answer": 42,
                "user_answer": 0,
                "operation": "*",
            },
        ],
    }


def post_record(user, payload, *, timeout=TIMEOUT):
    return requests.post(
        url("/api/math-training/records"),
        headers=user.headers,
        json=payload,
        timeout=timeout,
    )


def post_record_raw(user, body):
    return requests.post(
        url("/api/math-training/records"),
        headers={**user.headers, "Content-Type": "application/json"},
        data=body,
        timeout=TIMEOUT,
    )


@lru_cache(maxsize=1)
def _owned_mysql_target():
    """Validate the active runner's exact Docker resource before any SQL use."""
    if not re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{12}", RUN_ID):
        pytest.fail("isolated runner did not provide a valid Iteration 21 run id")

    database = os.environ.get("WN_I21_DB_NAME", "")
    expected_database = f"woniunote_test_{RUN_ID.replace('-', '')}"
    if database != expected_database:
        pytest.fail("refusing MySQL access without this run's exact disposable schema")
    if os.environ.get("WN_I21_DB_HOST") != "127.0.0.1":
        pytest.fail("refusing MySQL access outside the runner's loopback target")
    if os.environ.get("WN_I21_DB_USER") != "root" or not os.environ.get("WN_I21_DB_PASSWORD"):
        pytest.fail("isolated runner did not provide its per-run MySQL credentials")

    port = os.environ.get("WN_I21_DB_PORT", "")
    if not re.fullmatch(r"[0-9]{1,5}", port) or not 1024 <= int(port) <= 65535:
        pytest.fail("isolated runner did not provide a valid mapped MySQL port")

    container = f"woniunote-i21-{RUN_ID}-mysql"
    inspect_template = (
        '{{.Id}}|{{.Name}}|{{index .Config.Labels "org.woniunote.iter21.run-id"}}|'
        '{{index .Config.Labels "org.woniunote.iter21.service"}}|{{.State.Running}}'
    )
    inspected = subprocess.run(
        ["docker", "inspect", "--format", inspect_template, container],
        capture_output=True,
        text=True,
        check=False,
    )
    if inspected.returncode != 0:
        pytest.fail("this run's labeled MySQL container is not available")
    fields = inspected.stdout.strip().split("|")
    if (
        len(fields) != 5
        or not re.fullmatch(r"[0-9a-f]{64}", fields[0])
        or fields[1] != f"/{container}"
        or fields[2] != RUN_ID
        or fields[3] != "mysql"
        or fields[4] != "true"
    ):
        pytest.fail("MySQL container ownership labels do not match this run")

    mapped = subprocess.run(
        ["docker", "port", fields[0], "3306/tcp"],
        capture_output=True,
        text=True,
        check=False,
    )
    expected_mapping = f"127.0.0.1:{port}"
    if mapped.returncode != 0 or mapped.stdout.splitlines() != [expected_mapping]:
        pytest.fail("MySQL port does not match this run's loopback mapping")

    return fields[0], container, database


def _mysql(sql, *, rows=False):
    container_id, _, database = _owned_mysql_target()
    password = os.environ["WN_I21_DB_PASSWORD"]
    result = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            "-e",
            f"MYSQL_PWD={password}",
            container_id,
            "mysql",
            "--protocol=tcp",
            "--host=127.0.0.1",
            "--connect-timeout=5",
            "--default-character-set=utf8mb4",
            "--user=root",
            "--batch",
            "--raw",
            "--skip-column-names",
            f"--database={database}",
            f"--execute={sql}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail("query against the runner-owned MySQL container failed")
    output = result.stdout.rstrip("\n")
    return output.splitlines() if rows else output.strip()


def _sql_string(value):
    return "'" + value.replace("'", "''") + "'"


def _wait_for_no_active_database_transaction(timeout=5):
    database = _sql_string(os.environ["WN_I21_DB_NAME"])
    active = (
        "SELECT COUNT(*) FROM information_schema.innodb_trx trx "
        "JOIN information_schema.processlist p "
        "ON p.id = trx.trx_mysql_thread_id "
        f"WHERE p.db = {database}"
    )
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _mysql(active) == "0":
            return
        time.sleep(0.1)
    assert _mysql(active) == "0", "math write transaction remained active after its response"


def _time_pair(offset_seconds=0):
    start = (datetime.now(timezone.utc) + timedelta(days=30, seconds=offset_seconds))
    start = start.replace(microsecond=0)
    end = start + timedelta(seconds=10)
    return (
        start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    )


def test_math_routes_require_authentication():
    response = requests.get(url("/api/math-training/records"), timeout=TIMEOUT)
    assert response.status_code == 401

    response = requests.post(
        url("/api/math-training/records"), json=valid_record_payload(), timeout=TIMEOUT
    )
    assert response.status_code == 401


def test_math_record_recomputes_accuracy_and_round_trips_all_operators(user):
    payload = valid_record_payload()
    response = post_record(user, payload)
    body = require_status(response, 200)
    record_id = body.get("data", {}).get("id")
    assert isinstance(record_id, int) and record_id > 0

    records = requests.get(
        url("/api/math-training/records"), headers=user.headers, timeout=TIMEOUT
    )
    records_body = require_status(records, 200)
    rows = records_body.get("data")
    assert isinstance(rows, list)
    record = next(row for row in rows if row.get("id") == record_id)
    assert record.get("accuracy") == 20.0
    assert records_body.get("page") == 1
    assert records_body.get("page_size") == 10

    detail = requests.get(
        url(f"/api/math-training/records/{record_id}"),
        headers=user.headers,
        timeout=TIMEOUT,
    )
    detail_body = require_status(detail, 200)
    answers = detail_body.get("data", {}).get("wrong_answers")
    assert isinstance(answers, list) and len(answers) == 4
    assert [item.get("user_answer") for item in answers] == [None, 3.75, -0.25, 0]
    assert answers[0].get("question") == payload["wrong_answers"][0]["question"]
    assert answers[2].get("correct_answer") == -1

    direct_record = _mysql(
        "SELECT CONCAT(CAST(accuracy * 100 AS UNSIGNED), '|', total_questions, '|', "
        f"correct_count, '|', wrong_count) FROM math_training_records "
        f"WHERE id = {record_id} AND user_id = {user.user_id}"
    )
    assert direct_record == "2000|5|1|4"
    direct_answers = _mysql(
        "SELECT CONCAT(operation, '|', IF(user_answer IS NULL, 'NULL', "
        "CAST(user_answer AS CHAR))) FROM math_training_wrong_answers "
        f"WHERE record_id = {record_id} AND user_id = {user.user_id} ORDER BY id",
        rows=True,
    )
    assert direct_answers == ["/|NULL", "+|3.75", "-|-0.25", "*|0"]

    for operation in ("+", "-", "*", "/"):
        filtered = requests.get(
            url("/api/math-training/wrong-answers"),
            headers=user.headers,
            params={"operation": operation},
            timeout=TIMEOUT,
        )
        filtered_body = require_status(filtered, 200)
        matches = [
            item
            for item in filtered_body.get("data", [])
            if item.get("record_id") == record_id
        ]
        assert len(matches) == 1
        assert matches[0].get("operation") == operation
        assert filtered_body.get("page") == 1
        assert filtered_body.get("page_size") == 20

    by_difficulty = requests.get(
        url("/api/math-training/records"),
        headers=user.headers,
        params={"difficulty": 2},
        timeout=TIMEOUT,
    )
    assert any(
        item.get("id") == record_id for item in require_status(by_difficulty, 200)["data"]
    )
    answers_by_difficulty = requests.get(
        url("/api/math-training/wrong-answers"),
        headers=user.headers,
        params={"difficulty": 2},
        timeout=TIMEOUT,
    )
    assert any(
        item.get("record_id") == record_id
        for item in require_status(answers_by_difficulty, 200)["data"]
    )


def test_math_accepts_zero_and_maximum_question_counts(user):
    zero = valid_record_payload()
    zero.update(
        total_questions=0,
        correct_count=0,
        wrong_count=0,
        accuracy=88.8,
        wrong_answers=[],
    )
    zero["start_time"], zero["end_time"] = _time_pair(0)
    zero_response = post_record(user, zero)
    zero_body = require_status(zero_response, 200)
    zero_id = zero_body["data"]["id"]

    maximum = valid_record_payload()
    maximum.update(
        total_questions=1000,
        correct_count=1000,
        wrong_count=0,
        accuracy=0,
        wrong_answers=[],
    )
    maximum["start_time"], maximum["end_time"] = _time_pair(20)
    maximum_response = post_record(user, maximum)
    maximum_body = require_status(maximum_response, 200)
    maximum_id = maximum_body["data"]["id"]

    listed = require_status(
        requests.get(url("/api/math-training/records"), headers=user.headers, timeout=TIMEOUT),
        200,
    )["data"]
    assert next(row for row in listed if row["id"] == zero_id)["accuracy"] == 0.0
    assert next(row for row in listed if row["id"] == maximum_id)["accuracy"] == 100.0
    assert _mysql(
        "SELECT CONCAT(total_questions, '|', correct_count, '|', wrong_count, '|', "
        "CAST(accuracy * 100 AS UNSIGNED)) FROM math_training_records "
        f"WHERE id = {zero_id} AND user_id = {user.user_id}"
    ) == "0|0|0|0"
    assert _mysql(
        "SELECT CONCAT(total_questions, '|', correct_count, '|', wrong_count, '|', "
        "CAST(accuracy * 100 AS UNSIGNED)) FROM math_training_records "
        f"WHERE id = {maximum_id} AND user_id = {user.user_id}"
    ) == "1000|1000|0|10000"
    assert _mysql(
        "SELECT COUNT(*) FROM math_training_wrong_answers "
        f"WHERE record_id IN ({zero_id}, {maximum_id}) AND user_id = {user.user_id}"
    ) == "0"


def test_math_time_contract_uses_rounded_elapsed_seconds(user):
    payload = valid_record_payload()
    payload.update(total_questions=0, correct_count=0, wrong_count=0, wrong_answers=[])
    payload["start_time"] = "2026-10-23T10:00:00.000Z"
    payload["end_time"] = "2026-10-23T10:00:01.490Z"
    for duration in (0, 2):
        payload["duration_seconds"] = duration
        accepted = post_record(user, payload)
        require_status(accepted, 200)

    payload["duration_seconds"] = 3
    rejected = post_record(user, payload)
    assert rejected.status_code == 400

    payload["start_time"] = "2026-10-23T10:00:00Z"
    payload["end_time"] = "2026-10-23T10:00:01Z"
    payload["duration_seconds"] = 1
    require_status(post_record(user, payload), 200)


def test_math_strict_json_types_dates_and_answer_bounds(user):
    base = valid_record_payload()
    invalid_payloads = []

    invalid_payloads.append([])
    invalid_payloads.append({"difficulty": 2})

    for field, value in (
        ("difficulty", "2"),
        ("total_questions", 5.0),
        ("correct_count", True),
        ("wrong_count", "4"),
        ("duration_seconds", 10.0),
        ("accuracy", "99"),
        ("wrong_answers", {}),
    ):
        invalid = {**base, field: value}
        invalid_payloads.append(invalid)

    invalid = {**base}
    invalid["total_questions"] = 6
    invalid_payloads.append(invalid)

    invalid = {**base, "total_questions": 1001, "correct_count": 1001, "wrong_count": 0, "wrong_answers": []}
    invalid_payloads.append(invalid)

    for answer_field, value in (
        ("question", ""),
        ("question", "题" * 101),
        ("correct_answer", "3"),
        ("correct_answer", 3.0),
        ("correct_answer", 2_147_483_648),
        ("user_answer", "3.75"),
        ("user_answer", 2_147_483_648),
        ("user_answer", -2_147_483_649),
        ("operation", "x"),
    ):
        invalid = {**base, "wrong_answers": [dict(item) for item in base["wrong_answers"]]}
        invalid["wrong_answers"][0][answer_field] = value
        invalid_payloads.append(invalid)

    invalid_dates = (
        ("2026-10-23T10:00:00+00:00", "2026-10-23T10:00:10Z"),
        ("2026-10-23T10:00:00Z", "2026-10-23T09:59:59Z"),
        ("2026-02-29T10:00:00Z", "2026-02-29T10:00:10Z"),
        ("2026-10-23T10:00:00.0000Z", "2026-10-23T10:00:10Z"),
    )
    for start, end in invalid_dates:
        invalid = {**base, "start_time": start, "end_time": end}
        invalid_payloads.append(invalid)

    for payload in invalid_payloads:
        response = post_record(user, payload)
        assert response.status_code == 400, f"unexpectedly accepted invalid payload: {payload!r}"

    for answer in (float("inf"), float("nan")):
        invalid = {**base, "accuracy": answer}
        response = post_record_raw(user, json.dumps(invalid, allow_nan=True))
        assert response.status_code == 400
        invalid_answer = {**base, "wrong_answers": [dict(item) for item in base["wrong_answers"]]}
        invalid_answer["wrong_answers"][0]["user_answer"] = answer
        response = post_record_raw(user, json.dumps(invalid_answer, allow_nan=True))
        assert response.status_code == 400

    valid_boundary = valid_record_payload()
    valid_boundary["wrong_answers"][1]["user_answer"] = -2_147_483_647
    valid_boundary["wrong_answers"][2]["correct_answer"] = -2_147_483_648
    boundary_response = post_record(user, valid_boundary)
    require_status(boundary_response, 200)


def test_math_explicit_pagination_rejects_malformed_values_and_checks_offset(user):
    records = require_status(
        requests.get(url("/api/math-training/records"), headers=user.headers, timeout=TIMEOUT),
        200,
    )
    assert records["page"] == 1 and records["page_size"] == 10

    wrong_answers = require_status(
        requests.get(
            url("/api/math-training/wrong-answers"), headers=user.headers, timeout=TIMEOUT
        ),
        200,
    )
    assert wrong_answers["page"] == 1 and wrong_answers["page_size"] == 20

    bad_page_params = (
        {"page": ""},
        {"page": "abc"},
        {"page": "0"},
        {"page": "-1"},
        {"page": "1x"},
        {"page": "999999999999999999999999999999999999"},
        {"page_size": ""},
        {"page_size": "0"},
        {"page_size": "-1"},
        {"page_size": "101"},
        {"page": "1000002", "page_size": "1"},
        {"page": "100002", "page_size": "10"},
    )
    for path in ("/api/math-training/records", "/api/math-training/wrong-answers"):
        for params in bad_page_params:
            response = requests.get(url(path), headers=user.headers, params=params, timeout=TIMEOUT)
            assert response.status_code == 400, (path, params)

    boundary = requests.get(
        url("/api/math-training/records"),
        headers=user.headers,
        params={"page": "1000001", "page_size": "1"},
        timeout=TIMEOUT,
    )
    boundary_body = require_status(boundary, 200)
    assert boundary_body["page"] == 1000001
    assert boundary_body["page_size"] == 1

    for path, filter_names in (
        ("/api/math-training/records", ("difficulty",)),
        ("/api/math-training/wrong-answers", ("difficulty", "operation")),
    ):
        invalid_values = {
            "difficulty": ("", "0", "4", "2x"),
            "operation": ("", "x"),
        }
        for name in filter_names:
            for value in invalid_values[name]:
                params = {name: value}
                response = requests.get(
                    url(path),
                    headers=user.headers,
                    params=params,
                    timeout=TIMEOUT,
                )
                assert response.status_code == 400, (path, params)


def test_math_records_sort_tied_timestamps_by_id_and_paginate_without_drift(user):
    created_ids = []
    for offset in (0, 20):
        payload = valid_record_payload()
        payload.update(total_questions=0, correct_count=0, wrong_count=0, wrong_answers=[])
        payload["start_time"], payload["end_time"] = _time_pair(offset)
        response = post_record(user, payload)
        created_ids.append(require_status(response, 200)["data"]["id"])

    _mysql(
        "UPDATE math_training_records SET created_at = '2099-01-01 00:00:00' "
        f"WHERE user_id = {user.user_id} AND id IN ({created_ids[0]}, {created_ids[1]})"
    )
    first_page = require_status(
        requests.get(
            url("/api/math-training/records"),
            headers=user.headers,
            params={"page": 1, "page_size": 1},
            timeout=TIMEOUT,
        ),
        200,
    )["data"]
    second_page = require_status(
        requests.get(
            url("/api/math-training/records"),
            headers=user.headers,
            params={"page": 2, "page_size": 1},
            timeout=TIMEOUT,
        ),
        200,
    )["data"]
    assert [row["id"] for row in first_page + second_page] == sorted(created_ids, reverse=True)

    payload = valid_record_payload()
    payload.update(
        total_questions=3,
        correct_count=0,
        wrong_count=3,
        wrong_answers=[dict(item) for item in payload["wrong_answers"][:3]],
    )
    payload["start_time"], payload["end_time"] = _time_pair(40)
    record_id = require_status(post_record(user, payload), 200)["data"]["id"]
    _mysql(
        "UPDATE math_training_wrong_answers SET created_at = '2099-01-01 00:00:00' "
        f"WHERE user_id = {user.user_id} AND record_id = {record_id}"
    )
    expected_ids = [
        int(value)
        for value in _mysql(
            "SELECT id FROM math_training_wrong_answers "
            f"WHERE user_id = {user.user_id} AND record_id = {record_id} ORDER BY id DESC",
            rows=True,
        )
    ]
    pages = []
    for page in (1, 2):
        response = requests.get(
            url("/api/math-training/wrong-answers"),
            headers=user.headers,
            params={"page": page, "page_size": 2},
            timeout=TIMEOUT,
        )
        data = require_status(response, 200)["data"]
        pages.extend(item["id"] for item in data if item["record_id"] == record_id)
    assert pages == expected_ids


def test_math_records_and_wrong_answers_are_user_scoped(user):
    created = post_record(user, valid_record_payload())
    record_id = require_status(created, 200)["data"]["id"]
    other = create_user()

    other_detail = requests.get(
        url(f"/api/math-training/records/{record_id}"),
        headers=other.headers,
        timeout=TIMEOUT,
    )
    assert other_detail.status_code == 404

    other_records = require_status(
        requests.get(
            url("/api/math-training/records"), headers=other.headers, timeout=TIMEOUT
        ),
        200,
    )
    assert all(row.get("id") != record_id for row in other_records.get("data", []))

    other_answers = require_status(
        requests.get(
            url("/api/math-training/wrong-answers"), headers=other.headers, timeout=TIMEOUT
        ),
        200,
    )
    assert all(row.get("record_id") != record_id for row in other_answers.get("data", []))


@pytest.mark.parametrize("failure_index", [0, 1, 2], ids=["first", "middle", "last"])
def test_math_wrong_answer_insert_failure_rolls_back_parent_and_all_children(user, failure_index):
    marker = f"I21_FAIL_{RUN_ID.replace('-', '')}_{failure_index}"
    check_name = f"chk_i21_math_fail_{failure_index}"
    start_time, end_time = _time_pair(100 + failure_index * 20)
    payload = valid_record_payload()
    payload.update(
        total_questions=3,
        correct_count=0,
        wrong_count=3,
        accuracy=0,
        start_time=start_time,
        end_time=end_time,
        wrong_answers=[
            {
                "question": f"I21_CASE_{RUN_ID.replace('-', '')}_{failure_index}_{index}",
                "correct_answer": index + 1,
                "user_answer": index + 0.5,
                "operation": "+",
            }
            for index in range(3)
        ],
    )
    payload["wrong_answers"][failure_index]["question"] = marker
    case_prefix = f"I21_CASE_{RUN_ID.replace('-', '')}_{failure_index}_%"
    _mysql(
        "ALTER TABLE math_training_wrong_answers "
        f"ADD CONSTRAINT `{check_name}` CHECK (question <> {_sql_string(marker)})"
    )
    try:
        response = post_record(user, payload)
        assert response.status_code == 500
        body = response.json()
        assert body.get("error_code") != "WRITE_OUTCOME_UNKNOWN"
        _wait_for_no_active_database_transaction()

        stored_parent_count = _mysql(
            "SELECT COUNT(*) FROM math_training_records "
            f"WHERE user_id = {user.user_id} AND start_time = "
            f"{_sql_string(start_time[:19].replace('T', ' '))}"
        )
        stored_children_count = _mysql(
            "SELECT COUNT(*) FROM math_training_wrong_answers "
            f"WHERE user_id = {user.user_id} AND question LIKE "
            f"{_sql_string(case_prefix)}"
        )
        assert stored_parent_count == "0"
        assert stored_children_count == "0"
    finally:
        _mysql(f"ALTER TABLE math_training_wrong_answers DROP CHECK `{check_name}`")


def test_math_deadline_reports_unknown_and_does_not_commit_late_success(user):
    trigger_name = f"trg_i21_math_timeout_{user.user_id}"
    start_time, end_time = _time_pair(200)
    payload = valid_record_payload()
    payload.update(total_questions=0, correct_count=0, wrong_count=0, wrong_answers=[])
    payload["start_time"] = start_time
    payload["end_time"] = end_time

    _mysql(
        f"CREATE TRIGGER `{trigger_name}` BEFORE INSERT ON math_training_records "
        "FOR EACH ROW SET @i21_math_sleep = SLEEP(11)"
    )
    try:
        # A single direct HTTP attempt: this code path has no retry adapter.
        response = post_record(user, payload, timeout=15)
        assert response.status_code == 503
        body = response.json()
        assert body.get("error_code") == "WRITE_OUTCOME_UNKNOWN"
        assert isinstance(body.get("request_id"), str) and body["request_id"]

        active_insert = (
            "SELECT COUNT(*) FROM information_schema.processlist "
            f"WHERE db = {_sql_string(os.environ['WN_I21_DB_NAME'])} "
            "AND lower(COALESCE(info, '')) LIKE 'insert into math_training_records%'"
        )
        deadline = time.monotonic() + 5
        while _mysql(active_insert) != "0" and time.monotonic() < deadline:
            time.sleep(0.1)
        assert _mysql(active_insert) == "0", "timed-out SQL callback did not finish promptly"
        assert _mysql(
            "SELECT COUNT(*) FROM math_training_records "
            f"WHERE user_id = {user.user_id} AND start_time = "
            f"{_sql_string(start_time[:19].replace('T', ' '))}"
        ) == "0"
    finally:
        _mysql(f"DROP TRIGGER `{trigger_name}`")


def test_math_answer_migration_is_idempotent_and_preserves_legacy_values():
    container_id, _, database = _owned_mysql_target()
    env = os.environ.copy()
    env.update(
        {
            "WONIUNOTE_TEST_RUN_ID": RUN_ID,
            "WONIUNOTE_TEST_MYSQL_CONTAINER_ID": container_id,
            "WONIUNOTE_TEST_DB_NAME": database,
            "WONIUNOTE_TEST_DB_HOST": os.environ["WN_I21_DB_HOST"],
            "WONIUNOTE_TEST_DB_PORT": os.environ["WN_I21_DB_PORT"],
            "WONIUNOTE_TEST_DB_USER": os.environ["WN_I21_DB_USER"],
            "WONIUNOTE_TEST_DB_PASSWORD": os.environ["WN_I21_DB_PASSWORD"],
        }
    )
    migration_script = (
        Path(__file__).resolve().parents[3] / "scripts/tests/test_math_training_migration.sh"
    )
    result = subprocess.run(
        ["bash", str(migration_script)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=60,
    )
    assert result.returncode == 0, "owned migration test failed: " + result.stderr.strip()
    assert "PASS: owned MySQL math-answer migration" in result.stdout
