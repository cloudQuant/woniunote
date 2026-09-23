#!/usr/bin/env bash

# 验证线上缩略图端点真的返回图片。
#
# 背景：前端请求 /api/thumb/<type>.png。nginx 里有一条正则 location
#   location ~* \.(js|mjs|css|png|jpg|...)$
# 正则 location 的优先级高于无 ^~ 的前缀 location /api，所以 .png 请求会被
# 当成静态文件去 dist 目录找，返回 404，压根到不了 C++ 后端。这个脚本就是
# 用来抓这种回归的。
#
# 用法:
#   bash scripts/tests/test_thumb_endpoints.sh                    # 默认打 www.yunjinqi.top
#   bash scripts/tests/test_thumb_endpoints.sh https://example.com
#
# 注意：生产站证书已过期，这里用 -k 跳过校验；证书续期后可以去掉。

set -euo pipefail

BASE_URL="${1:-https://www.yunjinqi.top}"
# 取几个不同父分类下的类型，确保不是同一张回退图
IDS=(1 101 301 901)
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/woniunote-thumb-test.XXXXXX")"

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

FAILURES=0

pass() { printf '  ok   %s\n' "$1"; }
fail() { printf '  FAIL %s\n' "$1" >&2; FAILURES=$((FAILURES + 1)); }

echo "缩略图端点检查: $BASE_URL"
echo ""

declare -a HASHES=()

for id in "${IDS[@]}"; do
    url="$BASE_URL/api/thumb/${id}.png"
    body="$TMP_DIR/${id}.png"

    meta=$(curl -sk -m 30 -o "$body" -w '%{http_code} %{content_type}' "$url" || echo "000 -")

    status="${meta%% *}"
    content_type="${meta#* }"

    if [ "$status" != "200" ]; then
        fail "/api/thumb/${id}.png -> HTTP ${status}（应 200）"
        continue
    fi

    case "$content_type" in
        image/png*) ;;
        *)
            fail "/api/thumb/${id}.png -> Content-Type ${content_type}（应 image/png）"
            continue
            ;;
    esac

    # 必须是真的 PNG，且尺寸符合前端卡片布局
    size=$(python3 - "$body" <<'PY' 2>/dev/null || echo "invalid"
from PIL import Image
import sys
try:
    with Image.open(sys.argv[1]) as img:
        print("%dx%d" % img.size)
except Exception:
    print("invalid")
PY
)
    if [ "$size" != "226x136" ]; then
        fail "/api/thumb/${id}.png -> 不是有效 PNG 或尺寸为 ${size}（应 226x136）"
        continue
    fi

    pass "/api/thumb/${id}.png -> 200 image/png ${size}"
    HASHES+=("$(shasum -a 256 "$body" | cut -d' ' -f1)")
done

# 所有分类都返回同一张图 = 后端走了 1.png 回退，说明路径没匹配上真实文件
if [ "${#HASHES[@]}" -gt 1 ]; then
    unique=$(printf '%s\n' "${HASHES[@]}" | sort -u | wc -l | tr -d ' ')
    if [ "$unique" -eq 1 ]; then
        fail "所有分类返回同一张图（后端回退到 1.png，说明文件名没匹配上）"
    else
        pass "各分类图片内容不同（$unique 种）"
    fi
fi

echo ""
if [ "$FAILURES" -eq 0 ]; then
    echo "全部通过。"
    exit 0
fi

echo "$FAILURES 项失败。"
echo ""
echo "若 /api/thumb/<id>.png 返回 404 且响应体是 nginx 的 HTML 错误页，"
echo "说明 nginx 把 .png 请求截走了。检查 configs/woniunote_nginx_prod.conf："
echo "  location /api   -> 应写成  location ^~ /api"
echo "（^~ 前缀匹配会跳过正则 location，请求才能转发到后端）"
exit 1
