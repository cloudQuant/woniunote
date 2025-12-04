"""
UEditor 富文本编辑器 API 接口
支持配置获取、图片上传、图片列表等功能
"""
import os
import time
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Query, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image

from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# UEditor 配置
UEDITOR_CONFIG = {
    "imageActionName": "uploadimage",
    "imageFieldName": "upfile",
    "imageMaxSize": 10485760,  # 10MB
    "imageAllowFiles": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"],
    "imageCompressEnable": True,
    "imageCompressBorder": 1600,
    "imageInsertAlign": "none",
    "imageUrlPrefix": "",
    "imagePathFormat": "/uploads/{yyyy}{mm}{dd}/{time}{rand:6}",

    "scrawlActionName": "uploadscrawl",
    "scrawlFieldName": "upfile",
    "scrawlPathFormat": "/uploads/{yyyy}{mm}{dd}/{time}{rand:6}",
    "scrawlMaxSize": 2048000,
    "scrawlUrlPrefix": "",
    "scrawlInsertAlign": "none",

    "snapscreenActionName": "uploadimage",
    "snapscreenPathFormat": "/uploads/{yyyy}{mm}{dd}/{time}{rand:6}",
    "snapscreenUrlPrefix": "",
    "snapscreenInsertAlign": "none",

    "catcherLocalDomain": ["127.0.0.1", "localhost"],
    "catcherActionName": "catchimage",
    "catcherFieldName": "source",
    "catcherPathFormat": "/uploads/{yyyy}{mm}{dd}/{time}{rand:6}",
    "catcherUrlPrefix": "",
    "catcherMaxSize": 2048000,
    "catcherAllowFiles": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"],

    "videoActionName": "uploadvideo",
    "videoFieldName": "upfile",
    "videoPathFormat": "/uploads/{yyyy}{mm}{dd}/{time}{rand:6}",
    "videoUrlPrefix": "",
    "videoMaxSize": 102400000,
    "videoAllowFiles": [".flv", ".swf", ".mkv", ".avi", ".rm", ".rmvb", ".mpeg", ".mpg",
                        ".ogg", ".ogv", ".mov", ".wmv", ".mp4", ".webm", ".mp3", ".wav", ".mid"],

    "fileActionName": "uploadfile",
    "fileFieldName": "upfile",
    "filePathFormat": "/uploads/{yyyy}{mm}{dd}/{time}{rand:6}",
    "fileUrlPrefix": "",
    "fileMaxSize": 51200000,
    "fileAllowFiles": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp",
                       ".flv", ".swf", ".mkv", ".avi", ".rm", ".rmvb", ".mpeg", ".mpg",
                       ".ogg", ".ogv", ".mov", ".wmv", ".mp4", ".webm", ".mp3", ".wav", ".mid",
                       ".rar", ".zip", ".tar", ".gz", ".7z", ".bz2", ".cab", ".iso",
                       ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf", ".txt", ".md", ".xml"],

    "imageManagerActionName": "listimage",
    "imageManagerListPath": "/uploads/",
    "imageManagerListSize": 20,
    "imageManagerUrlPrefix": "",
    "imageManagerInsertAlign": "none",
    "imageManagerAllowFiles": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"],

    "fileManagerActionName": "listfile",
    "fileManagerListPath": "/uploads/",
    "fileManagerUrlPrefix": "",
    "fileManagerListSize": 20,
    "fileManagerAllowFiles": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp",
                              ".flv", ".swf", ".mkv", ".avi", ".rm", ".rmvb", ".mpeg", ".mpg",
                              ".ogg", ".ogv", ".mov", ".wmv", ".mp4", ".webm", ".mp3", ".wav", ".mid",
                              ".rar", ".zip", ".tar", ".gz", ".7z", ".bz2", ".cab", ".iso",
                              ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf", ".txt", ".md", ".xml"]
}

# 上传目录
def get_upload_dir() -> str:
    """获取上传目录"""
    # 尝试多个可能的位置
    current_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    project_root = os.path.dirname(backend_dir)
    
    possible_paths = [
        os.path.join(project_root, "woniunote", "resource", "upload"),
        os.path.join(backend_dir, "uploads"),
        os.path.join(os.getcwd(), "uploads"),
    ]
    
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            return abs_path
    
    # 如果都不存在，创建 backend/uploads
    upload_dir = os.path.join(backend_dir, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def compress_image(source: str, dest: str, max_width: int = 1600) -> bool:
    """压缩图片"""
    try:
        with Image.open(source) as img:
            # 如果图片宽度大于最大宽度，则压缩
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # 转换为 RGB 模式
            if img.mode in ('RGBA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    rgb_img.paste(img, mask=img.split()[-1])
                else:
                    rgb_img.paste(img)
                img = rgb_img
            
            img.save(dest, 'JPEG', quality=85, optimize=True)
        return True
    except Exception as e:
        logger.error(f"Image compression failed: {e}")
        return False


@router.api_route("/uedit", methods=["GET", "POST"])
async def ueditor_handler(
    action: Optional[str] = Query(None),
    upfile: Optional[UploadFile] = File(None)
):
    """
    UEditor 统一处理接口
    支持 config, uploadimage, listimage 等操作
    """
    logger.info(f"UEditor request: action={action}")
    
    # 获取配置
    if action == "config":
        return JSONResponse(content=UEDITOR_CONFIG)
    
    # 上传图片
    elif action == "uploadimage":
        if not upfile:
            return JSONResponse(content={"state": "FAIL", "message": "No file uploaded"})
        
        try:
            # 验证文件类型
            filename = upfile.filename or "upload.jpg"
            suffix = os.path.splitext(filename)[1].lower()
            
            if suffix not in UEDITOR_CONFIG["imageAllowFiles"]:
                return JSONResponse(content={"state": "FAIL", "message": "Invalid file type"})
            
            # 生成新文件名
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            random_str = uuid.uuid4().hex[:6]
            new_filename = f"{timestamp}_{random_str}{suffix}"
            
            # 保存文件
            upload_dir = get_upload_dir()
            os.makedirs(upload_dir, exist_ok=True)
            save_path = os.path.join(upload_dir, new_filename)
            
            # 写入文件
            content = await upfile.read()
            with open(save_path, "wb") as f:
                f.write(content)
            
            # 压缩图片
            if suffix in ['.jpg', '.jpeg', '.png']:
                compress_image(save_path, save_path, 1600)
            
            logger.info(f"Image uploaded: {new_filename}")
            
            return JSONResponse(content={
                "state": "SUCCESS",
                "url": f"/api/uploads/{new_filename}",
                "title": filename,
                "original": filename
            })
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return JSONResponse(content={"state": "FAIL", "message": str(e)})
    
    # 图片列表
    elif action == "listimage":
        try:
            upload_dir = get_upload_dir()
            image_list = []
            
            if os.path.exists(upload_dir):
                for filename in os.listdir(upload_dir):
                    suffix = os.path.splitext(filename)[1].lower()
                    if suffix in UEDITOR_CONFIG["imageManagerAllowFiles"]:
                        image_list.append({"url": f"/api/uploads/{filename}"})
            
            return JSONResponse(content={
                "state": "SUCCESS",
                "list": image_list[:UEDITOR_CONFIG["imageManagerListSize"]],
                "start": 0,
                "total": len(image_list)
            })
            
        except Exception as e:
            logger.error(f"List images failed: {e}")
            return JSONResponse(content={"state": "FAIL", "message": str(e)})
    
    # 上传涂鸦
    elif action == "uploadscrawl":
        if not upfile:
            return JSONResponse(content={"state": "FAIL", "message": "No file uploaded"})
        
        try:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            random_str = uuid.uuid4().hex[:6]
            new_filename = f"scrawl_{timestamp}_{random_str}.png"
            
            upload_dir = get_upload_dir()
            os.makedirs(upload_dir, exist_ok=True)
            save_path = os.path.join(upload_dir, new_filename)
            
            content = await upfile.read()
            with open(save_path, "wb") as f:
                f.write(content)
            
            return JSONResponse(content={
                "state": "SUCCESS",
                "url": f"/api/uploads/{new_filename}",
                "title": new_filename,
                "original": new_filename
            })
            
        except Exception as e:
            logger.error(f"Scrawl upload failed: {e}")
            return JSONResponse(content={"state": "FAIL", "message": str(e)})
    
    # 上传视频
    elif action == "uploadvideo":
        if not upfile:
            return JSONResponse(content={"state": "FAIL", "message": "No file uploaded"})
        
        try:
            filename = upfile.filename or "video.mp4"
            suffix = os.path.splitext(filename)[1].lower()
            
            if suffix not in UEDITOR_CONFIG["videoAllowFiles"]:
                return JSONResponse(content={"state": "FAIL", "message": "Invalid video type"})
            
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            random_str = uuid.uuid4().hex[:6]
            new_filename = f"video_{timestamp}_{random_str}{suffix}"
            
            upload_dir = get_upload_dir()
            os.makedirs(upload_dir, exist_ok=True)
            save_path = os.path.join(upload_dir, new_filename)
            
            content = await upfile.read()
            with open(save_path, "wb") as f:
                f.write(content)
            
            return JSONResponse(content={
                "state": "SUCCESS",
                "url": f"/api/uploads/{new_filename}",
                "title": filename,
                "original": filename
            })
            
        except Exception as e:
            logger.error(f"Video upload failed: {e}")
            return JSONResponse(content={"state": "FAIL", "message": str(e)})
    
    # 上传附件（支持PDF/PPT特殊处理）
    elif action == "uploadfile":
        if not upfile:
            return JSONResponse(content={"state": "FAIL", "message": "No file uploaded"})
        
        try:
            filename = upfile.filename or "file"
            suffix = os.path.splitext(filename)[1].lower()
            
            if suffix not in UEDITOR_CONFIG["fileAllowFiles"]:
                return JSONResponse(content={"state": "FAIL", "message": "Invalid file type"})
            
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            random_str = uuid.uuid4().hex[:6]
            new_filename = f"file_{timestamp}_{random_str}{suffix}"
            
            upload_dir = get_upload_dir()
            os.makedirs(upload_dir, exist_ok=True)
            save_path = os.path.join(upload_dir, new_filename)
            
            content = await upfile.read()
            with open(save_path, "wb") as f:
                f.write(content)
            
            # 如果是PPT/PPTX，转换为PDF
            pdf_url = None
            if suffix in ['.ppt', '.pptx']:
                from app.utils.ppt_converter import convert_ppt_to_pdf
                pdf_path = convert_ppt_to_pdf(save_path, upload_dir)
                if pdf_path and os.path.exists(pdf_path):
                    pdf_filename = os.path.basename(pdf_path)
                    pdf_url = f"/api/uploads/{pdf_filename}"
                    logger.info(f"PPT converted to PDF: {pdf_filename}")
            
            # 构建返回数据
            response_data = {
                "state": "SUCCESS",
                "url": f"/api/uploads/{new_filename}",
                "title": filename,
                "original": filename
            }
            
            # 如果是PDF或PPT，返回包含PDF查看器占位符的HTML，而不是普通链接
            if suffix == '.pdf' or pdf_url:
                pdf_url_final = pdf_url if pdf_url else f"/api/uploads/{new_filename}"
                # UEditor会直接插入这个HTML到编辑器中
                response_data["url"] = pdf_url_final
                response_data["fileType"] = "pdf"
                response_data["pdfUrl"] = pdf_url_final
                # 返回HTML片段，包含可见内容防止被UEditor过滤
                # 使用p标签包裹，添加文字内容，确保不会被过滤
                response_data["html"] = f'''<p class="pdf-viewer-placeholder" data-pdf-url="{pdf_url_final}" data-type="pdf" style="background:#f5f5f5;padding:20px;border:1px dashed #ccc;border-radius:4px;text-align:center;margin:10px 0;">
📄 PDF文档: {filename}<br/><small style="color:#999;">文档将在发布后以PDF查看器形式显示</small>
</p>'''
            
            return JSONResponse(content=response_data)
            
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            return JSONResponse(content={"state": "FAIL", "message": str(e)})
    
    # 未知操作
    else:
        return JSONResponse(content={"state": "FAIL", "message": f"Unknown action: {action}"})


@router.get("/uploads/{filename:path}")
async def serve_upload(filename: str):
    """提供上传文件的访问"""
    from fastapi.responses import FileResponse
    
    upload_dir = get_upload_dir()
    file_path = os.path.join(upload_dir, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path)
