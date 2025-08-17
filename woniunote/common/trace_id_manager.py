"""
统一跟踪ID管理器
替换各控制器中重复的跟踪ID生成逻辑
"""
import uuid
from datetime import datetime
from typing import Optional

class TraceIdManager:
    """跟踪ID管理器"""
    
    @staticmethod
    def generate_trace_id(module_name: str = "system") -> str:
        """
        生成统一格式的跟踪ID
        
        Args:
            module_name: 模块名称，用于区分不同模块的跟踪ID
            
        Returns:
            str: 格式为 'module_yyyyMMdd_uuid' 的跟踪ID
        """
        now = datetime.now()
        date_str = now.strftime('%Y%m%d')
        uuid_short = str(uuid.uuid4())[:8]
        return f"{module_name}_{date_str}_{uuid_short}"
    
    @staticmethod
    def generate_simple_trace_id() -> str:
        """
        生成简单格式的跟踪ID
        
        Returns:
            str: 格式为 'yyyyMMdd_uuid' 的跟踪ID
        """
        now = datetime.now()
        date_str = now.strftime('%Y%m%d')
        uuid_short = str(uuid.uuid4())[:8]
        return f"{date_str}_{uuid_short}"
    
    @staticmethod
    def generate_request_id() -> str:
        """
        生成请求ID（用于单次请求追踪）
        
        Returns:
            str: 8位随机UUID
        """
        return str(uuid.uuid4())[:8]
    
    @staticmethod
    def extract_module_from_trace_id(trace_id: str) -> Optional[str]:
        """
        从跟踪ID中提取模块名称
        
        Args:
            trace_id: 跟踪ID
            
        Returns:
            str: 模块名称，如果格式不正确则返回None
        """
        try:
            parts = trace_id.split('_')
            if len(parts) >= 3:
                return parts[0]
            return None
        except (AttributeError, IndexError):
            return None
    
    @staticmethod
    def extract_date_from_trace_id(trace_id: str) -> Optional[str]:
        """
        从跟踪ID中提取日期
        
        Args:
            trace_id: 跟踪ID
            
        Returns:
            str: 日期字符串(yyyyMMdd)，如果格式不正确则返回None
        """
        try:
            parts = trace_id.split('_')
            if len(parts) >= 3:
                return parts[1]
            elif len(parts) == 2:  # 简单格式
                return parts[0]
            return None
        except (AttributeError, IndexError):
            return None
    
    @staticmethod
    def is_valid_trace_id(trace_id: str) -> bool:
        """
        验证跟踪ID格式是否正确
        
        Args:
            trace_id: 要验证的跟踪ID
            
        Returns:
            bool: 格式是否正确
        """
        if not trace_id or not isinstance(trace_id, str):
            return False
        
        parts = trace_id.split('_')
        
        # 检查是否符合标准格式 (module_yyyyMMdd_uuid) 或简单格式 (yyyyMMdd_uuid)
        if len(parts) == 3:
            # 标准格式：module_yyyyMMdd_uuid
            module, date_str, uuid_part = parts
            if len(date_str) != 8 or not date_str.isdigit():
                return False
            if len(uuid_part) != 8:
                return False
            return True
        elif len(parts) == 2:
            # 简单格式：yyyyMMdd_uuid
            date_str, uuid_part = parts
            if len(date_str) != 8 or not date_str.isdigit():
                return False
            if len(uuid_part) != 8:
                return False
            return True
        
        return False

# 为了兼容现有代码，提供模块特定的生成函数
def generate_user_trace_id() -> str:
    """生成用户模块跟踪ID"""
    return TraceIdManager.generate_trace_id("user")

def get_user_trace_id() -> str:
    """获取用户模块跟踪ID（兼容函数）"""
    return generate_user_trace_id()

def generate_article_trace_id() -> str:
    """生成文章模块跟踪ID"""
    return TraceIdManager.generate_trace_id("article")

def get_article_trace_id() -> str:
    """获取文章模块跟踪ID（兼容函数）"""
    return generate_article_trace_id()

def generate_admin_trace_id() -> str:
    """生成管理模块跟踪ID"""
    return TraceIdManager.generate_trace_id("admin")

def get_admin_trace_id() -> str:
    """获取管理模块跟踪ID（兼容函数）"""
    return generate_admin_trace_id()

def generate_card_trace_id() -> str:
    """生成卡片模块跟踪ID"""
    return TraceIdManager.generate_trace_id("card")

def get_card_trace_id() -> str:
    """获取卡片模块跟踪ID（兼容函数）"""
    return generate_card_trace_id()

def generate_comment_trace_id() -> str:
    """生成评论模块跟踪ID"""
    return TraceIdManager.generate_trace_id("comment")

def get_comment_trace_id() -> str:
    """获取评论模块跟踪ID（兼容函数）"""
    return generate_comment_trace_id()

def generate_favorite_trace_id() -> str:
    """生成收藏模块跟踪ID"""
    return TraceIdManager.generate_trace_id("favorite")

def get_favorite_trace_id() -> str:
    """获取收藏模块跟踪ID（兼容函数）"""
    return generate_favorite_trace_id()

def generate_todo_trace_id() -> str:
    """生成待办事项模块跟踪ID"""
    return TraceIdManager.generate_trace_id("todo")

def get_todo_trace_id() -> str:
    """获取待办事项模块跟踪ID（兼容函数）"""
    return generate_todo_trace_id()

def generate_ucenter_trace_id() -> str:
    """生成用户中心模块跟踪ID"""
    return TraceIdManager.generate_trace_id("ucenter")

def get_ucenter_trace_id() -> str:
    """获取用户中心模块跟踪ID（兼容函数）"""
    return generate_ucenter_trace_id()

def generate_ueditor_trace_id() -> str:
    """生成编辑器模块跟踪ID"""
    return TraceIdManager.generate_trace_id("ueditor")

def get_ueditor_trace_id() -> str:
    """获取编辑器模块跟踪ID（兼容函数）"""
    return generate_ueditor_trace_id()

def generate_articles_trace_id() -> str:
    """生成文章模块跟踪ID（module目录）"""
    return TraceIdManager.generate_trace_id("articles")

def get_articles_trace_id() -> str:
    """获取文章模块跟踪ID（兼容函数）"""
    return generate_articles_trace_id()

def generate_credits_trace_id() -> str:
    """生成积分模块跟踪ID"""
    return TraceIdManager.generate_trace_id("credits")

def get_credits_trace_id() -> str:
    """获取积分模块跟踪ID（兼容函数）"""
    return generate_credits_trace_id()

def generate_comments_trace_id() -> str:
    """生成评论模块跟踪ID（module目录）"""
    return TraceIdManager.generate_trace_id("comments")

def get_comments_trace_id() -> str:
    """获取评论模块跟踪ID（兼容函数）"""
    return generate_comments_trace_id()

def generate_favorites_trace_id() -> str:
    """生成收藏模块跟踪ID（module目录）"""
    return TraceIdManager.generate_trace_id("favorites")

def get_favorites_trace_id() -> str:
    """获取收藏模块跟踪ID（兼容函数）"""
    return generate_favorites_trace_id()

def generate_users_trace_id() -> str:
    """生成用户模块跟踪ID（module目录）"""
    return TraceIdManager.generate_trace_id("users")

def get_users_trace_id() -> str:
    """获取用户模块跟踪ID（兼容函数）"""
    return generate_users_trace_id()

# 简单跟踪ID生成函数（兼容现有代码）
def generate_trace_id() -> str:
    """生成简单跟踪ID"""
    return TraceIdManager.generate_simple_trace_id()

def get_simple_trace_id() -> str:
    """获取简单跟踪ID（兼容函数）"""
    return generate_trace_id()

# 全局跟踪ID管理器实例
trace_manager = TraceIdManager()