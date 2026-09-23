#!/bin/bash
#
# 手动更新文章类型缩略图（backend_cpp/resource/thumb/<type>.png）
#
# start_app.sh 只在缩略图缺失时自动生成；文章内容或分类变动后，用这个脚本主动重建。
#
# 用法:
#   bash scripts/update_thumbs.sh              # 全量重建
#   bash scripts/update_thumbs.sh --dry-run    # 只预览关键词，不出图
#   bash scripts/update_thumbs.sh --only 101,102
#
# 选项原样透传给 backend_cpp/scripts/generate_thumbs.py。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
GENERATOR="$PROJECT_DIR/backend_cpp/scripts/generate_thumbs.py"
RESOURCE_DIR="$PROJECT_DIR/backend_cpp/resource"
THUMB_DIR="$RESOURCE_DIR/thumb"
STAGING_DIR="$RESOURCE_DIR/.thumb_staging"
BACKUP_DIR="$RESOURCE_DIR/.thumb_previous"
EXPECTED_SIZE="226x136"

info() { echo "  $1"; }
fail() { echo "" >&2; echo "[错误] $1" >&2; exit 1; }

DRY_RUN=0
for arg in "$@"; do
    if [ "$arg" = "--dry-run" ] || [ "$arg" = "-n" ]; then
        DRY_RUN=1
    fi
done

# 预览模式只走「自检 + 预览」两步
if [ "$DRY_RUN" -eq 1 ]; then TOTAL_STEPS=2; else TOTAL_STEPS=4; fi

echo "========================================"
echo "  文章缩略图更新"
echo "========================================"
echo ""

[ -f "$GENERATOR" ] || fail "找不到生成脚本: $GENERATOR"

PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" > /dev/null 2>&1 || fail "找不到 $PYTHON（可用 PYTHON=/path/to/python3 指定）"

# ---------------------------------------------------------------- 1. 环境自检
echo "[1/$TOTAL_STEPS] 检查运行环境..."

# 依赖必须能在加载生成器之前验证——生成器模块顶层就 import PIL。
PROBE=$("$PYTHON" - "$GENERATOR" <<'PY'
import importlib
import sys

missing = []
for module, package in (("PIL", "Pillow"), ("jieba", "jieba"), ("pymysql", "PyMySQL")):
    try:
        importlib.import_module(module)
    except ImportError:
        missing.append(package)

if missing:
    print("problem=missing-dependency:" + ",".join(missing))
    sys.exit(0)

import importlib.util
import os

spec = importlib.util.spec_from_file_location("gt", sys.argv[1])
gt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gt)

font = next((path for path, _, _ in gt.FONT_STACK if os.path.exists(path)), None)
if not font:
    print("problem=missing-font")
    sys.exit(0)

try:
    categories, articles = gt.fetch_database_context()
except Exception as exc:
    print("problem=database:%s" % exc)
    sys.exit(0)

print("python=%s" % sys.executable)
print("font=%s" % font)
print("categories=%d" % len(categories))
print("articles=%d" % len(articles))
PY
) || fail "环境自检失败"

case "$PROBE" in
    *"problem=missing-dependency:"*)
        PACKAGES="${PROBE##*problem=missing-dependency:}"
        fail "缺少 Python 依赖: $PACKAGES
       安装: $PYTHON -m pip install $PACKAGES"
        ;;
    *"problem=missing-font"*)
        fail "找不到中文字体，缩略图会渲染成方框。安装任一即可:
       Ubuntu: sudo apt-get install -y fonts-noto-cjk
       macOS : 系统自带 Hiragino Sans GB / PingFang 即可"
        ;;
    *"problem=database:"*)
        REASON="${PROBE##*problem=database:}"
        fail "数据库不可用: $REASON
       缩略图未做任何改动。
       请确认 MySQL 已启动，且 backend_cpp/config.local.json（或 config.json）
       的 db_clients 配置正确。"
        ;;
esac

PYTHON_PATH=$(sed -n 's/^python=//p' <<< "$PROBE")
FONT_PATH=$(sed -n 's/^font=//p' <<< "$PROBE")
CATEGORY_COUNT=$(sed -n 's/^categories=//p' <<< "$PROBE")
ARTICLE_COUNT=$(sed -n 's/^articles=//p' <<< "$PROBE")

info "Python  : $PYTHON_PATH"
info "字体    : $FONT_PATH"
info "数据库  : 分类 $CATEGORY_COUNT 个，文章 $ARTICLE_COUNT 篇"

# ---------------------------------------------------------------- 2. 预览模式
echo ""
if [ "$DRY_RUN" -eq 1 ]; then
    echo "[2/$TOTAL_STEPS] 预览关键词（--dry-run，不写文件）..."
    echo ""
    "$PYTHON" "$GENERATOR" "$@"
    echo ""
    echo "预览完成，未生成任何图片。"
    exit 0
fi

# ---------------------------------------------------------------- 3. 生成
echo "[2/$TOTAL_STEPS] 生成缩略图到临时目录..."
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"

# 先把现有缩略图放进临时目录。--only 只重建指定分类，其余分类的图必须保留，
# 否则最后那次原子替换会把它们一并删掉。
if [ -d "$THUMB_DIR" ]; then
    cp "$THUMB_DIR"/*.png "$STAGING_DIR"/ 2> /dev/null || true
fi

# 生成失败时直接退出，原有缩略图原封不动
if ! "$PYTHON" "$GENERATOR" --output-dir "$STAGING_DIR" "$@"; then
    rm -rf "$STAGING_DIR"
    fail "生成失败，原有缩略图保持不变。"
fi

# ---------------------------------------------------------------- 4. 校验
echo ""
echo "[3/$TOTAL_STEPS] 校验生成结果..."

TOTAL=$(find "$STAGING_DIR" -name '*.png' | wc -l | tr -d ' ')
if [ "$TOTAL" -eq 0 ]; then
    rm -rf "$STAGING_DIR"
    fail "临时目录里没有图片，放弃替换。"
fi

BAD_SIZE=$("$PYTHON" - "$STAGING_DIR" "$EXPECTED_SIZE" <<'PY'
import sys
from pathlib import Path

from PIL import Image

expected = tuple(int(part) for part in sys.argv[2].split("x"))
bad = []
for path in sorted(Path(sys.argv[1]).glob("*.png")):
    with Image.open(path) as img:
        if img.size != expected:
            bad.append("%s=%sx%s" % (path.name, img.size[0], img.size[1]))
print(" ".join(bad))
PY
)
if [ -n "$BAD_SIZE" ]; then
    rm -rf "$STAGING_DIR"
    fail "尺寸异常: $BAD_SIZE（应为 $EXPECTED_SIZE）"
fi

info "目录共 $TOTAL 张，尺寸全部为 $EXPECTED_SIZE"

# ---------------------------------------------------------------- 5. 替换
echo ""
echo "[4/$TOTAL_STEPS] 替换缩略图目录..."

# 同一文件系统内 mv 是 rename，切换瞬间完成
rm -rf "$BACKUP_DIR"
if [ -d "$THUMB_DIR" ]; then
    mv "$THUMB_DIR" "$BACKUP_DIR"
fi

if ! mv "$STAGING_DIR" "$THUMB_DIR"; then
    if [ -d "$BACKUP_DIR" ]; then
        mv "$BACKUP_DIR" "$THUMB_DIR"
    fi
    fail "替换失败，已回滚到原有缩略图。"
fi

rm -rf "$BACKUP_DIR"

echo ""
echo "========================================"
echo "  完成：缩略图目录共 $TOTAL 张"
echo "  目录：$THUMB_DIR"
echo "========================================"
echo ""
echo "浏览器可能仍显示旧图（前端按 THUMB_VERSION 缓存）。"
echo "若未更新，重启后端或强制刷新页面。"
