import yaml
from PIL import Image, ImageDraw, ImageFont
import os

# YAML content
yaml_content = """# 配置文章类型
ARTICLE_TYPES:
  1: 交易策略
  101: CTA策略
  102: 统计套利
  103: 高频交易
  104: 因子策略
  105: 选股与择时
  106: 机器学习
  107: 深度学习
  2: 量化框架
  201: backtrader
  202: wondertrader
  203: wtpy
  204: pyfolio
  205: alphalens
  3: 投资
  301: 股票
  302: 期货
  303: 期权
  304: 外汇
  305: crypto
  4: 理财
  401: 基金
  402: 保险
  403: 信托
  404: 银行理财
  405: 存款
  5: 区块链与defi
  501: 去中心化交易所
  502: 去中心化金融
  503: 去中心化借贷
  504: 去中心化治理
  505: 其他defi
  506: 区块链
  507: 比特币
  508: 以太坊
  6: 机器学习
  601: tensorflow
  602: pytorch
  603: keras
  604: scikit-learn
  605: 机器学习与交易
  7: 编程
  701: python
  702: c++
  703: cython
  704: java
  705: javascript
  706: cython
  707: pybind11
  708: swing
  8: 笔记
  801: 幸福
  802: 金融
  803: 经济
  804: 哲学
  805: 历史
  806: 科技
  9: 教程
  901: woniunote入门教程
  902: backtrader基础教程
  903: airflow入门教程
  904: arrow入门教程
  905: 量化交易入门教程
  906: 机器学习入门教程
  907: ib_tws_api入门教程
"""

# Parse YAML
article_types = yaml.safe_load(yaml_content)["ARTICLE_TYPES"]

# Directory to save images
output_dir = "generated_images"
os.makedirs(output_dir, exist_ok=True)

# Font configuration
font_path = "/System/Library/Fonts/Supplemental/Songti.ttc"  # Replace with a valid Chinese font path
image_size = (541, 273)  # (width, height)

# Generate images
for key, value in article_types.items():
    image = Image.new("RGB", image_size, (255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Dynamically adjust font size
    font_size = 60  # Initial font size
    font = ImageFont.truetype(font_path, font_size)
    text_bbox = draw.textbbox((0, 0), value, font=font)

    while text_bbox[2] - text_bbox[0] > image_size[0] * 0.9 or text_bbox[3] - text_bbox[1] > image_size[1] * 0.9:
        font_size -= 2
        font = ImageFont.truetype(font_path, font_size)
        text_bbox = draw.textbbox((0, 0), value, font=font)

    # Center the text
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    position = ((image_size[0] - text_width) // 2, (image_size[1] - text_height) // 2)

    # Draw text
    text_color = (0, 0, 255) if int(key) % 2 == 0 else (255, 0, 0)
    draw.text(position, value, fill=text_color, font=font)

    # Save image
    filename = os.path.join(output_dir, f"{key}.png")
    image.save(filename)

print(f"Images saved to {output_dir}")




