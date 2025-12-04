# PDF/PPT 在线阅读功能使用说明

## 功能概述

本功能支持在UEditor编辑器中上传PDF和PPT文件，并在文章详情页中直接在线阅读，无需下载。

- **PDF文件**：直接使用pdf.js在浏览器中渲染
- **PPT/PPTX文件**：自动转换为PDF后使用pdf.js渲染

## 后端配置

### 1. 安装PPT转PDF工具

系统支持两种转换工具，至少需要安装其中一种：

#### 方式一：LibreOffice（推荐）

**macOS:**
```bash
brew install --cask libreoffice
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install libreoffice
```

**Windows:**
下载安装：https://www.libreoffice.org/download/

#### 方式二：unoconv

**macOS:**
```bash
brew install unoconv
```

**Ubuntu/Debian:**
```bash
sudo apt-get install unoconv
```

**注意：** unoconv需要LibreOffice作为依赖，所以通常直接安装LibreOffice即可。

### 2. 验证安装

安装完成后，在终端执行以下命令验证：

```bash
# 检查LibreOffice
libreoffice --version

# 或检查unoconv
unoconv --version
```

### 3. 后端代码已就绪

后端代码已经实现了：
- PPT转PDF功能（`backend/app/utils/ppt_converter.py`）
- UEditor上传接口扩展（`backend/app/api/ueditor.py`）

## 前端配置

### 1. 依赖已安装

pdf.js依赖已经通过npm安装：
```bash
npm install pdfjs-dist
```

### 2. 组件已创建

- PDF查看器组件：`frontend/src/components/viewer/PdfViewer.vue`
- UEditor组件已扩展：`frontend/src/components/editor/UEditor.vue`
- 文章详情页已更新：`frontend/src/views/ArticleDetail.vue`

## 使用方法

### 1. 在UEditor中上传PDF/PPT

1. 打开写文章页面
2. 点击UEditor工具栏的"附件"按钮（📎图标）
3. 选择PDF或PPT/PPTX文件
4. 上传成功后，编辑器会自动插入PDF查看器占位符

### 2. 查看文章中的PDF

1. 发布文章后，在文章详情页查看
2. PDF会自动渲染为可交互的查看器
3. 支持功能：
   - 翻页（上一页/下一页）
   - 缩放（放大/缩小/重置）
   - 下载PDF文件

## 技术实现

### 后端流程

1. 用户上传PPT/PPTX文件
2. 后端保存原始文件
3. 调用LibreOffice/unoconv转换为PDF
4. 返回PDF URL和特殊标记（`fileType: "pdf"`）
5. UEditor插入PDF占位符HTML

### 前端流程

1. UEditor上传文件后，后端返回PDF URL
2. 编辑器插入占位符：`<div class="pdf-viewer-placeholder" data-pdf-url="..."></div>`
3. 文章详情页加载时，扫描占位符
4. 动态创建Vue组件实例，挂载PDF查看器
5. pdf.js加载并渲染PDF页面

## 故障排查

### PPT转换失败

**问题：** PPT上传后没有转换为PDF

**解决方案：**
1. 检查LibreOffice是否已安装：`libreoffice --version`
2. 检查后端日志，查看转换错误信息
3. 确保LibreOffice可以访问上传的文件路径
4. 检查文件权限

### PDF无法显示

**问题：** 文章中的PDF查看器显示"加载失败"

**解决方案：**
1. 检查浏览器控制台错误信息
2. 确认PDF文件URL可访问（检查CORS设置）
3. 检查pdf.js worker路径是否正确
4. 确认文件确实存在且未损坏

### UEditor上传后没有插入占位符

**问题：** 上传PDF后，编辑器只插入了普通链接

**解决方案：**
1. 检查后端返回的JSON是否包含`fileType: "pdf"`字段
2. 检查UEditor的`afterUpfile`事件监听是否正确
3. 查看浏览器控制台是否有JavaScript错误

## 性能优化建议

1. **PPT转换**：大文件转换可能较慢，建议：
   - 限制上传文件大小（当前限制50MB）
   - 考虑异步转换，先返回上传成功，后台转换完成后通知

2. **PDF加载**：大PDF文件加载可能较慢，建议：
   - 使用PDF分页加载（pdf.js已支持）
   - 考虑服务端PDF压缩

3. **缓存策略**：
   - PPT转PDF的结果可以缓存，避免重复转换
   - PDF文件可以设置适当的HTTP缓存头

## 后续优化方向

1. 支持更多文档格式（Word、Excel等）
2. 支持PDF全文搜索
3. 支持PDF标注和批注
4. 支持PPT动画效果（转换为视频或GIF）
5. 移动端优化（触摸手势支持）

