"""Black-box comment permissions, hierarchy and vote persistence contracts."""

from concurrent.futures import ThreadPoolExecutor
import time

import requests

from iter21_support import (
    TIMEOUT,
    create_article,
    create_user,
    owned_mysql_connection,
    require_status,
    response_json,
    url,
)


def _create_comment(user, article_id, content, *, reply_id=None):
    payload = {"articleid": article_id, "content": content}
    if reply_id is not None:
        payload["replyid"] = reply_id
    response = requests.post(
        url("/api/comments"),
        headers=user.headers,
        json=payload,
        timeout=TIMEOUT,
    )
    body = require_status(response, 200)
    assert body.get("code") == 200
    comment_id = body.get("data", {}).get("commentid")
    assert isinstance(comment_id, int) and comment_id > 0
    return comment_id


def _list_comments(article_id, *, headers=None):
    response = requests.get(
        url(f"/api/comments/article/{article_id}"),
        headers=headers,
        timeout=TIMEOUT,
    )
    return response


def test_comment_auth_direct_replies_votes_and_public_user_projection():
    author = create_user()
    voter = create_user()
    article_id = create_article(author)

    anonymous_create = requests.post(
        url("/api/comments"),
        json={"articleid": article_id, "content": "anonymous"},
        timeout=TIMEOUT,
    )
    assert anonymous_create.status_code == 401
    anonymous_vote = requests.post(
        url("/api/comments/1/vote"), json={"vote_type": 1}, timeout=TIMEOUT
    )
    assert anonymous_vote.status_code == 401

    root_id = _create_comment(author, article_id, "visible root")
    reply_id = _create_comment(voter, article_id, "visible direct reply", reply_id=root_id)
    deep_reply = requests.post(
        url("/api/comments"),
        headers=author.headers,
        json={"articleid": article_id, "content": "deep reply", "replyid": reply_id},
        timeout=TIMEOUT,
    )
    assert deep_reply.status_code == 404

    listing = _list_comments(article_id)
    body = require_status(listing, 200)
    items = body.get("data")
    assert isinstance(items, list) and len(items) == 1
    assert items[0].get("commentid") == root_id
    replies = items[0].get("replies")
    assert isinstance(replies, list) and [item.get("commentid") for item in replies] == [reply_id]

    first_vote = requests.post(
        url(f"/api/comments/{root_id}/vote"),
        headers=voter.headers,
        json={"vote_type": 1},
        timeout=TIMEOUT,
    )
    assert first_vote.status_code == 200
    assert response_json(first_vote).get("code") == 200
    for vote_type in (1, -1):
        duplicate_vote = requests.post(
            url(f"/api/comments/{root_id}/vote"),
            headers=voter.headers,
            json={"vote_type": vote_type},
            timeout=TIMEOUT,
        )
        assert duplicate_vote.status_code == 400

    connection = owned_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT agreecount, opposecount FROM comment WHERE commentid = %s",
                (root_id,),
            )
            assert cursor.fetchone() == (1, 0)
            cursor.execute(
                "SELECT vote_type FROM comment_votes WHERE commentid = %s AND userid = %s",
                (root_id, voter.user_id),
            )
            assert cursor.fetchall() == ((1,),)
        connection.commit()
    finally:
        connection.close()

    public_user = requests.get(url(f"/api/users/{author.user_id}"), timeout=TIMEOUT)
    public_data = require_status(public_user, 200).get("data")
    assert isinstance(public_data, dict)
    assert set(public_data) == {"userid", "username", "nickname", "avatar"}

    self_data = require_status(
        requests.get(url("/api/auth/me"), headers=author.headers, timeout=TIMEOUT), 200
    ).get("data")
    assert isinstance(self_data, dict) and {"qq", "role", "credit"}.issubset(self_data)


def test_comment_list_omits_orphans_cross_article_links_deep_replies_and_hidden_parents():
    author = create_user()
    article_id = create_article(author)
    other_article_id = create_article(author)
    root_id = _create_comment(author, article_id, "public root")
    direct_reply_id = _create_comment(author, article_id, "public direct reply", reply_id=root_id)
    other_article_root_id = _create_comment(author, other_article_id, "other article root")
    cross_article_reply = requests.post(
        url("/api/comments"),
        headers=author.headers,
        json={"articleid": article_id, "content": "cross article reply", "replyid": other_article_root_id},
        timeout=TIMEOUT,
    )
    assert cross_article_reply.status_code == 404

    connection = owned_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO comment (userid, articleid, content, replyid, createtime, updatetime) "
                "VALUES (%s, %s, %s, %s, NOW(), NOW())",
                (author.user_id, article_id, "deep database chain", direct_reply_id),
            )
            cursor.execute(
                "INSERT INTO comment (userid, articleid, content, replyid, createtime, updatetime) "
                "VALUES (%s, %s, %s, %s, NOW(), NOW())",
                (author.user_id, article_id, "orphan comment", 2147483647),
            )
            cursor.execute(
                "INSERT INTO comment (userid, articleid, content, replyid, createtime, updatetime) "
                "VALUES (%s, %s, %s, %s, NOW(), NOW())",
                (author.user_id, article_id, "cross article reply", other_article_root_id),
            )
            cursor.execute(
                "INSERT INTO comment (userid, articleid, content, createtime, updatetime) "
                "VALUES (%s, %s, %s, NOW(), NOW())",
                (author.user_id, article_id, "hidden parent"),
            )
            hidden_parent_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO comment (userid, articleid, content, replyid, createtime, updatetime) "
                "VALUES (%s, %s, %s, %s, NOW(), NOW())",
                (author.user_id, article_id, "reply below hidden parent", hidden_parent_id),
            )
            cursor.execute(
                "INSERT INTO comment (userid, articleid, content, createtime, updatetime) "
                "VALUES (%s, %s, %s, NOW(), NOW())",
                (author.user_id, article_id, "first node in cycle"),
            )
            cycle_first_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO comment (userid, articleid, content, createtime, updatetime) "
                "VALUES (%s, %s, %s, NOW(), NOW())",
                (author.user_id, article_id, "second node in cycle"),
            )
            cycle_second_id = cursor.lastrowid
            cursor.execute(
                "UPDATE comment SET replyid = %s WHERE commentid = %s",
                (cycle_second_id, cycle_first_id),
            )
            assert cursor.rowcount == 1
            cursor.execute(
                "UPDATE comment SET replyid = %s WHERE commentid = %s",
                (cycle_first_id, cycle_second_id),
            )
            assert cursor.rowcount == 1
            cursor.execute(
                "UPDATE comment SET hidden = 1 WHERE commentid = %s",
                (hidden_parent_id,),
            )
        connection.commit()
    finally:
        connection.close()

    response = _list_comments(article_id, headers=author.headers)
    comments = require_status(response, 200).get("data")
    assert isinstance(comments, list) and [item.get("commentid") for item in comments] == [root_id]
    assert [item.get("commentid") for item in comments[0].get("replies", [])] == [direct_reply_id]


def test_vote_requires_a_visible_root_or_direct_parent_and_handles_large_ids():
    author = create_user()
    voter = create_user()
    article_id = create_article(author)
    other_article_id = create_article(author)

    reply_zero = requests.post(
        url("/api/comments"),
        headers=author.headers,
        json={"articleid": article_id, "content": "root from zero replyid", "replyid": 0},
        timeout=TIMEOUT,
    )
    reply_zero_id = require_status(reply_zero, 200).get("data", {}).get("commentid")
    assert isinstance(reply_zero_id, int) and reply_zero_id > 0

    hidden_parent_id = _create_comment(author, article_id, "hidden parent")
    hidden_child_id = _create_comment(author, article_id, "visible child", reply_id=hidden_parent_id)

    cross_parent_id = _create_comment(author, other_article_id, "parent from another article")
    cross_target_id = _create_comment(author, article_id, "cross-linked target")

    deep_root_id = _create_comment(author, article_id, "deep root")
    deep_parent_id = _create_comment(author, article_id, "deep parent", reply_id=deep_root_id)
    deep_target_response = requests.post(
        url("/api/comments"),
        headers=author.headers,
        json={"articleid": article_id, "content": "deep target", "replyid": deep_parent_id},
        timeout=TIMEOUT,
    )
    assert deep_target_response.status_code == 404
    deep_target_id = _insert_corrupt_comment(author.user_id, article_id, "deep target", deep_parent_id)

    cycle_target_id = _create_comment(author, article_id, "cycle target")
    cycle_parent_id = _create_comment(author, article_id, "cycle parent")
    connection = owned_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE comment SET hidden = 1 WHERE commentid = %s", (hidden_parent_id,))
            assert cursor.rowcount == 1
            cursor.execute("UPDATE comment SET replyid = %s WHERE commentid = %s", (cross_parent_id, cross_target_id))
            assert cursor.rowcount == 1
            cursor.execute("UPDATE comment SET replyid = %s WHERE commentid = %s", (cycle_parent_id, cycle_target_id))
            assert cursor.rowcount == 1
            cursor.execute("UPDATE comment SET replyid = %s WHERE commentid = %s", (cycle_target_id, cycle_parent_id))
            assert cursor.rowcount == 1
        connection.commit()
    finally:
        connection.close()

    for target_id in (hidden_child_id, cross_target_id, deep_target_id, cycle_target_id):
        denied = requests.post(
            url(f"/api/comments/{target_id}/vote"),
            headers=voter.headers,
            json={"vote_type": 1},
            timeout=TIMEOUT,
        )
        assert denied.status_code == 404

    valid_vote = requests.post(
        url(f"/api/comments/{reply_zero_id}/vote"),
        headers=voter.headers,
        json={"vote_type": 1},
        timeout=TIMEOUT,
    )
    assert valid_vote.status_code == 200

    connection = owned_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM comment_votes WHERE commentid IN (%s, %s, %s, %s)",
                (hidden_child_id, cross_target_id, deep_target_id, cycle_target_id),
            )
            assert cursor.fetchone() == (0,)
            cursor.execute(
                "SELECT commentid, agreecount, opposecount FROM comment "
                "WHERE commentid IN (%s, %s, %s, %s) ORDER BY commentid",
                (hidden_child_id, cross_target_id, deep_target_id, cycle_target_id),
            )
            assert cursor.fetchall() == tuple(
                (comment_id, 0, 0)
                for comment_id in sorted(
                    (hidden_child_id, cross_target_id, deep_target_id, cycle_target_id)
                )
            )
            cursor.execute(
                "SELECT agreecount, opposecount FROM comment WHERE commentid = %s",
                (reply_zero_id,),
            )
            assert cursor.fetchone() == (1, 0)
        connection.commit()
    finally:
        connection.close()

    uint64_max = 18446744073709551615
    bad_article_id = requests.post(
        url("/api/comments"),
        headers=author.headers,
        json={"articleid": uint64_max, "content": "bad article id"},
        timeout=TIMEOUT,
    )
    assert bad_article_id.status_code == 400
    bad_reply_id = requests.post(
        url("/api/comments"),
        headers=author.headers,
        json={"articleid": article_id, "content": "bad reply id", "replyid": uint64_max},
        timeout=TIMEOUT,
    )
    assert bad_reply_id.status_code == 400


def _insert_corrupt_comment(user_id, article_id, content, reply_id):
    connection = owned_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO comment (userid, articleid, content, replyid, createtime, updatetime) "
                "VALUES (%s, %s, %s, %s, NOW(), NOW())",
                (user_id, article_id, content, reply_id),
            )
            inserted_id = cursor.lastrowid
        connection.commit()
        return inserted_id
    finally:
        connection.close()


def _hide_article(owner_id, article_id):
    connection = owned_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE article SET hidden = 1 WHERE articleid = %s AND userid = %s",
                (article_id, owner_id),
            )
            changed = cursor.rowcount
        connection.commit()
        return changed
    finally:
        connection.close()


def _promote_test_user_to_admin(user_id):
    """Promote only this isolated test's unique user in the run-owned schema."""
    connection = owned_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE users SET role = 'admin' WHERE userid = %s", (user_id,))
            assert cursor.rowcount == 1
        connection.commit()
    finally:
        connection.close()


def test_owner_can_read_and_comment_on_hidden_or_draft_article_only():
    owner = create_user()
    other = create_user()

    visible_article_id = create_article(owner)
    visible_comment_id = _create_comment(owner, visible_article_id, "visible article comment")
    for headers in (None, owner.headers):
        visible = require_status(_list_comments(visible_article_id, headers=headers), 200).get("data")
        assert isinstance(visible, list)
        assert [item.get("commentid") for item in visible] == [visible_comment_id]

    empty_article_id = create_article(owner)
    for headers in (None, owner.headers):
        empty = require_status(_list_comments(empty_article_id, headers=headers), 200).get("data")
        assert empty == []

    for visibility in ("draft", "hidden"):
        article_id = create_article(owner, drafted=1 if visibility == "draft" else 0)
        if visibility == "hidden":
            connection = owned_mysql_connection()
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE article SET hidden = 1 WHERE articleid = %s AND userid = %s",
                        (article_id, owner.user_id),
                    )
                    assert cursor.rowcount == 1
                connection.commit()
            finally:
                connection.close()

        comment_id = _create_comment(owner, article_id, f"owner comment on {visibility}")
        owner_listing = require_status(
            _list_comments(article_id, headers=owner.headers), 200
        ).get("data")
        assert isinstance(owner_listing, list)
        assert any(item.get("commentid") == comment_id for item in owner_listing)

        assert _list_comments(article_id).status_code == 404
        assert _list_comments(article_id, headers=other.headers).status_code == 404
        other_comment = requests.post(
            url("/api/comments"),
            headers=other.headers,
            json={"articleid": article_id, "content": "not allowed"},
            timeout=TIMEOUT,
        )
        assert other_comment.status_code == 404

        owner_vote = requests.post(
            url(f"/api/comments/{comment_id}/vote"),
            headers=owner.headers,
            json={"vote_type": 1},
            timeout=TIMEOUT,
        )
        assert owner_vote.status_code == 200
        other_vote = requests.post(
            url(f"/api/comments/{comment_id}/vote"),
            headers=other.headers,
            json={"vote_type": 1},
            timeout=TIMEOUT,
        )
        assert other_vote.status_code == 404


def test_non_author_admin_cannot_bypass_article_comment_visibility():
    author = create_user()
    admin = create_user()
    _promote_test_user_to_admin(admin.user_id)

    published_article_id = create_article(author)
    published_comment_id = _create_comment(author, published_article_id, "published comment")
    published_listing = _list_comments(published_article_id, headers=admin.headers)
    published_body = require_status(published_listing, 200)
    published_items = published_body.get("data")
    assert isinstance(published_items, list)
    assert [item.get("commentid") for item in published_items] == [published_comment_id]

    private_article_ids = {}
    private_comment_ids = {}
    for visibility in ("hidden", "draft"):
        article_id = create_article(author, drafted=1 if visibility == "draft" else 0)
        if visibility == "hidden":
            assert _hide_article(author.user_id, article_id) == 1
        comment_id = _create_comment(author, article_id, f"owner comment on {visibility}")
        private_article_ids[visibility] = article_id
        private_comment_ids[visibility] = comment_id

        assert _list_comments(article_id, headers=admin.headers).status_code == 404

        admin_root = requests.post(
            url("/api/comments"),
            headers=admin.headers,
            json={"articleid": article_id, "content": f"admin root on {visibility}"},
            timeout=TIMEOUT,
        )
        assert admin_root.status_code == 404

        admin_reply = requests.post(
            url("/api/comments"),
            headers=admin.headers,
            json={
                "articleid": article_id,
                "content": f"admin reply on {visibility}",
                "replyid": comment_id,
            },
            timeout=TIMEOUT,
        )
        assert admin_reply.status_code == 404

        admin_vote = requests.post(
            url(f"/api/comments/{comment_id}/vote"),
            headers=admin.headers,
            json={"vote_type": 1},
            timeout=TIMEOUT,
        )
        assert admin_vote.status_code == 404

    nonexistent_article_id = 2_147_483_647
    connection = owned_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT articleid FROM article WHERE articleid = %s",
                (nonexistent_article_id,),
            )
            assert cursor.fetchone() is None
        connection.commit()
    finally:
        connection.close()
    assert _list_comments(nonexistent_article_id, headers=admin.headers).status_code == 404

    connection = owned_mysql_connection()
    try:
        with connection.cursor() as cursor:
            for visibility in ("hidden", "draft"):
                cursor.execute(
                    "SELECT COUNT(*) FROM comment WHERE articleid = %s",
                    (private_article_ids[visibility],),
                )
                assert cursor.fetchone() == (1,)
                cursor.execute(
                    "SELECT COUNT(*) FROM comment_votes WHERE commentid = %s",
                    (private_comment_ids[visibility],),
                )
                assert cursor.fetchone() == (0,)
        connection.commit()
    finally:
        connection.close()


def test_comment_list_uses_one_visibility_snapshot_while_article_is_hidden():
    owner = create_user()
    article_id = create_article(owner)
    comment_id = _create_comment(owner, article_id, "visible before concurrent hide")
    connection = owned_mysql_connection()
    executor = ThreadPoolExecutor(max_workers=2)
    response_future = None
    hide_future = None
    try:
        with connection.cursor() as cursor:
            # The explicit WRITE table lock blocks the endpoint's read while
            # leaving its SQL visible in the server process list. Inspecting
            # that active SQL proves the permission check and comment rows are
            # read by one joined statement, rather than two separately timed
            # queries. The racing UPDATE may commit before or after that read;
            # both outcomes are legal while the requests overlap.
            cursor.execute("LOCK TABLES comment WRITE")
        response_future = executor.submit(_list_comments, article_id)

        monitor = owned_mysql_connection()
        try:
            deadline = time.monotonic() + 5
            blocked_join_seen = False
            with monitor.cursor() as cursor:
                while time.monotonic() < deadline:
                    cursor.execute(
                        "SELECT PROCESSLIST_INFO, PROCESSLIST_STATE "
                        "FROM performance_schema.threads "
                        "WHERE PROCESSLIST_INFO IS NOT NULL"
                    )
                    for row in cursor.fetchall():
                        statement = " ".join(str(row[0] or "").lower().split())
                        state = str(row[1] or "").lower()
                        if ("from article a" in statement and
                                "left join comment c" in statement and
                                "where a.articleid" in statement and
                                "waiting" in state):
                            blocked_join_seen = True
                            break
                    if blocked_join_seen:
                        break
                    if response_future.done():
                        break
                    time.sleep(0.05)
            assert blocked_join_seen, (
                "GET did not block on the controller's article/comment JOIN while comment was locked"
            )
        finally:
            monitor.close()

        hide_future = executor.submit(_hide_article, owner.user_id, article_id)
    finally:
        try:
            with connection.cursor() as cursor:
                cursor.execute("UNLOCK TABLES")
        except Exception:
            pass
        connection.close()
        for future in (response_future, hide_future):
            if future is None:
                continue
            try:
                future.result(timeout=TIMEOUT)
            except Exception:
                pass
        executor.shutdown(wait=True, cancel_futures=True)

    response = response_future.result(timeout=TIMEOUT)
    assert hide_future is not None
    assert hide_future.result(timeout=TIMEOUT) == 1
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        visible_comments = response_json(response).get("data")
        assert isinstance(visible_comments, list)
        assert [item.get("commentid") for item in visible_comments] == [comment_id]

    # Once the hide is committed, a subsequent anonymous read must be denied.
    after_hide = _list_comments(article_id)
    assert after_hide.status_code == 404

    # The concurrent read used one joined statement. After the hide commit,
    # verify that both persisted states match the expected result.
    connection = owned_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT hidden FROM article WHERE articleid = %s AND userid = %s",
                (article_id, owner.user_id),
            )
            assert cursor.fetchone() == (1,)
            cursor.execute(
                "SELECT COUNT(*) FROM comment WHERE commentid = %s AND articleid = %s",
                (comment_id, article_id),
            )
            assert cursor.fetchone() == (1,)
        connection.commit()
    finally:
        connection.close()
