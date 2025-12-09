"""
文件上传 API 模块

本模块提供图片、普通文件和头像的上传功能。
"""
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from app.core.config import settings
from app.models.user import User
from app.schemas.common import ResponseModel
from app.api.deps import get_current_user_required

router = APIRouter()


def get_file_extension(filename: str) -> str:
    """
    获取文件扩展名
    
    Args:
        filename: 文件名
        
    Returns:
        str: 文件扩展名（小写）
    """
    if '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[1].lower()


def generate_filename(original_filename: str) -> str:
    """
    生成唯一文件名
    
    格式: {timestamp}_{uuid}.{ext}
    
    Args:
        original_filename: 原始文件名
        
    Returns:
        str: 生成的唯一文件名
    """
    ext = get_file_extension(original_filename)
    unique_id = uuid.uuid4().hex[:8]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{timestamp}_{unique_id}.{ext}"


@router.post("/image", response_model=ResponseModel[dict])
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_required)
):
    """
    上传图片
    
    支持 jpg, jpeg, png, gif, webp 格式。
    
    Args:
        file: 上传的文件
        current_user: 当前已认证用户
        
    Returns:
        ResponseModel[dict]: 上传结果，包含文件 URL
        
    Raises:
        HTTPException(400): 不支持的文件格式或文件过大
    """
    # 检查文件类型
    ext = get_file_extension(file.filename)
    if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的图片格式"
        )
    
    # 检查文件大小
    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制（最大{settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB）"
        )
    
    # 生成文件名和路径
    filename = generate_filename(file.filename)
    date_path = datetime.now().strftime("%Y/%m")
    upload_dir = os.path.join(settings.UPLOAD_DIR, "images", date_path)
    
    # 确保目录存在
    os.makedirs(upload_dir, exist_ok=True)
    
    # 保存文件
    file_path = os.path.join(upload_dir, filename)
    with open(file_path, 'wb') as f:
        f.write(contents)
    
    # 返回URL
    url = f"/uploads/images/{date_path}/{filename}"
    
    return ResponseModel(
        code=200,
        message="上传成功",
        data={
            "url": url,
            "filename": filename,
            "original_filename": file.filename
        }
    )


@router.post("/file", response_model=ResponseModel[dict])
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_required)
):
    """
    上传普通文件
    
    支持配置中允许的文件格式。
    
    Args:
        file: 上传的文件
        current_user: 当前已认证用户
        
    Returns:
        ResponseModel[dict]: 上传结果，包含文件 URL
        
    Raises:
        HTTPException(400): 不支持的文件格式或文件过大
    """
    # 检查文件类型
    ext = get_file_extension(file.filename)
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件格式，允许的格式：{', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # 检查文件大小
    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制（最大{settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB）"
        )
    
    # 生成文件名和路径
    filename = generate_filename(file.filename)
    date_path = datetime.now().strftime("%Y/%m")
    upload_dir = os.path.join(settings.UPLOAD_DIR, "files", date_path)
    
    # 确保目录存在
    os.makedirs(upload_dir, exist_ok=True)
    
    # 保存文件
    file_path = os.path.join(upload_dir, filename)
    with open(file_path, 'wb') as f:
        f.write(contents)
    
    # 返回URL
    url = f"/uploads/files/{date_path}/{filename}"
    
    return ResponseModel(
        code=200,
        message="上传成功",
        data={
            "url": url,
            "filename": filename,
            "original_filename": file.filename,
            "size": len(contents)
        }
    )


@router.post("/avatar", response_model=ResponseModel[dict])
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_required)
):
    """
    上传头像
    
    支持 jpg, jpeg, png, gif 格式，最大 2MB。
    
    Args:
        file: 上传的文件
        current_user: 当前已认证用户
        
    Returns:
        ResponseModel[dict]: 上传结果，包含文件 URL
        
    Raises:
        HTTPException(400): 不支持的文件格式或文件过大
    """
    # 检查文件类型
    ext = get_file_extension(file.filename)
    if ext not in ['jpg', 'jpeg', 'png', 'gif']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="头像仅支持 jpg, jpeg, png, gif 格式"
        )
    
    # 检查文件大小（头像最大2MB）
    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="头像文件大小超过限制（最大2MB）"
        )
    
    # 生成文件名
    filename = f"avatar_{current_user.userid}_{uuid.uuid4().hex[:8]}.{ext}"
    upload_dir = os.path.join(settings.UPLOAD_DIR, "avatars")
    
    # 确保目录存在
    os.makedirs(upload_dir, exist_ok=True)
    
    # 保存文件
    file_path = os.path.join(upload_dir, filename)
    with open(file_path, 'wb') as f:
        f.write(contents)
    
    # 返回URL
    url = f"/uploads/avatars/{filename}"
    
    return ResponseModel(
        code=200,
        message="上传成功",
        data={
            "url": url,
            "filename": filename
        }
    )
