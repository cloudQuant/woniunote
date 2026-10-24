"""Real HTTP contracts for article thumbnail validation and persistence."""

from __future__ import annotations

import struct
import uuid
import zlib

import pytest
import requests

from iter21_support import (
    TIMEOUT,
    login,
    owned_mysql_connection,
    register_user,
    response_json,
    url,
)


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    chunk = kind + payload
    return (
        struct.pack(">I", len(payload))
        + chunk
        + struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)
    )


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
    + _png_chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00\xff"))
    + _png_chunk(b"IEND", b"")
)


@pytest.fixture
def owned_database():
    connection = owned_mysql_connection()
    connection.autocommit(True)
    try:
        yield connection
    finally:
        connection.close()


def _database_scalar(connection, sql: str, parameters: tuple[object, ...]) -> object:
    with connection.cursor() as cursor:
        cursor.execute(sql, parameters)
        row = cursor.fetchone()
        assert row is not None, "isolated MySQL query returned no row"
        return row[0]


def _article_count(connection, user_id: int) -> int:
    return int(
        _database_scalar(
            connection,
            "SELECT COUNT(*) FROM article WHERE userid = %s",
            (user_id,),
        )
    )


def _stored_thumbnail(connection, user_id: int, article_id: int) -> str:
    value = _database_scalar(
        connection,
        "SELECT thumbnail FROM article WHERE userid = %s AND articleid = %s",
        (user_id, article_id),
    )
    assert isinstance(value, str), "owned article thumbnail was not stored as a string"
    return value


def _upload_thumbnail(user, original_name: str) -> str:
    response = requests.post(
        url("/api/upload/image"),
        headers=user.headers,
        files={"file": (original_name, PNG_BYTES, "image/png")},
        timeout=TIMEOUT,
    )
    assert response.status_code == 200, "thumbnail upload did not return HTTP 200"
    body = response_json(response)
    assert body.get("code") == 200, "thumbnail upload returned an unsuccessful response"
    data = body.get("data")
    assert isinstance(data, dict), "thumbnail upload omitted its response data"
    path = data.get("url")
    assert isinstance(path, str) and path.startswith("/uploads/"), (
        "thumbnail upload did not return a same-origin uploads path"
    )
    try:
        encoded_path = path.encode("ascii")
    except UnicodeEncodeError:
        pytest.fail("thumbnail upload returned a non-ASCII path")
    assert len(encoded_path) <= 512
    assert ".." not in path and "\\" not in path and "%" not in path
    return path


def _create_article(user, headline: str, **fields: object) -> dict:
    payload: dict[str, object] = {
        "headline": headline,
        "type": 1,
        "content": "<p>iteration 21 thumbnail integration</p>",
        "credit": 0,
        "drafted": 1,
    }
    payload.update(fields)
    response = requests.post(
        url("/api/articles"),
        headers=user.headers,
        json=payload,
        timeout=TIMEOUT,
    )
    assert response.status_code == 200, "article creation did not return HTTP 200"
    body = response_json(response)
    data = body.get("data")
    assert body.get("code") == 200 and isinstance(data, dict), (
        "article creation returned an unsuccessful response"
    )
    return data


def _article_detail(user, article_id: int) -> dict:
    response = requests.get(
        url(f"/api/articles/{article_id}"),
        headers=user.headers,
        timeout=TIMEOUT,
    )
    assert response.status_code == 200, "owned article detail did not return HTTP 200"
    body = response_json(response)
    data = body.get("data")
    assert body.get("code") == 200 and isinstance(data, dict), (
        "article detail returned an unsuccessful response"
    )
    return data


def _update_article(user, article_id: int, payload: dict[str, object]) -> requests.Response:
    return requests.put(
        url(f"/api/articles/{article_id}"),
        headers=user.headers,
        json=payload,
        timeout=TIMEOUT,
    )


def _listed_thumbnail(user, article_id: int) -> object:
    response = requests.get(
        url("/api/articles/my"),
        headers=user.headers,
        timeout=TIMEOUT,
    )
    assert response.status_code == 200, "own-article list did not return HTTP 200"
    body = response_json(response)
    articles = body.get("data")
    assert body.get("code") == 200 and isinstance(articles, list), (
        "own-article list returned an unsuccessful response"
    )
    for article in articles:
        if isinstance(article, dict) and article.get("articleid") == article_id:
            return article.get("thumbnail")
    pytest.fail("created article was missing from the author's list")


def test_article_thumbnail_create_read_update_and_validation(user, owned_database):
    before_invalid_creates = _article_count(owned_database, user.user_id)
    invalid_values: list[object] = [
        None,
        17,
        {"url": "/uploads/images/cover.png"},
        "a" * 509 + ".png",
    ]
    for value in invalid_values:
        response = requests.post(
            url("/api/articles"),
            headers=user.headers,
            json={
                "headline": f"Invalid thumbnail {uuid.uuid4().hex[:12]}",
                "type": 1,
                "drafted": 1,
                "thumbnail": value,
            },
            timeout=TIMEOUT,
        )
        assert response.status_code == 400, "invalid article thumbnail was not rejected"
    assert _article_count(owned_database, user.user_id) == before_invalid_creates, (
        "invalid article thumbnail created a database row"
    )

    first_path = _upload_thumbnail(user, f"iter21-cover-{uuid.uuid4().hex[:8]}.png")
    second_path = _upload_thumbnail(user, f"iter21-cover-{uuid.uuid4().hex[:8]}.png")
    article = _create_article(
        user,
        f"Thumbnail round trip {uuid.uuid4().hex[:12]}",
        thumbnail=first_path,
    )
    article_id = article.get("articleid")
    assert isinstance(article_id, int) and article_id > 0
    assert article.get("thumbnail") == first_path
    assert _stored_thumbnail(owned_database, user.user_id, article_id) == first_path

    assert _article_detail(user, article_id).get("thumbnail") == first_path
    assert _listed_thumbnail(user, article_id) == first_path

    headline = article["headline"]
    content = article["content"]
    edit_fields: dict[str, object] = {
        "headline": headline,
        "content": content,
        "type": 1,
        "drafted": 1,
    }
    response = _update_article(
        user,
        article_id,
        {**edit_fields, "thumbnail": second_path},
    )
    assert response.status_code == 200, "owner could not replace the article thumbnail"
    assert _article_detail(user, article_id).get("thumbnail") == second_path
    assert _listed_thumbnail(user, article_id) == second_path
    assert _stored_thumbnail(owned_database, user.user_id, article_id) == second_path

    response = _update_article(user, article_id, edit_fields)
    assert response.status_code == 200, "owner could not update without a thumbnail field"
    assert _article_detail(user, article_id).get("thumbnail") == second_path
    assert _stored_thumbnail(owned_database, user.user_id, article_id) == second_path

    response = _update_article(
        user,
        article_id,
        {**edit_fields, "thumbnail": "/api/thumb/legacy-cover.png"},
    )
    assert response.status_code == 200, "legacy API thumbnail path was not accepted"
    assert _stored_thumbnail(owned_database, user.user_id, article_id) == "legacy-cover.png"
    assert _article_detail(user, article_id).get("thumbnail") == "legacy-cover.png"

    invalid_updates: list[object] = [
        None,
        False,
        "a" * 509 + ".png",
        "/uploads/../cover.png",
        "https://cdn.example/cover.png",
    ]
    for value in invalid_updates:
        response = _update_article(user, article_id, {"thumbnail": value})
        assert response.status_code == 400, "invalid thumbnail update was not rejected"
        assert _stored_thumbnail(owned_database, user.user_id, article_id) == "legacy-cover.png", (
            "invalid thumbnail update changed the stored value"
        )

    another_user = login(register_user())
    response = _update_article(
        another_user,
        article_id,
        {"type": 1, "thumbnail": second_path},
    )
    assert response.status_code == 403, "non-owner was allowed to change an article thumbnail"
    assert _stored_thumbnail(owned_database, user.user_id, article_id) == "legacy-cover.png"

    response = _update_article(user, article_id, {**edit_fields, "thumbnail": ""})
    assert response.status_code == 200, "empty thumbnail did not restore the type default"
    assert _stored_thumbnail(owned_database, user.user_id, article_id) == ""
    assert _article_detail(user, article_id).get("thumbnail") == "1.png"
    assert _listed_thumbnail(user, article_id) == "1.png"

    response = _update_article(user, article_id, {**edit_fields, "type": 2})
    assert response.status_code == 200, "owner could not change the article type"
    assert _stored_thumbnail(owned_database, user.user_id, article_id) == "", (
        "omitting thumbnail during update overwrote the stored empty override"
    )
    assert _article_detail(user, article_id).get("thumbnail") == "2.png", (
        "empty thumbnail did not follow the article's new type default"
    )
    assert _listed_thumbnail(user, article_id) == "2.png"

    omitted = _create_article(user, f"Omitted thumbnail {uuid.uuid4().hex[:12]}")
    omitted_id = omitted.get("articleid")
    assert isinstance(omitted_id, int) and omitted_id > 0
    assert _stored_thumbnail(owned_database, user.user_id, omitted_id) == ""
    assert _article_detail(user, omitted_id).get("thumbnail") == "1.png"
