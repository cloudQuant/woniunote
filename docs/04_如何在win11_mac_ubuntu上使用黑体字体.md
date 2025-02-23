### ubuntu安装黑体指令
`sudo apt-get install ttf-wqy-microhei`
### macos上安装
`brew install --cask font-wqy-microhei`

### 相关python代码

```python
import platform

# 根据操作系统选择字体路径
if platform.system() == "Windows":
    font_path = "C:/Windows/Fonts/msyh.ttc"  # 微软雅黑路径
elif platform.system() == "Darwin":  # macOS
    font_path = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"  # 微软雅黑路径
else:  # Linux (Ubuntu)
    font_path = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"  # 文泉驿微米黑路径

```
