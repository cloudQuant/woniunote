"""Real MySQL transaction-boundary contracts for Iteration 21 writes."""

from __future__ import annotations

import json
import socket
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import pytest
import requests

from iter21_support import (
    TIMEOUT,
    UserCredentials,
    create_article,
    create_user,
    owned_mysql_connection,
    register_user,
    require_status,
    url,
)
from test_iter21_transport_faults import (
    TEST_TIMEOUT_SECONDS,
    _FaultBackend,
    _login_at,
    _require_mysql_fault_observable,
    _record_fault_evidence,
)


def _db_connection():
    connection = owned_mysql_connection()
    connection.autocommit(True)
    return connection


def _create_comment(user, article_id: int, content: str) -> int:
    response = requests.post(
        url("/api/comments"),
        headers=user.headers,
        json={"articleid": article_id, "content": content},
        timeout=TIMEOUT,
    )
    body = require_status(response, 200)
    assert body.get("code") == 200
    comment_id = body.get("data", {}).get("commentid")
    assert isinstance(comment_id, int) and comment_id > 0
    return comment_id


def _vote(user, comment_id: int):
    return requests.post(
        url(f"/api/comments/{comment_id}/vote"),
        headers=user.headers,
        json={"vote_type": 1},
        timeout=TIMEOUT,
    )


def _vote_at(base_url: str, headers: dict[str, str], comment_id: int, session):
    return session.post(
        f"{base_url}/api/comments/{comment_id}/vote",
        headers=headers,
        json={"vote_type": 1},
        timeout=TIMEOUT + 2,
    )


def _comment_vote_state(connection, comment_id: int):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT agreecount, opposecount FROM `comment` WHERE commentid = %s",
            (comment_id,),
        )
        counts = cursor.fetchone()
        cursor.execute(
            "SELECT userid, vote_type FROM comment_votes "
            "WHERE commentid = %s ORDER BY userid",
            (comment_id,),
        )
        votes = cursor.fetchall()
    return counts, votes


def _secondary_headers(base_url: str, credentials: UserCredentials) -> dict[str, str]:
    session = _login_at(base_url, credentials)
    token = session.get("access_token")
    assert isinstance(token, str) and token
    return {"Authorization": f"Bearer {token}"}


def _training_payload(question: str) -> dict:
    start = datetime.now(timezone.utc).replace(microsecond=0)
    end = start + timedelta(seconds=10)
    return {
        "difficulty": 2,
        "total_questions": 2,
        "correct_count": 1,
        "wrong_count": 1,
        "accuracy": 50.0,
        "start_time": start.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "end_time": end.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "duration_seconds": 10,
        "wrong_answers": [
            {
                "question": question,
                "correct_answer": 7,
                "user_answer": 6.5,
                "operation": "+",
            }
        ],
    }


def _post_training(base_url: str, headers: dict[str, str], payload: dict, *, timeout: float):
    return requests.post(
        f"{base_url}/api/math-training/records",
        headers=headers,
        json=payload,
        timeout=timeout,
    )


def _training_rows(connection, user_id: int, question: str):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT r.id, r.total_questions, r.correct_count, r.wrong_count, r.accuracy, "
            "COUNT(w.id) FROM math_training_records AS r "
            "JOIN math_training_wrong_answers AS w ON w.record_id = r.id "
            "WHERE r.user_id = %s AND w.question = %s "
            "GROUP BY r.id, r.total_questions, r.correct_count, r.wrong_count, r.accuracy",
            (user_id, question),
        )
        return cursor.fetchall()


def _poll_training_rows(user_id: int, question: str, *, timeout: float = 12.0):
    deadline = time.monotonic() + timeout
    connection = _db_connection()
    try:
        while time.monotonic() < deadline:
            rows = _training_rows(connection, user_id, question)
            if rows:
                return rows
            time.sleep(0.1)
        return _training_rows(connection, user_id, question)
    finally:
        connection.close()


def _assert_unknown_write_response(response: requests.Response) -> str:
    body = require_status(response, 503)
    assert body.get("code") == 503
    assert body.get("error_code") == "WRITE_OUTCOME_UNKNOWN"
    request_id = body.get("request_id")
    assert isinstance(request_id, str) and request_id
    return request_id


def _blocked_article_lock_visible(connection) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.PROCESSLIST "
            "WHERE DB = DATABASE() AND INFO LIKE %s",
            ("SELECT userid, hidden, drafted FROM article WHERE articleid =%",),
        )
        return cursor.fetchone()[0] > 0


@pytest.mark.fault_injection
def test_vote_prewrite_lock_deadline_returns_known_unavailable_without_write(fault_backend):
    author = create_user()
    article_id = create_article(author)
    comment_id = _create_comment(author, article_id, f"i21 prewrite timeout {uuid.uuid4().hex}")
    voter = create_user()
    headers = _secondary_headers(fault_backend.base_url, voter)

    lock_owner = owned_mysql_connection()
    lock_owner.autocommit(False)
    observer = _db_connection()
    session = requests.Session()
    executor = ThreadPoolExecutor(max_workers=1)
    response_future = None
    try:
        with lock_owner.cursor() as cursor:
            cursor.execute(
                "SELECT articleid FROM article WHERE articleid = %s FOR UPDATE",
                (article_id,),
            )

        started = time.monotonic()
        response_future = executor.submit(
            _vote_at, fault_backend.base_url, headers, comment_id, session
        )
        lock_deadline = time.monotonic() + 3.0
        while time.monotonic() < lock_deadline and not _blocked_article_lock_visible(observer):
            if response_future.done():
                break
            time.sleep(0.05)
        assert _blocked_article_lock_visible(observer), (
            "vote did not reach the pre-write article row lock"
        )

        response = response_future.result(timeout=TIMEOUT + 2)
        elapsed = time.monotonic() - started
        body = require_status(response, 503)
        assert body.get("code") == 503
        assert body.get("error_code") != "WRITE_OUTCOME_UNKNOWN"
        assert elapsed >= 4.5

        counts, votes = _comment_vote_state(observer, comment_id)
        assert counts == (0, 0)
        assert votes == ()
    finally:
        observer.close()
        lock_owner.close()
        if response_future is not None and not response_future.done():
            response_future.result(timeout=TIMEOUT + 2)
        executor.shutdown(wait=True, cancel_futures=True)

    # The late SELECT completes after the timeout. Reusing the same HTTP
    # session checks that its completion does not write or corrupt the next
    # request on that connection.
    time.sleep(0.2)
    retry = _vote_at(fault_backend.base_url, headers, comment_id, session)
    assert require_status(retry, 200).get("code") == 200
    connection = _db_connection()
    try:
        assert _comment_vote_state(connection, comment_id) == (
            (1, 0),
            ((voter.user_id, 1),),
        )
    finally:
        connection.close()
        session.close()


@pytest.mark.fault_injection
def test_vote_comment_lock_reply_drop_returns_known_unavailable_without_write(fault_backend):
    author = create_user()
    article_id = create_article(author)
    comment_id = _create_comment(author, article_id, f"i21 comment lock drop {uuid.uuid4().hex}")
    voter = create_user()
    headers = _secondary_headers(fault_backend.base_url, voter)
    fault_backend.mysql_proxy.reset_metrics()
    fault_backend.redis_proxy.reset_metrics()
    _require_mysql_fault_observable(fault_backend.mysql_proxy)
    fault_backend.mysql_proxy.arm("mysql.vote.comment_lock", "drop")
    try:
        response = requests.post(
            f"{fault_backend.base_url}/api/comments/{comment_id}/vote",
            headers=headers,
            json={"vote_type": 1},
            timeout=TEST_TIMEOUT_SECONDS + 2,
        )
        metrics = fault_backend.mysql_proxy.snapshot()
        assert metrics["matched"] == 1
        assert metrics["replies_dropped"] == 1
        assert metrics["dropped_connection_closes"] == 1
        assert metrics["mysql_vote_comment_lock_packets"] == 1
        assert metrics["protocol_gaps"] == 0
        body = require_status(response, 503)
        assert body.get("code") == 503
        assert body.get("error_code") != "WRITE_OUTCOME_UNKNOWN"

        connection = _db_connection()
        try:
            assert _comment_vote_state(connection, comment_id) == ((0, 0), ())
        finally:
            connection.close()
    finally:
        _record_fault_evidence(
            "mysql-vote-comment-lock-reply-drop",
            fault_backend.mysql_proxy,
            fault_backend.redis_proxy,
        )


@pytest.mark.fault_injection
def test_vote_first_business_write_reply_drop_returns_unknown_with_readback(fault_backend):
    author = create_user()
    article_id = create_article(author)
    comment_id = _create_comment(author, article_id, f"i21 vote write drop {uuid.uuid4().hex}")
    voter = create_user()
    headers = _secondary_headers(fault_backend.base_url, voter)
    connection = _db_connection()
    try:
        before = _comment_vote_state(connection, comment_id)
    finally:
        connection.close()
    assert before == ((0, 0), ())

    fault_backend.mysql_proxy.reset_metrics()
    fault_backend.redis_proxy.reset_metrics()
    _require_mysql_fault_observable(fault_backend.mysql_proxy)
    fault_backend.mysql_proxy.arm("mysql.vote.business_write", "drop")
    try:
        response = requests.post(
            f"{fault_backend.base_url}/api/comments/{comment_id}/vote",
            headers=headers,
            json={"vote_type": 1},
            timeout=TEST_TIMEOUT_SECONDS + 2,
        )
        metrics = fault_backend.mysql_proxy.snapshot()
        assert metrics["matched"] == 1
        assert metrics["replies_dropped"] == 1
        assert metrics["dropped_connection_closes"] == 1
        assert metrics["mysql_vote_business_write_packets"] == 1
        assert metrics["protocol_gaps"] == 0
        _assert_unknown_write_response(response)

        connection = _db_connection()
        try:
            assert _comment_vote_state(connection, comment_id) == before
        finally:
            connection.close()
    finally:
        _record_fault_evidence(
            "mysql-vote-first-business-write-reply-drop",
            fault_backend.mysql_proxy,
            fault_backend.redis_proxy,
        )


def _send_request_and_drop_response(base_url: str, path: str, headers: dict, payload: dict) -> None:
    parsed = urlsplit(base_url)
    assert parsed.scheme == "http" and parsed.hostname == "127.0.0.1"
    assert parsed.port is not None
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request_headers = {
        "Host": f"{parsed.hostname}:{parsed.port}",
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
        "Connection": "close",
        **headers,
    }
    header_text = "POST " + path + " HTTP/1.1\r\n"
    header_text += "".join(f"{name}: {value}\r\n" for name, value in request_headers.items())
    sock = socket.create_connection((parsed.hostname, parsed.port), timeout=5)
    try:
        sock.sendall(header_text.encode("ascii") + b"\r\n" + body)
        # Finish the request bytes, then drop the client socket without reading
        # any response. The server still receives the request followed by EOF.
        try:
            sock.shutdown(socket.SHUT_WR)
        except OSError:
            # A very fast response may close the peer while this client is
            # half-closing; the request was already queued by sendall().
            pass
    finally:
        sock.close()


@pytest.fixture
def fault_backend():
    backend = _FaultBackend()
    try:
        backend.start()
        yield backend
    finally:
        backend.close()


def test_concurrent_votes_count_once_per_user_and_accumulate_for_distinct_users():
    author = create_user()
    article_id = create_article(author)
    comment_id = _create_comment(author, article_id, f"i21 vote race {uuid.uuid4().hex}")
    first_voter = create_user()

    same_user_start = threading.Barrier(3)

    def same_user_vote():
        same_user_start.wait(timeout=10)
        return _vote(first_voter, comment_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        duplicate_attempts = [pool.submit(same_user_vote) for _ in range(2)]
        same_user_start.wait(timeout=10)
        duplicate_responses = [future.result(timeout=TIMEOUT + 5) for future in duplicate_attempts]
    assert sorted(response.status_code for response in duplicate_responses) == [200, 400]

    other_voters = [create_user(), create_user()]
    distinct_start = threading.Barrier(len(other_voters) + 1)

    def distinct_user_vote(voter):
        distinct_start.wait(timeout=10)
        return _vote(voter, comment_id)

    with ThreadPoolExecutor(max_workers=len(other_voters)) as pool:
        distinct_attempts = [pool.submit(distinct_user_vote, voter) for voter in other_voters]
        distinct_start.wait(timeout=10)
        distinct_responses = [future.result(timeout=TIMEOUT + 5) for future in distinct_attempts]
    assert [response.status_code for response in distinct_responses] == [200] * len(other_voters)

    connection = _db_connection()
    try:
        counts, votes = _comment_vote_state(connection, comment_id)
    finally:
        connection.close()
    expected_users = sorted([first_voter.user_id, *(voter.user_id for voter in other_voters)])
    assert counts == (len(expected_users), 0)
    assert votes == tuple((user_id, 1) for user_id in expected_users)


@pytest.mark.fault_injection
def test_vote_count_update_sql_failure_rolls_back_inserted_vote_and_count():
    author = create_user()
    voter = create_user()
    article_id = create_article(author)
    comment_id = _create_comment(author, article_id, f"i21 vote rollback {uuid.uuid4().hex}")
    trigger_name = f"trg_i21_vote_failure_{uuid.uuid4().hex[:16]}"
    connection = _db_connection()
    trigger_created = False
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE TRIGGER `{trigger_name}` BEFORE UPDATE ON `comment` "
                "FOR EACH ROW BEGIN "
                f"IF OLD.commentid = {comment_id} AND NEW.agreecount > OLD.agreecount THEN "
                "SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'i21 injected vote count failure'; "
                "END IF; END"
            )
        trigger_created = True

        response = _vote(voter, comment_id)
        assert require_status(response, 500).get("code") == 500
    finally:
        try:
            if trigger_created:
                with connection.cursor() as cursor:
                    cursor.execute(f"DROP TRIGGER IF EXISTS `{trigger_name}`")
        finally:
            connection.close()

    connection = _db_connection()
    try:
        counts, votes = _comment_vote_state(connection, comment_id)
    finally:
        connection.close()
    assert counts == (0, 0)
    assert votes == ()


@pytest.mark.fault_injection
def test_training_commit_ack_drop_returns_unknown_but_persists_once(fault_backend):
    credentials = register_user()
    headers = _secondary_headers(fault_backend.base_url, credentials)
    question = f"i21-training-{uuid.uuid4().hex}"
    payload = _training_payload(question)
    fault_backend.mysql_proxy.reset_metrics()
    fault_backend.redis_proxy.reset_metrics()
    _require_mysql_fault_observable(fault_backend.mysql_proxy)
    fault_backend.mysql_proxy.arm("mysql.commit", "drop")
    try:
        started = time.monotonic()
        response = _post_training(
            fault_backend.base_url,
            headers,
            payload,
            timeout=TEST_TIMEOUT_SECONDS + 7,
        )
        elapsed = time.monotonic() - started
        assert elapsed <= TEST_TIMEOUT_SECONDS + 3
        metrics = fault_backend.mysql_proxy.snapshot()
        assert metrics["matched"] == 1
        assert metrics["replies_dropped"] == 1
        assert metrics["protocol_gaps"] == 0
        _assert_unknown_write_response(response)

        rows = _poll_training_rows(credentials.user_id, question)
        assert len(rows) == 1
        record_id, total, correct, wrong, accuracy, wrong_answer_count = rows[0]
        assert record_id > 0
        assert (total, correct, wrong, float(accuracy), wrong_answer_count) == (2, 1, 1, 50.0, 1)
        assert len(_poll_training_rows(credentials.user_id, question, timeout=0.5)) == 1
    finally:
        _record_fault_evidence(
            "mysql-training-commit-ack-drop",
            fault_backend.mysql_proxy,
            fault_backend.redis_proxy,
        )


@pytest.mark.fault_injection
def test_vote_commit_ack_drop_returns_unknown_but_persists_once(fault_backend):
    author = create_user()
    article_id = create_article(author)
    comment_id = _create_comment(author, article_id, f"i21 vote ack {uuid.uuid4().hex}")
    credentials = register_user()
    headers = _secondary_headers(fault_backend.base_url, credentials)
    fault_backend.mysql_proxy.reset_metrics()
    fault_backend.redis_proxy.reset_metrics()
    _require_mysql_fault_observable(fault_backend.mysql_proxy)
    fault_backend.mysql_proxy.arm("mysql.commit", "drop")
    try:
        started = time.monotonic()
        response = requests.post(
            f"{fault_backend.base_url}/api/comments/{comment_id}/vote",
            headers=headers,
            json={"vote_type": 1},
            timeout=TEST_TIMEOUT_SECONDS + 2,
        )
        elapsed = time.monotonic() - started
        assert elapsed <= TEST_TIMEOUT_SECONDS
        metrics = fault_backend.mysql_proxy.snapshot()
        assert metrics["matched"] == 1
        assert metrics["replies_dropped"] == 1
        assert metrics["protocol_gaps"] == 0
        _assert_unknown_write_response(response)

        connection = _db_connection()
        try:
            counts, votes = _comment_vote_state(connection, comment_id)
        finally:
            connection.close()
        assert counts == (1, 0)
        assert votes == ((credentials.user_id, 1),)
    finally:
        _record_fault_evidence(
            "mysql-vote-commit-ack-drop",
            fault_backend.mysql_proxy,
            fault_backend.redis_proxy,
        )


@pytest.mark.fault_injection
def test_training_write_persists_once_when_client_drops_http_response(fault_backend):
    credentials = register_user()
    headers = _secondary_headers(fault_backend.base_url, credentials)
    question = f"i21-dropped-response-training-{uuid.uuid4().hex}"
    _send_request_and_drop_response(
        fault_backend.base_url,
        "/api/math-training/records",
        headers,
        _training_payload(question),
    )

    rows = _poll_training_rows(credentials.user_id, question)
    assert len(rows) == 1
    assert rows[0][1:] == (2, 1, 1, 50.0, 1)
    time.sleep(0.25)
    assert len(_poll_training_rows(credentials.user_id, question, timeout=0.5)) == 1


@pytest.mark.fault_injection
def test_vote_persists_once_when_client_drops_http_response(fault_backend):
    author = create_user()
    article_id = create_article(author)
    comment_id = _create_comment(author, article_id, f"i21 dropped response {uuid.uuid4().hex}")
    credentials = register_user()
    headers = _secondary_headers(fault_backend.base_url, credentials)
    _send_request_and_drop_response(
        fault_backend.base_url,
        f"/api/comments/{comment_id}/vote",
        headers,
        {"vote_type": 1},
    )

    deadline = time.monotonic() + 8
    connection = _db_connection()
    try:
        state = None
        while time.monotonic() < deadline:
            counts, votes = _comment_vote_state(connection, comment_id)
            if votes:
                state = (counts, votes)
                break
            time.sleep(0.1)
    finally:
        connection.close()
    assert state == ((1, 0), ((credentials.user_id, 1),))
    time.sleep(0.25)
    connection = _db_connection()
    try:
        assert _comment_vote_state(connection, comment_id) == (
            (1, 0),
            ((credentials.user_id, 1),),
        )
    finally:
        connection.close()
