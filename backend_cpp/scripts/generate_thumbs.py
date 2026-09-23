#!/usr/bin/env python3
"""
Generate content-driven category thumbnails for article lists.

The frontend uses /api/thumb/<type>.png for article cards. This script keeps
that contract and makes each type image communicate the article topic at a
glance: the category name in large type, a short rule, and a single row of
keywords drawn from the category's article headlines and content.

Keywords come from article content when the category yields enough usable
terms (TF-IDF scored, part-of-speech filtered); otherwise the curated
TYPE_KEYWORDS / ROOT_KEYWORDS lists are used so a thumbnail never ships
garbage words. See build_keywords().

Usage:
    python3 generate_thumbs.py                 # generate every category
    python3 generate_thumbs.py --dry-run       # print keywords, write nothing
    python3 generate_thumbs.py --only 101,102  # regenerate selected categories
    python3 generate_thumbs.py --check         # exit 1 if any image is missing
"""

import argparse
import html
import json
import logging
import math
import os
import re
import sys
import unicodedata
import warnings
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 226
HEIGHT = 136
SUPERSAMPLE = 3          # render large, downscale with LANCZOS for crisp text
KEYWORD_COUNT = 4        # keywords shown in the row under the title
MIN_CONTENT_KEYWORDS = 4 # below this, fall back to curated keywords
# Below this many articles a category has no trustworthy content profile. Raised
# from 5 after comparing both paths: with the current database, categories under
# this line produced mismatched words (区块链与defi -> 期货, 笔记 -> 牛顿), while
# their curated lists read correctly. Lower it once article categorisation is fixed.
MIN_ARTICLES_FOR_CONTENT = 20
VIGNETTE_STRENGTH = 0.28
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "resource" / "thumb"


# Article types with gradient anchors. IDs must stay compatible with article.type.
# Categories present in the database but absent here are picked up at runtime by
# build_category_catalog(), so this table only needs the ones with bespoke colors.
ARTICLE_TYPES = {
    1: ("交易策略", "#7C3AED", "#4C1D95"),
    101: ("CTA策略", "#2563EB", "#1E3A8A"),
    102: ("统计套利", "#0F766E", "#134E4A"),
    103: ("高频交易", "#DC2626", "#7F1D1D"),
    104: ("因子策略", "#D97706", "#78350F"),
    105: ("选股与择时", "#9333EA", "#581C87"),
    106: ("机器学习", "#334155", "#0F172A"),
    107: ("深度学习", "#EA580C", "#7C2D12"),

    2: ("量化框架", "#16A34A", "#14532D"),
    201: ("backtrader", "#2563EB", "#1D4ED8"),
    202: ("wondertrader", "#7C3AED", "#5B21B6"),
    203: ("wtpy", "#0891B2", "#164E63"),
    204: ("pyfolio", "#DC2626", "#7F1D1D"),
    205: ("alphalens", "#D97706", "#78350F"),

    3: ("投资", "#22C55E", "#166534"),
    301: ("股票", "#DC2626", "#991B1B"),
    302: ("期货", "#2563EB", "#1E3A8A"),
    303: ("期权", "#7C3AED", "#4C1D95"),
    304: ("外汇", "#0F766E", "#134E4A"),
    305: ("crypto", "#F59E0B", "#92400E"),
    306: ("黄金", "#EAB308", "#854D0E"),
    307: ("债券", "#334155", "#111827"),

    4: ("理财", "#0D9488", "#134E4A"),
    401: ("基金", "#2563EB", "#1E3A8A"),
    402: ("保险", "#9333EA", "#581C87"),
    403: ("信托", "#DC2626", "#7F1D1D"),
    404: ("银行理财", "#16A34A", "#14532D"),
    405: ("存款", "#D97706", "#78350F"),

    5: ("区块链与defi", "#7C3AED", "#312E81"),
    501: ("去中心化交易所", "#2563EB", "#1E3A8A"),
    502: ("去中心化金融", "#0F766E", "#134E4A"),
    503: ("去中心化借贷", "#DC2626", "#7F1D1D"),
    504: ("去中心化治理", "#D97706", "#78350F"),
    505: ("其他defi", "#9333EA", "#581C87"),
    506: ("区块链", "#334155", "#0F172A"),
    507: ("比特币", "#F7931A", "#9A3412"),
    508: ("以太坊", "#627EEA", "#3730A3"),

    6: ("机器学习", "#334155", "#0F172A"),
    601: ("tensorflow", "#F97316", "#9A3412"),
    602: ("pytorch", "#EA580C", "#7C2D12"),
    603: ("keras", "#DC2626", "#7F1D1D"),
    604: ("scikit-learn", "#F59E0B", "#92400E"),
    605: ("机器学习与交易", "#2563EB", "#1E3A8A"),
    606: ("深度学习与交易", "#7C3AED", "#4C1D95"),

    7: ("编程", "#2563EB", "#1E3A8A"),
    701: ("python", "#3776AB", "#1E3A8A"),
    702: ("c++", "#00599C", "#0F172A"),
    703: ("cython", "#CA8A04", "#713F12"),
    704: ("java", "#EA580C", "#7C2D12"),
    705: ("javascript", "#CA8A04", "#713F12"),
    706: ("swing", "#DC2626", "#7F1D1D"),
    707: ("pybind11", "#0891B2", "#164E63"),

    8: ("笔记", "#16A34A", "#14532D"),
    801: ("幸福", "#22C55E", "#166534"),
    802: ("金融", "#9333EA", "#581C87"),
    803: ("经济", "#2563EB", "#1E3A8A"),
    804: ("哲学", "#7C3AED", "#4C1D95"),
    805: ("历史", "#C2410C", "#7C2D12"),
    806: ("科技", "#0F766E", "#134E4A"),
    807: ("读书笔记", "#334155", "#0F172A"),
    808: ("其他笔记", "#64748B", "#334155"),
    809: ("个人知识库", "#DC2626", "#7F1D1D"),

    9: ("教程", "#EA580C", "#7C2D12"),
    901: ("woniunote入门教程", "#7C3AED", "#4C1D95"),
    902: ("backtrader基础教程", "#2563EB", "#1E3A8A"),
    903: ("airflow入门教程", "#0891B2", "#164E63"),
    904: ("arrow入门教程", "#0F766E", "#134E4A"),
    905: ("量化交易入门教程", "#DC2626", "#7F1D1D"),
    906: ("机器学习入门教程", "#334155", "#0F172A"),
    907: ("ib_tws_api入门教程", "#16A34A", "#14532D"),
}


ROOT_KEYWORDS = {
    1: ["量化交易", "回测", "信号", "风控", "收益", "仓位", "择时"],
    2: ["框架", "回测引擎", "数据源", "组合", "绩效", "接口", "策略开发"],
    3: ["资产配置", "市场", "行情", "估值", "波动", "交易", "收益"],
    4: ["财富管理", "产品", "现金流", "收益率", "风险偏好", "资产"],
    5: ["链上", "合约", "DeFi", "治理", "流动性", "钱包", "协议"],
    6: ["模型", "特征", "训练", "预测", "算法", "数据集", "神经网络"],
    7: ["代码", "工程", "性能", "接口", "调试", "自动化", "架构"],
    8: ["知识库", "复盘", "阅读", "思考", "记录", "方法论", "成长"],
    9: ["教程", "入门", "实践", "案例", "步骤", "配置", "示例"],
}


TYPE_KEYWORDS = {
    101: ["CTA", "趋势跟踪", "突破", "均线", "通道", "止损"],
    102: ["配对交易", "价差", "协整", "均值回归", "套利", "统计检验"],
    103: ["盘口", "微结构", "延迟", "撮合", "订单流", "tick"],
    104: ["因子", "IC", "RankIC", "多因子", "暴露", "中性化"],
    105: ["选股", "择时", "alpha", "轮动", "动量", "估值"],
    106: ["特征工程", "分类", "回归", "交叉验证", "调参", "预测"],
    107: ["神经网络", "LSTM", "Transformer", "Embedding", "训练", "推理"],
    201: ["Cerebro", "Strategy", "Analyzer", "Broker", "Feed", "回测"],
    202: ["事件驱动", "交易接口", "组合", "撮合", "实盘", "回测"],
    203: ["wtpy", "策略引擎", "行情", "CTA", "HFT", "组合"],
    204: ["收益曲线", "回撤", "夏普", "绩效", "风险", "报告"],
    205: ["alpha", "因子分析", "分组收益", "IC", "换手", "衰减"],
    301: ["A股", "财报", "估值", "行业", "成交量", "资金流"],
    302: ["合约", "保证金", "基差", "展期", "主力", "套保"],
    303: ["波动率", "希腊值", "Delta", "Gamma", "组合", "定价"],
    304: ["汇率", "央行", "利差", "美元", "趋势", "宏观"],
    305: ["链上数据", "BTC", "ETH", "波动", "交易所", "资金费率"],
    306: ["避险", "通胀", "美元", "利率", "周期", "商品"],
    307: ["久期", "收益率曲线", "信用", "利率", "票息", "配置"],
    401: ["净值", "指数基金", "主动管理", "定投", "费率", "组合"],
    402: ["保障", "保费", "理赔", "寿险", "重疾", "现金价值"],
    403: ["非标", "风控", "收益", "期限", "底层资产", "兑付"],
    404: ["固收", "现金管理", "风险等级", "净值化", "期限", "收益"],
    405: ["利率", "期限", "安全性", "流动性", "复利", "现金"],
    501: ["AMM", "Swap", "流动性池", "滑点", "LP", "DEX"],
    502: ["协议", "TVL", "收益农场", "治理", "代币", "组合"],
    503: ["抵押", "清算", "借贷池", "利率模型", "健康因子", "杠杆"],
    504: ["DAO", "投票", "提案", "治理代币", "快照", "社区"],
    505: ["跨链", "预言机", "空投", "桥", "收益", "风险"],
    506: ["区块", "节点", "共识", "合约", "Gas", "链上"],
    507: ["BTC", "减半", "矿工", "UTXO", "闪电网络", "储值"],
    508: ["ETH", "EVM", "Layer2", "Gas", "质押", "智能合约"],
    601: ["TensorFlow", "Tensor", "Graph", "GPU", "Keras", "训练"],
    602: ["PyTorch", "Tensor", "Autograd", "Module", "GPU", "训练"],
    603: ["Keras", "Layer", "Model", "Callback", "训练", "快速建模"],
    604: ["sklearn", "Pipeline", "特征", "分类", "回归", "评估"],
    605: ["预测", "特征", "标签", "回测", "模型风险", "信号"],
    606: ["深度模型", "时序", "Transformer", "LSTM", "特征", "交易信号"],
    701: ["Python", "pandas", "numpy", "脚本", "数据分析", "自动化"],
    702: ["C++", "性能", "模板", "并发", "内存", "低延迟"],
    703: ["Cython", "扩展", "编译", "加速", "类型", "Python桥接"],
    704: ["Java", "JVM", "Spring", "并发", "服务端", "工程"],
    705: ["JavaScript", "Vue", "Vite", "前端", "交互", "异步"],
    706: ["Swing", "桌面", "组件", "事件", "布局", "UI"],
    707: ["pybind11", "绑定", "C++扩展", "Python", "接口", "性能"],
    801: ["幸福", "关系", "健康", "心态", "习惯", "长期主义"],
    802: ["金融", "市场", "资产", "风险", "现金流", "估值"],
    803: ["经济", "周期", "通胀", "利率", "增长", "政策"],
    804: ["哲学", "认知", "逻辑", "价值", "思辨", "人生"],
    805: ["历史", "人物", "时代", "制度", "事件", "演化"],
    806: ["科技", "AI", "工程", "产品", "趋势", "创新"],
    807: ["书摘", "观点", "复盘", "认知", "方法", "笔记"],
    808: ["灵感", "碎片", "记录", "整理", "主题", "复盘"],
    809: ["知识管理", "索引", "卡片", "链接", "沉淀", "复用"],
    901: ["WoniuNote", "发布", "配置", "账号", "导航", "入门"],
    902: ["backtrader", "策略", "数据", "回测", "指标", "订单"],
    903: ["Airflow", "DAG", "调度", "任务", "依赖", "工作流"],
    904: ["Arrow", "时间", "日期", "时区", "解析", "格式化"],
    905: ["量化入门", "策略", "数据", "回测", "风控", "实盘"],
    906: ["机器学习", "训练", "特征", "评估", "模型", "实践"],
    907: ["IB API", "TWS", "订单", "行情", "账户", "接口"],
}


STOPWORDS = {
    "一个", "一些", "一种", "一样", "这个", "那个", "这些", "那些", "可以", "进行", "通过", "使用", "如果",
    "因为", "所以", "但是", "不是", "没有", "已经", "还是", "以及", "或者", "并且", "我们", "你们", "他们",
    "自己", "需要", "相关", "比较", "主要", "就是", "对于", "关于", "之后", "之前", "时候", "其中", "可能",
    "非常", "一般", "这里", "那里", "然后", "目前", "问题", "内容", "文章", "分类", "标题", "数据", "分析",
    "方法", "实现", "代码", "系统", "时候", "由于", "比如", "比如说", "以及", "通过", "使用", "进行",
    "如何", "读者", "本文", "作者", "链接", "查看", "点击", "更多", "如下", "上面", "下面", "今天", "这里",
    "的", "了", "和", "是", "在", "对", "与", "或", "及", "也", "都", "而", "被", "把", "从", "到", "为",
    "the", "and", "for", "with", "from", "this", "that", "you", "your", "are", "was", "were", "has", "have",
    "in", "to", "of", "is", "as", "by", "on", "at", "be", "if", "else", "then", "than", "into", "out",
    "add", "lesson", "section", "session", "version", "value", "item", "list", "true", "false", "null",
    "users", "user", "yunjinqi", "documents", "localhost", "backend", "frontend", "resource", "uploads",
    "dbsession", "sessionid", "request", "response", "config", "logger",
    "not", "can", "will", "http", "https", "www", "com", "nbsp", "amp", "quot", "lt", "gt", "article",
    "div", "span", "class", "style", "href", "src", "target", "blank", "img", "ueditor", "woniunote",
}

COLOR_FALLBACKS = [
    ("#2563EB", "#1E3A8A"),
    ("#7C3AED", "#4C1D95"),
    ("#0F766E", "#134E4A"),
    ("#DC2626", "#7F1D1D"),
    ("#D97706", "#78350F"),
    ("#16A34A", "#14532D"),
    ("#334155", "#0F172A"),
    ("#EA580C", "#7C2D12"),
]

# Part-of-speech tags kept when scoring content keywords. Nouns and verbs carry
# topic meaning; particles, adverbs and numerals are noise on a 226x136 image.
ALLOWED_POS = ("n", "vn", "v", "eng", "j", "l", "i")

# (path, regular_face_index, bold_face_index). PingFang ships on macOS but not
# every install, and the Linux entries cover the Ubuntu server.
FONT_STACK = [
    ("/System/Library/Fonts/PingFang.ttc", 2, 4),
    ("/System/Library/Fonts/Hiragino Sans GB.ttc", 0, 2),
    ("/System/Library/Fonts/STHeiti Medium.ttc", 1, 1),
    ("/Library/Fonts/Arial Unicode.ttf", 0, 0),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 2, 4),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 0, 0),
    ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 2, 4),
    ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 0, 0),
    ("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", 0, 0),
]

_CJK_PROBE = "交易策略"


def backend_root():
    return Path(__file__).resolve().parents[1]


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def mix(hex_a, hex_b, weight_a):
    a = hex_to_rgb(hex_a)
    b = hex_to_rgb(hex_b)
    w = max(0.0, min(1.0, weight_a))
    return rgb_to_hex(tuple(a[i] * w + b[i] * (1 - w) for i in range(3)))


# --------------------------------------------------------------------------
# Fonts
# --------------------------------------------------------------------------

_FONT_CACHE = {}


def _renders_cjk(font):
    try:
        mask = font.getmask(_CJK_PROBE)
        return mask.getbbox() is not None
    except Exception:
        return False


def load_font(size, bold=False):
    """Return a CJK-capable font, or raise if none of the candidates work."""
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    for path, regular_index, bold_index in FONT_STACK:
        if not os.path.exists(path):
            continue
        for index in ([bold_index, regular_index] if bold else [regular_index, bold_index]):
            try:
                font = ImageFont.truetype(path, size, index=index)
            except (OSError, ValueError):
                continue
            if _renders_cjk(font):
                _FONT_CACHE[key] = font
                return font

    raise RuntimeError(
        "No CJK-capable font found. Install one of: "
        + ", ".join(path for path, _, _ in FONT_STACK)
    )


def text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def font_that_fits(draw, text, target_size, max_width, min_size=10, bold=False):
    size = target_size
    while size > min_size:
        font = load_font(size, bold=bold)
        width, _ = text_size(draw, text, font)
        if width <= max_width:
            return font
        size -= 1
    return load_font(min_size, bold=bold)


def draw_centered(draw, text, font, cx, cy, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    x = cx - (bbox[2] - bbox[0]) / 2 - bbox[0]
    y = cy - (bbox[3] - bbox[1]) / 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=fill)


# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------

def load_db_config():
    config_paths = [
        backend_root() / "config.local.json",
        backend_root() / "config.json",
    ]
    selected = None
    for path in config_paths:
        if path.exists():
            selected = path
            break
    if not selected:
        return None

    with selected.open("r", encoding="utf-8") as fh:
        config = json.load(fh)

    clients = config.get("db_clients") or []
    mysql_client = next(
        (client for client in clients if client.get("rdbms") == "mysql" or client.get("name") == "mysql"),
        None,
    )
    if not mysql_client:
        return None

    return {
        "host": os.getenv("DB_HOST", mysql_client.get("host", "127.0.0.1")),
        "port": int(os.getenv("DB_PORT", mysql_client.get("port", 3306))),
        "user": os.getenv("DB_USER", mysql_client.get("user", "")),
        "password": os.getenv("DB_PASS", mysql_client.get("passwd", "")),
        "database": os.getenv("DB_NAME", mysql_client.get("dbname", "woniunote")),
        "charset": mysql_client.get("client_encoding", "utf8mb4"),
    }


def fetch_database_context():
    """Return (categories, articles). Raises RuntimeError when the DB is unusable."""
    try:
        import pymysql
    except ImportError as exc:
        raise RuntimeError(f"PyMySQL unavailable: {exc}") from exc

    db_config = load_db_config()
    if not db_config:
        raise RuntimeError("No MySQL config found (config.local.json / config.json)")

    connection = pymysql.connect(
        host=db_config["host"],
        port=db_config["port"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"],
        charset=db_config["charset"],
        cursorclass=pymysql.cursors.DictCursor,
    )

    categories = {}
    articles = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, parent_id, name FROM article_category")
            for row in cursor.fetchall():
                category_id = int(row["id"])
                categories[category_id] = {
                    "id": category_id,
                    "name": str(row["name"] or "").strip(),
                    "parent_id": int(row["parent_id"]) if row.get("parent_id") is not None else None,
                }

            cursor.execute(
                "SELECT type, headline, content FROM article "
                "WHERE hidden = 0 AND drafted = 0"
            )
            for row in cursor.fetchall():
                article_type = row.get("type")
                if article_type is None:
                    continue
                articles.append({
                    "type": int(article_type),
                    "headline": row.get("headline") or "",
                    "content": row.get("content") or "",
                })
    finally:
        connection.close()

    return categories, articles


# --------------------------------------------------------------------------
# Category catalog
# --------------------------------------------------------------------------

def category_colors(type_id, parent_id=None):
    if type_id in ARTICLE_TYPES:
        _, color1, color2 = ARTICLE_TYPES[type_id]
        return color1, color2
    if parent_id in ARTICLE_TYPES:
        _, color1, color2 = ARTICLE_TYPES[parent_id]
        return mix(color1, "#ffffff", 0.86), color2
    palette_index = abs(int(type_id)) % len(COLOR_FALLBACKS)
    return COLOR_FALLBACKS[palette_index]


def build_category_catalog(db_categories):
    """Merge the hardcoded table with whatever the database actually has."""
    catalog = {}
    for type_id, (name, color1, color2) in ARTICLE_TYPES.items():
        catalog[type_id] = {
            "id": type_id,
            "name": name,
            "parent_id": None if type_id < 100 else type_id // 100,
            "color1": color1,
            "color2": color2,
        }

    for category_id, category in db_categories.items():
        color1, color2 = category_colors(category_id, category.get("parent_id"))
        catalog[category_id] = {
            "id": category_id,
            "name": category.get("name") or f"分类{category_id}",
            "parent_id": category.get("parent_id"),
            "color1": color1,
            "color2": color2,
        }
    return catalog


def category_descendants(type_id, catalog):
    children = defaultdict(list)
    for category in catalog.values():
        parent_id = category.get("parent_id")
        if parent_id:
            children[parent_id].append(category["id"])

    result = set()
    stack = [type_id]
    while stack:
        current = stack.pop()
        if current in result:
            continue
        result.add(current)
        stack.extend(children.get(current, []))

    if len(result) == 1 and type_id < 100:
        result.update(
            category_id for category_id in catalog
            if category_id == type_id or category_id // 100 == type_id
        )
    return result


def group_articles_by_type(articles):
    grouped = defaultdict(list)
    for article in articles:
        grouped[article["type"]].append(article)
    return grouped


def articles_for_category(type_id, catalog, grouped_articles):
    article_types = category_descendants(type_id, catalog)
    selected = []
    for article_type in article_types:
        selected.extend(grouped_articles.get(article_type, []))
    return selected


# --------------------------------------------------------------------------
# Keyword extraction
# --------------------------------------------------------------------------

def clean_article_text(text):
    value = html.unescape(str(text or ""))
    value = re.sub(r"(?is)<(script|style|pre|code).*?>.*?</\1>", " ", value)
    value = re.sub(r"(?is)<[^>]+>", " ", value)
    value = re.sub(r"https?://\S+|www\.\S+", " ", value)
    value = re.sub(r"(/[\w .+\-]+){2,}", " ", value)
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"[\u200b-\u200f\ufeff]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def get_segmenter():
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="pkg_resources is deprecated.*")
            import jieba
        jieba.setLogLevel(logging.ERROR)
        return jieba
    except ImportError:
        return None


def prepare_segmenter(catalog):
    segmenter = get_segmenter()
    if not segmenter:
        return None

    for category in catalog.values():
        name = category.get("name")
        if name:
            segmenter.add_word(name, freq=100000)
    for words in list(ROOT_KEYWORDS.values()) + list(TYPE_KEYWORDS.values()):
        for word in words:
            segmenter.add_word(word, freq=50000)
    return segmenter


def fallback_segment(text):
    tokens = []
    for match in re.finditer(r"[A-Za-z][A-Za-z0-9+#.-]{1,}|[一-鿿]+", text):
        value = match.group(0)
        if re.fullmatch(r"[一-鿿]+", value) and len(value) > 4:
            tokens.extend((value[i:i + 2], "n") for i in range(0, len(value) - 1, 2))
        else:
            tokens.append((value, "eng" if value[0].isascii() else "n"))
    return tokens


def tokenize(text, segmenter):
    """Yield (word, pos) pairs, keeping only content-bearing tokens."""
    if segmenter is None:
        for word, pos in fallback_segment(text):
            yield word, pos
        return

    import jieba.posseg as pseg
    for pair in pseg.lcut(text):
        word, flag = pair.word, pair.flag
        if flag.startswith(ALLOWED_POS):
            yield word, flag


def normalize_word(token, category_name):
    word = unicodedata.normalize("NFKC", str(token or "")).strip()
    word = word.strip(" \t\r\n,.;:!?()[]{}<>\"'`~，。；：！？（）【】《》、|/\\")
    if not word:
        return None, None

    ascii_word = re.fullmatch(r"[A-Za-z][A-Za-z0-9+#.-]*", word)
    normalized = word.lower() if ascii_word else word
    if normalized in STOPWORDS or word in STOPWORDS:
        return None, None
    if word == category_name or normalized == category_name.lower():
        return None, None
    if re.fullmatch(r"\d+(\.\d+)?%?", normalized):
        return None, None
    if len(word) < 2 and not ascii_word:
        return None, None
    if len(word) == 1 and ascii_word:
        return None, None
    if re.search(r"[=*&^%$#@]", word) and not ascii_word:
        return None, None
    return normalized, word


def collect_category_terms(category_name, articles, segmenter):
    """Per-category term frequencies plus the set of terms used by this category."""
    frequencies = Counter()
    document_counts = Counter()
    display = {}

    for article in articles:
        seen_in_article = set()
        for raw_text, weight in ((article.get("headline", ""), 4), (article.get("content", ""), 1)):
            text = clean_article_text(raw_text)
            if not text:
                continue
            for token, _pos in tokenize(text, segmenter):
                key, shown = normalize_word(token, category_name)
                if not key:
                    continue
                frequencies[key] += weight
                display.setdefault(key, shown)
                seen_in_article.add(key)
        for key in seen_in_article:
            document_counts[key] += 1

    return frequencies, document_counts, display


def score_category_terms(frequencies, document_counts, display, article_count):
    """Rank by within-category frequency, dropping one-off terms.

    TF-IDF was tried here and made things worse, not better: on a corpus where
    most categories hold a handful of articles, the idf term *rewards* the
    loneliest words (a term appearing in one category gets the highest weight),
    which is exactly the noise we want gone. Representative terms beat
    distinctive ones for a category label.
    """
    min_document_count = 2 if article_count >= MIN_ARTICLES_FOR_CONTENT else 1
    scored = []

    for term, frequency in frequencies.items():
        if document_counts[term] < min_document_count:
            continue
        scored.append((frequency, display[term]))

    scored.sort(key=lambda item: (-item[0], len(item[1]), item[1]))
    return [shown for _freq, shown in scored]


def build_keywords(type_id, name, catalog, articles, segmenter):
    """Return (keywords, source). Content keywords win when they can be trusted."""
    root_id = type_id if type_id < 100 else type_id // 100

    if len(articles) >= MIN_ARTICLES_FOR_CONTENT:
        frequencies, document_counts, display = collect_category_terms(name, articles, segmenter)
        content = score_category_terms(frequencies, document_counts, display, len(articles))
        if len(content) >= MIN_CONTENT_KEYWORDS:
            return content[:KEYWORD_COUNT], "content"

    parent_id = catalog.get(type_id, {}).get("parent_id") or root_id
    parent_name = catalog.get(parent_id, {}).get("name") or ARTICLE_TYPES.get(root_id, ("文章", "", ""))[0]
    curated = (
        TYPE_KEYWORDS.get(type_id, [])
        + ([parent_name] if parent_name != name else [])
        + ROOT_KEYWORDS.get(root_id, [])
    )
    keywords = [word for word in unique_words(curated) if word != name][:KEYWORD_COUNT]
    return keywords, "curated"


def unique_words(words):
    seen = set()
    result = []
    for word in words:
        normalized = str(word).strip()
        if not normalized or normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        result.append(normalized)
    return result


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def create_gradient(width, height, color1, color2):
    """Diagonal gradient between the two anchor colors, kept vivid.

    Rendered small and scaled up: a per-pixel loop at full size is slow and the
    result is identical after BICUBIC upscaling.
    """
    small_w = max(8, width // 8)
    small_h = max(8, height // 8)
    start = hex_to_rgb(color1)
    end = hex_to_rgb(color2)

    small = Image.new("RGB", (small_w, small_h))
    pixels = small.load()
    for y in range(small_h):
        for x in range(small_w):
            t = 0.62 * (y / max(1, small_h - 1)) + 0.38 * (x / max(1, small_w - 1))
            t = max(0.0, min(1.0, t))
            pixels[x, y] = tuple(
                int(start[i] + (end[i] - start[i]) * t) for i in range(3)
            )

    return small.resize((width, height), Image.BICUBIC).convert("RGBA")


def apply_vignette(img, strength=VIGNETTE_STRENGTH):
    """Darken the edges slightly so the centered type reads as the focal point."""
    width, height = img.size
    small_w = max(8, width // 16)
    small_h = max(8, height // 16)

    mask = Image.new("L", (small_w, small_h))
    pixels = mask.load()
    for y in range(small_h):
        for x in range(small_w):
            nx = (x / max(1, small_w - 1)) * 2 - 1
            ny = (y / max(1, small_h - 1)) * 2 - 1
            distance = min(1.0, math.hypot(nx, ny) / 1.4142)
            pixels[x, y] = int(255 * (1 - strength * distance ** 1.6))

    mask = mask.resize((width, height), Image.BICUBIC)
    dark = Image.new("RGBA", img.size, (0, 0, 0, 255))
    return Image.composite(img, dark, mask)


def fit_keyword_row(draw, keywords, max_width, scale):
    """Fit the keyword row inside max_width.

    Long English terms ("Cerebro Strategy Analyzer Broker") overflow the canvas
    if drawn naively. Prefer the full font size and drop trailing words before
    shrinking the type, so what remains stays readable.

    Returns (font, words, gap, widths); font is None when nothing fits.
    """
    target = int(12.5 * scale)
    floor = int(10.5 * scale)

    for size in range(target, floor - 1, -1):
        font = load_font(size)
        gap = max(6 * scale, int(size * 1.15))
        for count in range(len(keywords), 0, -1):
            words = keywords[:count]
            widths = [text_size(draw, word, font)[0] for word in words]
            if sum(widths) + gap * (len(words) - 1) <= max_width:
                return font, words, gap, widths
    return None, [], 0, []


def title_font_size(name):
    length = len(name)
    if length <= 3:
        return 54
    if length <= 5:
        return 46
    if length <= 8:
        return 33
    return 26


def draw_thumbnail(name, color1, color2, keywords):
    width = WIDTH * SUPERSAMPLE
    height = HEIGHT * SUPERSAMPLE
    scale = SUPERSAMPLE

    img = create_gradient(width, height, color1, color2)
    img = apply_vignette(img)
    draw = ImageDraw.Draw(img)

    # Title
    title_font = font_that_fits(
        draw, name, title_font_size(name) * scale, width - 30 * scale, min_size=17 * scale, bold=True
    )
    draw_centered(draw, name, title_font, width / 2, height * 0.36, (255, 255, 255, 252))

    # Short rule under the title
    rule_y = height * 0.585
    draw.line(
        [(width / 2 - 17 * scale, rule_y), (width / 2 + 17 * scale, rule_y)],
        fill=(255, 255, 255, 92),
        width=scale,
    )

    # Keyword row, evenly spaced, never rotated or overlapped
    if keywords:
        keyword_font, words, gap, widths = fit_keyword_row(
            draw, keywords, width - 24 * scale, scale
        )
        if keyword_font is not None:
            total = sum(widths) + gap * (len(words) - 1)
            x = width / 2 - total / 2
            for word, word_width in zip(words, widths):
                bbox = draw.textbbox((0, 0), word, font=keyword_font)
                draw.text(
                    (x - bbox[0], height * 0.72 - (bbox[3] - bbox[1]) / 2 - bbox[1]),
                    word,
                    font=keyword_font,
                    fill=(255, 255, 255, 205),
                )
                x += word_width + gap

    return img.convert("RGB").resize((WIDTH, HEIGHT), Image.LANCZOS)


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------

def parse_type_filter(raw):
    if not raw:
        return None
    selected = set()
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if not chunk.isdigit():
            raise ValueError(f"--only expects comma-separated numeric ids, got: {chunk!r}")
        selected.add(int(chunk))
    return selected or None


def build_plan(catalog, grouped_articles, segmenter, selected=None):
    """Compute keywords for every selected category."""
    targets = sorted(tid for tid in catalog if selected is None or tid in selected)

    plan = []
    for type_id in targets:
        category = catalog[type_id]
        articles = articles_for_category(type_id, catalog, grouped_articles)
        keywords, source = build_keywords(
            type_id, category["name"], catalog, articles, segmenter
        )
        plan.append({
            "type_id": type_id,
            "name": category["name"],
            "color1": category["color1"],
            "color2": category["color2"],
            "keywords": keywords,
            "source": source,
            "article_count": len(articles),
        })
    return plan


def missing_thumbnails(output_dir):
    """Type ids the database knows about that have no PNG on disk."""
    try:
        db_categories, _articles = fetch_database_context()
    except Exception:
        return None

    catalog = build_category_catalog(db_categories)
    return [
        type_id for type_id in sorted(catalog)
        if not (output_dir / f"{type_id}.png").exists()
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Generate content-driven category thumbnails",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 generate_thumbs.py                 # regenerate every category\n"
            "  python3 generate_thumbs.py --dry-run       # preview keywords only\n"
            "  python3 generate_thumbs.py --only 101,102  # selected categories\n"
            "  python3 generate_thumbs.py --check         # exit 1 if any image is missing\n"
        ),
    )
    parser.add_argument("--only", "-o", metavar="IDS",
                        help="comma-separated category ids to regenerate")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="print the keywords that would be used, write no images")
    parser.add_argument("--output-dir", metavar="DIR", type=Path, default=None,
                        help=f"output directory (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--check", action="store_true",
                        help="exit 0 when every category has an image, 1 otherwise")
    args = parser.parse_args()

    output_dir = (args.output_dir or DEFAULT_OUTPUT_DIR).resolve()

    if args.check:
        missing = missing_thumbnails(output_dir)
        if missing is None:
            # Database unreachable: fall back to "is there anything at all?"
            have_any = output_dir.is_dir() and any(output_dir.glob("*.png"))
            print("Cannot reach database; thumbnails present" if have_any
                  else "Cannot reach database and no thumbnails on disk")
            return 0 if have_any else 1
        if missing:
            print(f"Missing {len(missing)} thumbnails: {', '.join(str(i) for i in missing[:10])}"
                  + (" ..." if len(missing) > 10 else ""))
            return 1
        print("All thumbnails present")
        return 0

    try:
        selected = parse_type_filter(args.only)
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    try:
        db_categories, articles = fetch_database_context()
    except Exception as exc:
        print(f"[ERROR] Database unavailable: {exc}", file=sys.stderr)
        print("        Thumbnails were NOT regenerated.", file=sys.stderr)
        return 1

    catalog = build_category_catalog(db_categories)
    grouped_articles = group_articles_by_type(articles)
    segmenter = prepare_segmenter(catalog)
    if segmenter is None:
        print("[WARN] jieba unavailable; using regex token fallback.", file=sys.stderr)

    plan = build_plan(catalog, grouped_articles, segmenter, selected)
    if not plan:
        print("[ERROR] No matching categories to generate.", file=sys.stderr)
        return 1

    if args.dry_run:
        for item in plan:
            source = "内容" if item["source"] == "content" else "精选"
            print(f"[{item['type_id']:>3}] {item['name']:<18} {item['article_count']:>3}篇 {source}  "
                  + " ".join(item["keywords"]))
        content_count = sum(1 for item in plan if item["source"] == "content")
        print(f"\n共 {len(plan)} 个分类：内容词 {content_count} 个，精选词 {len(plan) - content_count} 个")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    for item in plan:
        image = draw_thumbnail(item["name"], item["color1"], item["color2"], item["keywords"])
        destination = output_dir / f"{item['type_id']}.png"
        image.save(destination, "PNG", optimize=True)
        print(f"Generated: {destination} ({', '.join(item['keywords'])})")

    content_count = sum(1 for item in plan if item["source"] == "content")
    print(f"\nGenerated {len(plan)} thumbnails "
          f"(content keywords: {content_count}, curated keywords: {len(plan) - content_count}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
