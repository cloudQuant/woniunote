#!/usr/bin/env python3
"""
预生成所有文章类型的缩略图

使用 app/core/thumbnail.py 中的 create_thumb_png 函数为每个文章类型
生成带渐变背景和文字的缩略图，保存到 resource/thumb 目录。

C++ 后端可以直接提供这些静态文件。
"""
import os
import sys

# 添加 backend 目录到 Python 路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.core.thumbnail import create_thumb_png

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


def main():
    # 确定输出目录
    thumb_dir = os.path.join(backend_dir, "resource", "thumb")
    os.makedirs(thumb_dir, exist_ok=True)
    
    print(f"输出目录: {thumb_dir}")
    print(f"共 {len(ARTICLE_TYPE_NAMES)} 个类型需要生成缩略图")
    print("-" * 50)
    
    success_count = 0
    fail_count = 0
    
    for type_id, type_name in ARTICLE_TYPE_NAMES.items():
        filename = f"{type_id}.png"
        filepath = os.path.join(thumb_dir, filename)
        
        try:
            # 使用 create_thumb_png 生成缩略图
            # 尺寸 226x136 与前端卡片匹配
            # 使用 type_id 作为 seed 确保每个类型有固定的颜色
            img = create_thumb_png(width=226, height=136, text=type_name, seed=type_id)
            img.save(filepath, "PNG")
            print(f"✓ {filename}: {type_name}")
            success_count += 1
        except Exception as e:
            print(f"✗ {filename}: {type_name} - 错误: {e}")
            fail_count += 1
    
    print("-" * 50)
    print(f"完成! 成功: {success_count}, 失败: {fail_count}")
    print(f"缩略图已保存到: {thumb_dir}")


if __name__ == "__main__":
    main()
