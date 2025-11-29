"""
缩略图资源路由
支持自动生成和返回文章类型缩略图
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
import logging

from app.core.thumbnail import create_thumb_png
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# 文章类型映射 (与 articles.py 中的 ARTICLE_TYPES 保持一致)
ARTICLE_TYPE_NAMES = {
    1: '交易策略',
    101: 'CTA策略', 102: '统计套利', 103: '高频交易', 104: '因子策略',
    105: '选股与择时', 106: '机器学习', 107: '深度学习',
    2: '量化框架',
    201: 'backtrader', 202: 'wondertrader', 203: 'wtpy',
    204: 'pyfolio', 205: 'alphalens',
    3: '投资',
    301: '股票', 302: '期货', 303: '期权', 304: '外汇',
    305: 'crypto', 306: '黄金', 307: '债券',
    4: '理财',
    401: '基金', 402: '保险', 403: '信托', 404: '银行理财', 405: '存款',
    5: '区块链与defi',
    501: '去中心化交易所', 502: '去中心化金融', 503: '去中心化借贷',
    504: '去中心化治理', 505: '其他defi', 506: '区块链',
    507: '比特币', 508: '以太坊',
    6: '机器学习',
    601: 'tensorflow', 602: 'pytorch', 603: 'keras',
    604: 'scikit-learn', 605: '机器学习与交易', 606: '深度学习与交易',
    7: '编程',
    701: 'python', 702: 'c++', 703: 'cython', 704: 'java',
    705: 'javascript', 706: 'swing', 707: 'pybind11',
    8: '笔记',
    801: '幸福', 802: '金融', 803: '经济', 804: '哲学', 805: '历史',
    806: '科技', 807: '读书笔记', 808: '其他笔记', 809: '个人知识库',
    9: '教程',
    901: 'woniunote入门', 902: 'backtrader教程', 903: 'airflow教程',
    904: 'arrow教程', 905: '量化交易入门', 906: '机器学习入门', 907: 'ib_tws_api教程'
}


def get_thumb_root() -> str:
    """获取缩略图根目录，支持多种路径查找策略"""
    # 1. 如果配置了 RESOURCE_DIR，优先使用
    if settings.RESOURCE_DIR:
        thumb_dir = os.path.join(settings.RESOURCE_DIR, "thumb")
        if os.path.exists(thumb_dir):
            return thumb_dir
    
    # 2. 尝试从当前文件位置推断项目根目录
    # backend/app/api/thumb.py -> backend -> 项目根目录 -> woniunote/resource/thumb
    current_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    project_root = os.path.dirname(backend_dir)
    
    possible_paths = [
        os.path.join(project_root, "woniunote", "resource", "thumb"),
        os.path.join(backend_dir, "..", "woniunote", "resource", "thumb"),
        os.path.join(os.getcwd(), "woniunote", "resource", "thumb"),
        os.path.join(os.getcwd(), "..", "woniunote", "resource", "thumb"),
    ]
    
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            logger.info(f"Found thumb directory at: {abs_path}")
            return abs_path
    
    # 3. 如果都不存在，返回第一个路径并尝试创建
    default_path = os.path.abspath(possible_paths[0])
    logger.warning(f"Thumb directory not found, will create at: {default_path}")
    return default_path


def get_type_text(type_id: int) -> str:
    """根据类型ID获取显示文字"""
    # 直接查找完整类型ID
    if type_id in ARTICLE_TYPE_NAMES:
        return ARTICLE_TYPE_NAMES[type_id]
    
    # 尝试查找父类型 (子类型 >= 100, 父类型 = 子类型 // 100)
    if type_id >= 100:
        parent_id = type_id // 100
        if parent_id in ARTICLE_TYPE_NAMES:
            return ARTICLE_TYPE_NAMES[parent_id]
    
    return f"类型{type_id}"


@router.get("/thumb/{filename:path}")
async def thumb_resources(filename: str):
    """获取缩略图资源，支持自动生成"""
    thumb_root = get_thumb_root()
    file_path = os.path.join(thumb_root, filename)

    # 已存在的文件直接返回
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="image/png")

    # 不存在则尝试自动创建目录
    try:
        os.makedirs(thumb_root, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create thumb directory: {e}")
        raise HTTPException(status_code=500, detail="Failed to prepare thumbnail directory")

    # 仅处理 .png 文件
    if filename.lower().endswith(".png"):
        base_name = filename[:-4]
        try:
            type_id = int(base_name)
        except ValueError:
            type_id = None

        if type_id is not None:
            text = get_type_text(type_id)

            try:
                image = create_thumb_png(width=226, height=136, text=text)
                image.save(file_path, "PNG")
                return FileResponse(file_path, media_type="image/png")
            except Exception:
                # 生成失败则继续走降级逻辑
                pass

    # 找最近的现有缩略图
    try:
        existing = []
        for f in os.listdir(thumb_root):
            if not f.lower().endswith(".png"):
                continue
            try:
                f_id = int(os.path.splitext(f)[0])
            except ValueError:
                continue
            existing.append((f_id, f))

        if existing:
            existing.sort(key=lambda x: x[0])
            target_id = None
            if filename.lower().endswith(".png"):
                try:
                    target_id = int(filename[:-4])
                except ValueError:
                    target_id = None

            if target_id is not None:
                closest = None
                min_diff = float("inf")
                for f_id, f_name in existing:
                    diff = abs(f_id - target_id)
                    if diff < min_diff:
                        min_diff = diff
                        closest = f_name
                if closest:
                    return FileResponse(os.path.join(thumb_root, closest), media_type="image/png")
    except Exception:
        pass

    # 默认缩略图：1.png
    default_path = os.path.join(thumb_root, "1.png")
    if not os.path.exists(default_path):
        try:
            image = create_thumb_png(width=226, height=136, text="WoniuNote")
            image.save(default_path, "PNG")
        except Exception:
            raise HTTPException(status_code=404, detail="Thumbnail not found")

    return FileResponse(default_path, media_type="image/png")
