#!/usr/bin/python3
import http.client
import re
import ssl
import sys


HOST = "yunjinqi.top"
TLS = ssl._create_unverified_context()


def request(path, headers=None):
    conn = http.client.HTTPSConnection("127.0.0.1", 443, context=TLS, timeout=3)
    request_headers = {"Host": HOST}
    if headers:
        request_headers.update(headers)
    conn.request("GET", path, headers=request_headers)
    response = conn.getresponse()
    body = response.read()
    result = response.status, {key.lower(): value for key, value in response.getheaders()}, body
    conn.close()
    return result


def require(condition, label, detail=""):
    if not condition:
        raise AssertionError(f"{label}: {detail}")
    print(f"PASS {label}{': ' + detail if detail else ''}")


def cache(headers):
    return headers.get("cache-control", "").lower()


def has_no_cache(headers):
    value = cache(headers)
    return "no-cache" in value and "must-revalidate" in value and "immutable" not in value


def has_immutable(headers):
    value = cache(headers)
    return "public" in value and "immutable" in value and "max-age=31536000" in value


def expected_version(version):
    status, headers, body = request("/")
    index_body = body
    require(status == 200, "GET /", f"HTTP {status}")
    require(headers.get("content-type", "").startswith("text/html"), "index MIME", headers.get("content-type", ""))
    require(has_no_cache(headers), "index cache", cache(headers))
    require(f'data-release="{version}"'.encode() in body, "active index version", version)
    etag = headers.get("etag")
    require(bool(etag), "index ETag", str(etag))
    status_304, headers_304, _ = request("/index.html", {"If-None-Match": etag})
    require(status_304 == 304, "conditional index response", f"HTTP {status_304}")
    require(has_no_cache(headers_304), "304 index cache", cache(headers_304))

    status, headers, body = request(f"/articles/{version}/fixture")
    require(status == 200 and f'data-release="{version}"'.encode() in body, "SPA fallback", f"HTTP {status}")
    require(headers.get("content-type", "").startswith("text/html") and has_no_cache(headers), "SPA cache and MIME", cache(headers))

    status, headers, body = request("/assets/ueditor.config.js")
    require(status == 200, "non-hash asset", f"HTTP {status}")
    require(headers.get("content-type", "").startswith("application/javascript"), "non-hash asset MIME", headers.get("content-type", ""))
    require(has_no_cache(headers), "non-hash asset cache", cache(headers))

    asset = re.search(rb'src="(/assets/[^" ]+\.js)"', body)
    # SPA fallback body is the same index; use the root body when route text is
    # returned through the fallback to keep the assertion independent of HTML.
    if not asset:
        _, _, body = request("/")
        asset = re.search(rb'src="(/assets/[^" ]+\.js)"', body)
    require(bool(asset), "hashed asset reference")
    asset_path = asset.group(1).decode("ascii")
    status, headers, body = request(asset_path)
    require(status == 200 and version.encode() in body, "hashed asset response", f"HTTP {status} {asset_path}")
    require(headers.get("content-type", "").startswith("application/javascript"), "hashed asset MIME", headers.get("content-type", ""))
    require(has_immutable(headers), "hashed asset immutable cache", cache(headers))
    asset_etag = headers.get("etag")
    require(bool(asset_etag), "hashed asset ETag", str(asset_etag))
    status_304, headers_304, _ = request(asset_path, {"If-None-Match": asset_etag})
    require(status_304 == 304, "conditional hashed asset response", f"HTTP {status_304}")
    require(has_immutable(headers_304), "304 hashed asset immutable cache", cache(headers_304))

    css_asset = re.search(rb'href="(/assets/[^" ]+\.css)"', index_body)
    require(bool(css_asset), "hashed CSS entry reference")
    css_path = css_asset.group(1).decode("ascii")
    status, headers, body = request(css_path)
    require(status == 200 and f"fixture-css:{version}".encode() in body, "hashed CSS entry response", f"HTTP {status} {css_path}")
    require(headers.get("content-type", "").startswith("text/css"), "hashed CSS MIME", headers.get("content-type", ""))
    require(has_immutable(headers), "hashed CSS immutable cache", cache(headers))

    missing = "/assets/missing-12345678.js"
    status, headers, body = request(missing)
    require(status == 404, "missing hash asset", f"HTTP {status}")
    require(has_no_cache(headers), "missing hash asset cache", cache(headers))
    require(f'data-release="{version}"'.encode() not in body, "missing asset does not fall back to SPA")

    status, headers, _ = request("/pdf.worker.min.mjs")
    require(status == 200 and "javascript" in headers.get("content-type", "").lower(), "PDF worker MIME", headers.get("content-type", ""))
    require(has_no_cache(headers), "PDF worker cache", cache(headers))

    status, headers, body = request("/api/articles/types")
    require(status == 200 and b'"code": 200' in body, "read-only API proxy", f"HTTP {status}")
    require(headers.get("content-type", "").startswith("application/json"), "API MIME", headers.get("content-type", ""))
    require(has_no_cache(headers), "API cache", cache(headers))

    status, headers, body = request("/api/thumb/fixture-12345678.png")
    require(status == 200 and body.startswith(b"\x89PNG"), "thumbnail proxy beats static regex", f"HTTP {status}")
    require(headers.get("content-type", "").startswith("image/png"), "thumbnail MIME", headers.get("content-type", ""))
    require(has_no_cache(headers), "thumbnail cache", cache(headers))

    for path in ("/api/uploads/smoke.bin", "/uploads/smoke.bin"):
        status, headers, body = request(path)
        require(status == 200, f"upload proxy {path}", f"HTTP {status}")
        require(headers.get("content-type", "").startswith("application/octet-stream"), f"upload MIME {path}", headers.get("content-type", ""))
        require(has_no_cache(headers), f"upload cache {path}", cache(headers))
        require(body.startswith(b"iter21 persistent upload fixture"), f"upload payload {path}")

    status, headers, _ = request("/api/not-found")
    require(status == 404, "API 404 remains an API response", f"HTTP {status}")
    require(has_no_cache(headers), "API 404 cache", cache(headers))
    status, headers, body = request("/api/fail500")
    require(status == 500 and b"fixture upstream error" in body, "upstream 500", f"HTTP {status}")
    require(has_no_cache(headers), "upstream 500 cache", cache(headers))


def main(argv):
    if len(argv) == 3 and argv[1] == "--asset-status":
        status, _, _ = request(argv[2])
        print(status)
        return 0
    if len(argv) != 2:
        print("usage: /usr/bin/python3 http_probe.py VERSION | --asset-status PATH", file=sys.stderr)
        return 2
    expected_version(argv[1])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except Exception as exc:
        print(f"FAIL {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
