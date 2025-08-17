#!/usr/bin/env python3
"""
统一响应格式系统
提供标准化的API响应格式和分页响应
"""

import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from flask import jsonify, Response
from woniunote.common.simple_logger import get_simple_logger

logger = get_simple_logger('unified_response')

@dataclass
class PageInfo:
    """分页信息"""
    page: int  # 当前页码
    page_size: int  # 每页大小
    total: int  # 总记录数
    total_pages: int  # 总页数
    has_next: bool  # 是否有下一页
    has_prev: bool  # 是否有上一页

@dataclass
class ApiResponse:
    """标准API响应"""
    success: bool
    data: Any = None
    message: str = ""
    error_code: Optional[int] = None
    timestamp: int = None
    request_id: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = int(time.time() * 1000)

@dataclass
class PaginatedResponse(ApiResponse):
    """分页响应"""
    pagination: Optional[PageInfo] = None

class ResponseBuilder:
    """响应构建器"""
    
    @staticmethod
    def success(data: Any = None, message: str = "操作成功", request_id: str = None) -> Dict[str, Any]:
        """构建成功响应"""
        response = ApiResponse(
            success=True,
            data=data,
            message=message,
            request_id=request_id
        )
        return asdict(response)
    
    @staticmethod
    def error(message: str, error_code: int = None, data: Any = None, request_id: str = None) -> Dict[str, Any]:
        """构建错误响应"""
        response = ApiResponse(
            success=False,
            data=data,
            message=message,
            error_code=error_code,
            request_id=request_id
        )
        return asdict(response)
    
    @staticmethod
    def paginated(data: List[Any], page: int, page_size: int, total: int, 
                 message: str = "查询成功", request_id: str = None) -> Dict[str, Any]:
        """构建分页响应"""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        
        pagination = PageInfo(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
        
        response = PaginatedResponse(
            success=True,
            data=data,
            message=message,
            pagination=pagination,
            request_id=request_id
        )
        return asdict(response)
    
    @staticmethod
    def list_response(items: List[Any], message: str = "查询成功", 
                     total: int = None, request_id: str = None) -> Dict[str, Any]:
        """构建列表响应"""
        response_data = {
            'items': items,
            'count': len(items)
        }
        
        if total is not None:
            response_data['total'] = total
        
        return ResponseBuilder.success(
            data=response_data,
            message=message,
            request_id=request_id
        )
    
    @staticmethod
    def create_response(data: Any, message: str = "创建成功", request_id: str = None) -> Dict[str, Any]:
        """构建创建响应"""
        return ResponseBuilder.success(data=data, message=message, request_id=request_id)
    
    @staticmethod
    def update_response(data: Any = None, message: str = "更新成功", request_id: str = None) -> Dict[str, Any]:
        """构建更新响应"""
        return ResponseBuilder.success(data=data, message=message, request_id=request_id)
    
    @staticmethod
    def delete_response(message: str = "删除成功", request_id: str = None) -> Dict[str, Any]:
        """构建删除响应"""
        return ResponseBuilder.success(message=message, request_id=request_id)
    
    @staticmethod
    def validation_error(field: str, message: str, request_id: str = None) -> Dict[str, Any]:
        """构建验证错误响应"""
        error_data = {
            'field': field,
            'validation_message': message
        }
        return ResponseBuilder.error(
            message=f"参数验证失败: {message}",
            error_code=2000,
            data=error_data,
            request_id=request_id
        )
    
    @staticmethod
    def not_found_error(resource: str = "资源", request_id: str = None) -> Dict[str, Any]:
        """构建资源未找到响应"""
        return ResponseBuilder.error(
            message=f"{resource}未找到",
            error_code=2003,
            request_id=request_id
        )
    
    @staticmethod
    def permission_error(message: str = "权限不足", request_id: str = None) -> Dict[str, Any]:
        """构建权限错误响应"""
        return ResponseBuilder.error(
            message=message,
            error_code=2002,
            request_id=request_id
        )
    
    @staticmethod
    def server_error(message: str = "服务器内部错误", request_id: str = None) -> Dict[str, Any]:
        """构建服务器错误响应"""
        return ResponseBuilder.error(
            message=message,
            error_code=1000,
            request_id=request_id
        )

class FlaskResponseHelper:
    """Flask响应助手"""
    
    @staticmethod
    def json_response(data: Dict[str, Any], status_code: int = 200) -> Response:
        """创建JSON响应"""
        response = jsonify(data)
        response.status_code = status_code
        return response
    
    @staticmethod
    def success_json(data: Any = None, message: str = "操作成功", 
                    request_id: str = None, status_code: int = 200) -> Response:
        """创建成功JSON响应"""
        response_data = ResponseBuilder.success(data, message, request_id)
        return FlaskResponseHelper.json_response(response_data, status_code)
    
    @staticmethod
    def error_json(message: str, error_code: int = None, data: Any = None,
                  request_id: str = None, status_code: int = 400) -> Response:
        """创建错误JSON响应"""
        response_data = ResponseBuilder.error(message, error_code, data, request_id)
        return FlaskResponseHelper.json_response(response_data, status_code)
    
    @staticmethod
    def paginated_json(data: List[Any], page: int, page_size: int, total: int,
                      message: str = "查询成功", request_id: str = None) -> Response:
        """创建分页JSON响应"""
        response_data = ResponseBuilder.paginated(data, page, page_size, total, message, request_id)
        return FlaskResponseHelper.json_response(response_data, 200)
    
    @staticmethod
    def created_json(data: Any, message: str = "创建成功", request_id: str = None) -> Response:
        """创建资源创建响应"""
        response_data = ResponseBuilder.create_response(data, message, request_id)
        return FlaskResponseHelper.json_response(response_data, 201)
    
    @staticmethod
    def no_content() -> Response:
        """创建无内容响应"""
        response = jsonify({})
        response.status_code = 204
        return response

def standardize_response(func):
    """标准化响应装饰器"""
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            
            # 如果返回的已经是标准响应格式，直接返回
            if isinstance(result, (dict, tuple)):
                if isinstance(result, dict) and 'success' in result:
                    return result
                elif isinstance(result, tuple):
                    return result
            
            # 包装成功响应
            if result is None:
                return ResponseBuilder.success(message="操作成功")
            else:
                return ResponseBuilder.success(data=result)
                
        except Exception as e:
            logger.error(f"函数执行异常: {func.__name__}", {
                'error': str(e),
                'function': f"{func.__module__}.{func.__name__}"
            })
            return ResponseBuilder.server_error(f"操作失败: {str(e)}")
    
    return wrapper

def paginate_query_result(query_result: List[Any], page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """对查询结果进行分页处理"""
    total = len(query_result)
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    
    paginated_data = query_result[start_index:end_index]
    
    return ResponseBuilder.paginated(
        data=paginated_data,
        page=page,
        page_size=page_size,
        total=total
    )

def format_article_response(article: Any, include_content: bool = True) -> Dict[str, Any]:
    """格式化文章响应数据"""
    if not article:
        return None
    
    # 基础字段
    formatted = {
        'articleid': getattr(article, 'articleid', None),
        'userid': getattr(article, 'userid', None),
        'headline': getattr(article, 'headline', ''),
        'type': getattr(article, 'type', 0),
        'thumbnail': getattr(article, 'thumbnail', ''),
        'credit': getattr(article, 'credit', 0),
        'readcount': getattr(article, 'readcount', 0),
        'replycount': getattr(article, 'replycount', 0),
        'recommended': getattr(article, 'recommended', 0),
        'hidden': getattr(article, 'hidden', 0),
        'drafted': getattr(article, 'drafted', 0),
        'checked': getattr(article, 'checked', 1),
        'createtime': getattr(article, 'createtime', None),
        'updatetime': getattr(article, 'updatetime', None)
    }
    
    # 可选包含内容
    if include_content:
        formatted['content'] = getattr(article, 'content', '')
    
    # 格式化时间
    for time_field in ['createtime', 'updatetime']:
        if formatted[time_field]:
            formatted[time_field] = formatted[time_field].strftime('%Y-%m-%d %H:%M:%S')
    
    return formatted

def format_user_response(user: Any, include_sensitive: bool = False) -> Dict[str, Any]:
    """格式化用户响应数据"""
    if not user:
        return None
    
    # 基础字段
    formatted = {
        'userid': getattr(user, 'userid', None),
        'username': getattr(user, 'username', ''),
        'nickname': getattr(user, 'nickname', ''),
        'avatar': getattr(user, 'avatar', ''),
        'role': getattr(user, 'role', 'user'),
        'credit': getattr(user, 'credit', 0),
        'createtime': getattr(user, 'createtime', None),
        'updatetime': getattr(user, 'updatetime', None)
    }
    
    # 敏感信息（仅在必要时包含）
    if include_sensitive:
        formatted['qq'] = getattr(user, 'qq', '')
    
    # 格式化时间
    for time_field in ['createtime', 'updatetime']:
        if formatted[time_field]:
            formatted[time_field] = formatted[time_field].strftime('%Y-%m-%d %H:%M:%S')
    
    return formatted

# 全局响应构建器实例
response_builder = ResponseBuilder()
flask_helper = FlaskResponseHelper()

# 便捷函数
def success_response(data: Any = None, message: str = "操作成功") -> Dict[str, Any]:
    """便捷成功响应函数"""
    return response_builder.success(data, message)

def error_response(message: str, error_code: int = None) -> Dict[str, Any]:
    """便捷错误响应函数"""
    return response_builder.error(message, error_code)

def paginated_response(data: List[Any], page: int, page_size: int, total: int) -> Dict[str, Any]:
    """便捷分页响应函数"""
    return response_builder.paginated(data, page, page_size, total)