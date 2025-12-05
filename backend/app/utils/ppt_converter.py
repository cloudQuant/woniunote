"""
PPT转PDF工具
支持多种转换方式：
1. Windows: 使用 Microsoft PowerPoint (COM) 或 LibreOffice
2. Linux/Mac: 使用 LibreOffice 或 unoconv
"""
import os
import sys
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 检测操作系统
IS_WINDOWS = sys.platform == 'win32'


def convert_ppt_to_pdf(ppt_path: str, output_dir: str = None) -> str:
    """
    将PPT/PPTX文件转换为PDF
    
    Args:
        ppt_path: PPT文件路径
        output_dir: 输出目录，如果为None则使用PPT文件所在目录
    
    Returns:
        PDF文件路径，如果转换失败则返回None
    """
    if not os.path.exists(ppt_path):
        logger.error(f"PPT file not found: {ppt_path}")
        return None
    
    # 确定输出目录和文件名
    if output_dir is None:
        output_dir = os.path.dirname(ppt_path)
    
    ppt_file = Path(ppt_path)
    pdf_filename = ppt_file.stem + ".pdf"
    pdf_path = os.path.join(output_dir, pdf_filename)
    
    # 转换为绝对路径（PowerPoint COM 需要）
    ppt_path = os.path.abspath(ppt_path)
    pdf_path = os.path.abspath(pdf_path)
    
    # Windows 优先使用 PowerPoint COM
    if IS_WINDOWS:
        if _convert_with_powerpoint_com(ppt_path, pdf_path):
            return pdf_path
    
    # 尝试使用LibreOffice转换
    if _convert_with_libreoffice(ppt_path, pdf_path):
        return pdf_path
    
    # Linux/Mac 尝试使用unoconv转换
    if not IS_WINDOWS:
        if _convert_with_unoconv(ppt_path, pdf_path):
            return pdf_path
    
    logger.warning("No conversion tool available (PowerPoint/LibreOffice/unoconv)")
    return None


def _convert_with_powerpoint_com(ppt_path: str, pdf_path: str) -> bool:
    """
    使用 Microsoft PowerPoint COM 接口转换 (仅 Windows)
    需要安装 Microsoft Office
    """
    if not IS_WINDOWS:
        return False
    
    try:
        import comtypes.client
        
        logger.info(f"Attempting PowerPoint COM conversion: {ppt_path}")
        
        # 创建 PowerPoint 应用实例
        powerpoint = comtypes.client.CreateObject("PowerPoint.Application")
        powerpoint.Visible = 1  # 设为可见有助于调试，生产环境可设为0
        
        try:
            # 打开演示文稿
            presentation = powerpoint.Presentations.Open(ppt_path, WithWindow=False)
            
            # 导出为 PDF (32 = ppSaveAsPDF)
            presentation.SaveAs(pdf_path, 32)
            
            # 关闭演示文稿
            presentation.Close()
            
            logger.info(f"Successfully converted PPT to PDF using PowerPoint: {pdf_path}")
            return True
            
        finally:
            # 退出 PowerPoint
            powerpoint.Quit()
            
    except ImportError:
        logger.warning("comtypes not installed, cannot use PowerPoint COM")
        return False
    except Exception as e:
        logger.error(f"PowerPoint COM conversion error: {e}")
        return False


def _find_libreoffice_windows() -> str:
    """在 Windows 上查找 LibreOffice 可执行文件"""
    possible_paths = [
        "C:\\Program Files\\LibreOffice\\program\\soffice.exe",
        "C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe",
        os.path.expandvars("%PROGRAMFILES%\\LibreOffice\\program\\soffice.exe"),
        os.path.expandvars("%PROGRAMFILES(X86)%\\LibreOffice\\program\\soffice.exe"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # 尝试使用 where 命令查找
    try:
        result = subprocess.run(
            ["where", "soffice"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0]
    except Exception:
        pass
    
    return None


def _find_libreoffice_unix() -> str:
    """在 Linux/Mac 上查找 LibreOffice"""
    try:
        result = subprocess.run(
            ["which", "libreoffice"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    
    # Mac 上的常见路径
    mac_paths = [
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ]
    for path in mac_paths:
        if os.path.exists(path):
            return path
    
    return None


def _convert_with_libreoffice(ppt_path: str, pdf_path: str) -> bool:
    """使用LibreOffice命令行转换"""
    try:
        # 根据系统查找 LibreOffice
        if IS_WINDOWS:
            libreoffice_cmd = _find_libreoffice_windows()
        else:
            libreoffice_cmd = _find_libreoffice_unix()
        
        if not libreoffice_cmd:
            logger.debug("LibreOffice not found")
            return False
        
        logger.info(f"Using LibreOffice: {libreoffice_cmd}")
        
        # 执行转换
        output_dir = os.path.dirname(pdf_path)
        cmd = [
            libreoffice_cmd,
            "--headless",
            "--convert-to", "pdf",
            "--outdir", output_dir,
            ppt_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 转换超时时间120秒
        )
        
        if result.returncode == 0 and os.path.exists(pdf_path):
            logger.info(f"Successfully converted PPT to PDF using LibreOffice: {pdf_path}")
            return True
        else:
            logger.error(f"LibreOffice conversion failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("LibreOffice conversion timeout")
        return False
    except Exception as e:
        logger.error(f"LibreOffice conversion error: {e}")
        return False


def _convert_with_unoconv(ppt_path: str, pdf_path: str) -> bool:
    """使用unoconv转换 (Linux/Mac)"""
    if IS_WINDOWS:
        return False
    
    try:
        # 检查unoconv是否可用
        result = subprocess.run(
            ["which", "unoconv"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            return False
        
        # 执行转换
        cmd = [
            "unoconv",
            "-f", "pdf",
            "-o", pdf_path,
            ppt_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0 and os.path.exists(pdf_path):
            logger.info(f"Successfully converted PPT to PDF using unoconv: {pdf_path}")
            return True
        else:
            logger.error(f"unoconv conversion failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("unoconv conversion timeout")
        return False
    except Exception as e:
        logger.error(f"unoconv conversion error: {e}")
        return False

