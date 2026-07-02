#!/usr/bin/env python3
"""
Generate content-driven category word-cloud thumbnails for article lists.

The frontend uses /api/thumb/<type>.png for article cards. This script keeps
that contract and makes each type image communicate the article topic at a
glance: category name in the center, supporting words segmented from the
category's article headlines/content around it, and a polished high-contrast
background.
"""

import html
import json
import logging
import os
import re
import unicodedata
import warnings
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 226
HEIGHT = 136


# Article types with gradient anchors. IDs must stay compatible with article.type.
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

WORD_SLOTS = [
    (0.23, 0.25, -10, 0.82),
    (0.77, 0.25, 8, 0.78),
    (0.23, 0.72, 9, 0.70),
    (0.77, 0.73, -8, 0.70),
    (0.52, 0.19, 0, 0.62),
    (0.50, 0.82, 0, 0.60),
    (0.15, 0.52, -12, 0.56),
    (0.85, 0.52, 12, 0.56),
    (0.33, 0.88, -4, 0.52),
    (0.67, 0.88, 4, 0.52),
    (0.34, 0.15, 5, 0.50),
    (0.66, 0.15, -5, 0.50),
]


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


def create_gradient(width, height, color1, color2):
    img = Image.new("RGB", (width, height))
    r1, g1, b1 = hex_to_rgb(mix(color1, "#111827", 0.72))
    r2, g2, b2 = hex_to_rgb(mix(color2, "#020617", 0.76))
    for y in range(height):
        ratio = y / max(1, height - 1)
        for x in range(width):
            drift = (x / max(1, width - 1)) * 0.16
            blend = min(1.0, ratio * 0.84 + drift)
            r = int(r1 + (r2 - r1) * blend)
            g = int(g1 + (g2 - g1) * blend)
            b = int(b1 + (b2 - b1) * blend)
            img.putpixel((x, y), (r, g, b))
    return img.convert("RGBA")


def get_font(size, bold=False):
    font_paths = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc" if bold else "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    ]
    for font_path in font_paths:
        if font_path and os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def font_that_fits(draw, text, target_size, max_width, min_size=10, bold=False):
    size = target_size
    while size > min_size:
        font = get_font(size, bold=bold)
        width, _ = text_size(draw, text, font)
        if width <= max_width:
            return font
        size -= 1
    return get_font(min_size, bold=bold)


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


def root_type_id(type_id):
    return type_id if type_id < 100 else type_id // 100


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
    try:
        import pymysql
    except ImportError as exc:
        print(f"[WARN] PyMySQL unavailable; using fallback keywords only: {exc}")
        return {}, []

    db_config = load_db_config()
    if not db_config:
        print("[WARN] MySQL config not found; using fallback keywords only.")
        return {}, []

    try:
        connection = pymysql.connect(
            host=db_config["host"],
            port=db_config["port"],
            user=db_config["user"],
            password=db_config["password"],
            database=db_config["database"],
            charset=db_config["charset"],
            cursorclass=pymysql.cursors.DictCursor,
        )
    except Exception as exc:
        print(f"[WARN] Cannot connect to MySQL; using fallback keywords only: {exc}")
        return {}, []

    categories = {}
    articles = []
    try:
        with connection.cursor() as cursor:
            try:
                cursor.execute("SELECT id, parent_id, name FROM article_category")
                for row in cursor.fetchall():
                    category_id = int(row["id"])
                    categories[category_id] = {
                        "id": category_id,
                        "name": str(row["name"] or "").strip(),
                        "parent_id": int(row["parent_id"]) if row.get("parent_id") is not None else None,
                    }
            except Exception as exc:
                print(f"[WARN] article_category unavailable; using legacy category tree: {exc}")

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

    print(f"[INFO] Loaded {len(categories)} DB categories and {len(articles)} articles for word clouds.")
    return categories, articles


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
        print("[WARN] jieba unavailable; using regex token fallback.")
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
    for match in re.finditer(r"[A-Za-z][A-Za-z0-9+#.-]{1,}|[\u4e00-\u9fff]+", text):
        value = match.group(0)
        if re.fullmatch(r"[\u4e00-\u9fff]+", value) and len(value) > 4:
            tokens.extend(value[i:i + 2] for i in range(0, len(value) - 1, 2))
        else:
            tokens.append(value)
    return tokens


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


def extract_content_keywords(category_name, articles, segmenter, limit=14):
    counter = Counter()
    display = {}

    for article in articles:
        weighted_parts = [
            (article.get("headline", ""), 4),
            (article.get("content", ""), 1),
        ]
        for raw_text, weight in weighted_parts:
            text = clean_article_text(raw_text)
            if not text:
                continue
            tokens = segmenter.lcut(text) if segmenter else fallback_segment(text)
            for token in tokens:
                key, shown = normalize_word(token, category_name)
                if not key:
                    continue
                counter[key] += weight
                display.setdefault(key, shown)

    ranked = sorted(counter.items(), key=lambda item: (-item[1], len(display[item[0]]), display[item[0]]))
    return [display[key] for key, _ in ranked[:limit]]


def build_keywords(type_id, name, catalog, articles, segmenter):
    root_id = root_type_id(type_id)
    parent_id = catalog.get(type_id, {}).get("parent_id") or root_id
    parent_name = catalog.get(parent_id, {}).get("name") or ARTICLE_TYPES.get(root_id, ("文章", "", ""))[0]
    content_keywords = extract_content_keywords(name, articles, segmenter)
    raw = (
        [name]
        + content_keywords
        + TYPE_KEYWORDS.get(type_id, [])
        + ([parent_name] if parent_name != name else [])
        + ROOT_KEYWORDS.get(root_id, [])
    )
    return unique_words(raw)[:14]


def draw_background_details(img, accent):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    accent_rgb = hex_to_rgb(mix(accent, "#ffffff", 0.42))

    draw.rounded_rectangle(
        [8, 8, img.width - 8, img.height - 8],
        radius=14,
        outline=(*accent_rgb, 80),
        width=1,
    )
    draw.ellipse([img.width - 70, -35, img.width + 35, 70], fill=(*accent_rgb, 34))
    draw.ellipse([-38, img.height - 68, 58, img.height + 34], fill=(255, 255, 255, 20))

    for x in range(18, img.width, 26):
        draw.line([(x, 18), (x + 42, img.height - 18)], fill=(255, 255, 255, 12), width=1)
    for y in range(24, img.height, 28):
        draw.line([(14, y), (img.width - 14, y)], fill=(255, 255, 255, 8), width=1)

    return Image.alpha_composite(img, overlay)


def draw_rotated_word(base, center, word, font, fill, angle=0, alpha=180):
    scratch = Image.new("RGBA", (base.width, base.height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(scratch)
    width, height = text_size(draw, word, font)
    x = int(center[0] - width / 2)
    y = int(center[1] - height / 2)
    shadow = (0, 0, 0, max(18, alpha // 5))
    draw.text((x + 1, y + 1), word, font=font, fill=shadow)
    draw.text((x, y), word, font=font, fill=fill[:3] + (alpha,))

    if angle:
        rotated = scratch.rotate(angle, resample=Image.Resampling.BICUBIC)
        base.alpha_composite(rotated)
    else:
        base.alpha_composite(scratch)


def draw_word_cloud(img, name, color1, keywords):
    draw = ImageDraw.Draw(img)
    accent = hex_to_rgb(mix(color1, "#ffffff", 0.32))
    light = hex_to_rgb("#F8FAFC")
    cool = hex_to_rgb(mix(color1, "#E0F2FE", 0.22))
    warm = hex_to_rgb(mix("#FDE68A", color1, 0.2))
    palette = [light, accent, cool, warm]

    # Ambient words first, so the category name owns the visual hierarchy.
    for idx, word in enumerate(keywords[1:]):
        if idx >= len(WORD_SLOTS):
            break
        x_ratio, y_ratio, angle, scale = WORD_SLOTS[idx]
        max_width = 76 if x_ratio in (0.15, 0.85) else 96
        size = int(17 * scale + (3 if idx < 4 else 0))
        font = font_that_fits(draw, word, size, max_width, min_size=10)
        fill = palette[idx % len(palette)]
        draw_rotated_word(
            img,
            (WIDTH * x_ratio, HEIGHT * y_ratio),
            word,
            font,
            fill,
            angle=angle,
            alpha=178 if idx < 6 else 142,
        )

    title_size = 34 if len(name) <= 3 else 29 if len(name) <= 5 else 24 if len(name) <= 8 else 20
    title_font = font_that_fits(draw, name, title_size, WIDTH - 44, min_size=17, bold=True)
    title_w, title_h = text_size(draw, name, title_font)
    title_x = (WIDTH - title_w) // 2
    title_y = (HEIGHT - title_h) // 2 - 4

    pill_pad_x = 13
    pill_pad_y = 8
    draw.rounded_rectangle(
        [
            title_x - pill_pad_x,
            title_y - pill_pad_y,
            title_x + title_w + pill_pad_x,
            title_y + title_h + pill_pad_y,
        ],
        radius=14,
        fill=(2, 6, 23, 96),
        outline=(255, 255, 255, 52),
        width=1,
    )
    draw.text((title_x + 1, title_y + 2), name, font=title_font, fill=(0, 0, 0, 120))
    draw.text((title_x, title_y), name, font=title_font, fill=(255, 255, 255, 245))


def create_thumbnail(type_id, name, color1, color2, keywords, output_path):
    img = create_gradient(WIDTH, HEIGHT, color1, color2)
    img = draw_background_details(img, color1)
    draw_word_cloud(img, name, color1, keywords)
    img.convert("RGB").save(output_path, "PNG", optimize=True)
    print(f"Generated: {output_path} ({', '.join(keywords[:6])})")


def main():
    script_dir = Path(__file__).resolve().parent
    output_dir = (script_dir / ".." / "resource" / "thumb").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    db_categories, articles = fetch_database_context()
    catalog = build_category_catalog(db_categories)
    grouped_articles = group_articles_by_type(articles)
    segmenter = prepare_segmenter(catalog)

    print(f"Generating content-driven word-cloud thumbnails to: {output_dir}")
    for type_id in sorted(catalog):
        category = catalog[type_id]
        selected_articles = articles_for_category(type_id, catalog, grouped_articles)
        keywords = build_keywords(type_id, category["name"], catalog, selected_articles, segmenter)
        create_thumbnail(
            type_id,
            category["name"],
            category["color1"],
            category["color2"],
            keywords,
            output_dir / f"{type_id}.png",
        )

    print(f"\nGenerated {len(catalog)} content-driven word-cloud thumbnails successfully.")


if __name__ == "__main__":
    main()
