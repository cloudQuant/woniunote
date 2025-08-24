#!/usr/bin/env python3
"""
代码重构助手
提供公共方法提取、重复代码消除、代码质量改进等功能
"""

import time
from typing import Dict, Any, List, Optional, Callable, Union
from functools import wraps
from woniunote.common.unified_logging import get_simple_logger
from woniunote.common.unified_response import success_response, error_response
from woniunote.common.unified_error_handler import exception_handler

logger = get_simple_logger('code_refactor_helper')

class CommonValidators:
    """公共验证器"""
    
    @staticmethod
    def validate_pagination_params(page: Any, page_size: Any, max_page_size: int = 100) -> Dict[str, int]:
        """验证分页参数"""
        try:
            page = int(page) if page else 1
            page_size = int(page_size) if page_size else 20
            
            if page < 1:
                page = 1
            if page_size < 1:
                page_size = 20
            if page_size > max_page_size:
                page_size = max_page_size
                
            return {
                'page': page,
                'page_size': page_size,
                'offset': (page - 1) * page_size
            }
        except (ValueError, TypeError):
            return {
                'page': 1,
                'page_size': 20,
                'offset': 0
            }
    
    @staticmethod
    def validate_sort_params(sort_field: str, sort_order: str, 
                           allowed_fields: List[str]) -> Dict[str, str]:
        """验证排序参数"""
        # 默认值
        default_field = allowed_fields[0] if allowed_fields else 'id'
        default_order = 'desc'
        
        # 验证排序字段
        if sort_field not in allowed_fields:
            sort_field = default_field
        
        # 验证排序方向
        if sort_order.lower() not in ['asc', 'desc']:
            sort_order = default_order
        
        return {
            'sort_field': sort_field,
            'sort_order': sort_order.lower()
        }
    
    @staticmethod
    def validate_id_param(id_value: Any, param_name: str = "ID") -> int:
        """验证ID参数"""
        try:
            id_int = int(id_value)
            if id_int <= 0:
                raise ValueError(f"{param_name}必须是正整数")
            return id_int
        except (ValueError, TypeError):
            raise ValueError(f"{param_name}格式错误")

class CommonQueryBuilders:
    """公共查询构建器"""
    
    @staticmethod
    def build_pagination_query(base_query, page: int, page_size: int):
        """构建分页查询"""
        offset = (page - 1) * page_size
        return base_query.offset(offset).limit(page_size)
    
    @staticmethod
    def build_search_conditions(search_term: str, search_fields: List[str]):
        """构建搜索条件"""
        from sqlalchemy import or_, func
        
        if not search_term or not search_fields:
            return None
        
        search_conditions = []
        for field in search_fields:
            search_conditions.append(func.lower(field).like(f'%{search_term.lower()}%'))
        
        return or_(*search_conditions) if search_conditions else None
    
    @staticmethod
    def build_date_range_conditions(date_field, start_date: str = None, end_date: str = None):
        """构建日期范围条件"""
        from sqlalchemy import and_
        from datetime import datetime
        
        conditions = []
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                conditions.append(date_field >= start_dt)
            except ValueError:
                logger.warning(f"无效的开始日期格式: {start_date}")
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                conditions.append(date_field <= end_dt)
            except ValueError:
                logger.warning(f"无效的结束日期格式: {end_date}")
        
        return and_(*conditions) if conditions else None

class CommonResponseHandlers:
    """公共响应处理器"""
    
    @staticmethod
    def handle_list_query(query_func: Callable, format_func: Callable = None,
                         page: int = 1, page_size: int = 20, **kwargs) -> Dict[str, Any]:
        """处理列表查询的通用逻辑"""
        try:
            # 执行查询
            result = query_func(page=page, page_size=page_size, **kwargs)
            
            # 格式化数据
            if format_func and hasattr(result, '__iter__'):
                formatted_data = [format_func(item) for item in result]
            else:
                formatted_data = result
            
            # 计算总数（如果查询函数支持）
            try:
                total = query_func(count_only=True, **kwargs)
            except:
                total = len(formatted_data)
            
            return success_response({
                'items': formatted_data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': total,
                    'total_pages': (total + page_size - 1) // page_size
                }
            })
            
        except Exception as e:
            logger.error("列表查询处理失败", {
                'error': str(e),
                'page': page,
                'page_size': page_size
            })
            return error_response("查询失败")
    
    @staticmethod
    def handle_detail_query(query_func: Callable, resource_id: int,
                           format_func: Callable = None, resource_name: str = "资源") -> Dict[str, Any]:
        """处理详情查询的通用逻辑"""
        try:
            # 执行查询
            result = query_func(resource_id)
            
            if not result:
                return error_response(f"{resource_name}未找到", error_code=2003)
            
            # 格式化数据
            if format_func:
                formatted_data = format_func(result)
            else:
                formatted_data = result
            
            return success_response(formatted_data)
            
        except Exception as e:
            logger.error("详情查询处理失败", {
                'error': str(e),
                'resource_id': resource_id
            })
            return error_response("查询失败")
    
    @staticmethod
    def handle_create_operation(create_func: Callable, data: Dict[str, Any],
                              format_func: Callable = None, resource_name: str = "资源") -> Dict[str, Any]:
        """处理创建操作的通用逻辑"""
        try:
            # 执行创建
            result = create_func(data)
            
            # 格式化数据
            if format_func:
                formatted_data = format_func(result)
            else:
                formatted_data = result
            
            return success_response(formatted_data, f"{resource_name}创建成功")
            
        except Exception as e:
            logger.error("创建操作处理失败", {
                'error': str(e),
                'data': data
            })
            return error_response("创建失败")
    
    @staticmethod
    def handle_update_operation(update_func: Callable, resource_id: int, data: Dict[str, Any],
                              format_func: Callable = None, resource_name: str = "资源") -> Dict[str, Any]:
        """处理更新操作的通用逻辑"""
        try:
            # 执行更新
            result = update_func(resource_id, data)
            
            if not result:
                return error_response(f"{resource_name}未找到", error_code=2003)
            
            # 格式化数据
            if format_func:
                formatted_data = format_func(result)
            else:
                formatted_data = result
            
            return success_response(formatted_data, f"{resource_name}更新成功")
            
        except Exception as e:
            logger.error("更新操作处理失败", {
                'error': str(e),
                'resource_id': resource_id,
                'data': data
            })
            return error_response("更新失败")
    
    @staticmethod
    def handle_delete_operation(delete_func: Callable, resource_id: int,
                              resource_name: str = "资源") -> Dict[str, Any]:
        """处理删除操作的通用逻辑"""
        try:
            # 执行删除
            success = delete_func(resource_id)
            
            if not success:
                return error_response(f"{resource_name}未找到", error_code=2003)
            
            return success_response(None, f"{resource_name}删除成功")
            
        except Exception as e:
            logger.error("删除操作处理失败", {
                'error': str(e),
                'resource_id': resource_id
            })
            return error_response("删除失败")

class CommonDecorators:
    """公共装饰器"""
    
    @staticmethod
    def validate_request_params(**param_validators):
        """请求参数验证装饰器"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                from flask import request
                
                # 验证参数
                validated_params = {}
                for param_name, validator in param_validators.items():
                    param_value = request.args.get(param_name) or request.form.get(param_name)
                    try:
                        validated_params[param_name] = validator(param_value)
                    except ValueError as e:
                        return error_response(f"参数{param_name}验证失败: {str(e)}")
                
                # 将验证后的参数传递给函数
                kwargs.update(validated_params)
                return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    @staticmethod
    def require_pagination(max_page_size: int = 100):
        """分页参数装饰器"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                from flask import request
                
                page = request.args.get('page', 1)
                page_size = request.args.get('page_size', 20)
                
                pagination = CommonValidators.validate_pagination_params(
                    page, page_size, max_page_size
                )
                
                kwargs.update(pagination)
                return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    @staticmethod
    def log_operation(operation_name: str, log_params: bool = True):
        """操作日志装饰器"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                
                log_data = {
                    'operation': operation_name,
                    'function': f"{func.__module__}.{func.__name__}",
                    'start_time': start_time
                }
                
                if log_params:
                    log_data.update({
                        'args_count': len(args),
                        'kwargs_keys': list(kwargs.keys())
                    })
                
                try:
                    result = func(*args, **kwargs)
                    
                    duration = time.time() - start_time
                    log_data.update({
                        'success': True,
                        'duration_seconds': round(duration, 3)
                    })
                    
                    logger.info(f"{operation_name}操作完成", log_data)
                    return result
                    
                except Exception as e:
                    duration = time.time() - start_time
                    log_data.update({
                        'success': False,
                        'duration_seconds': round(duration, 3),
                        'error': str(e)
                    })
                    
                    logger.error(f"{operation_name}操作失败", log_data)
                    raise
            
            return wrapper
        return decorator

class CommonUtilities:
    """公共工具函数"""
    
    @staticmethod
    def safe_int_conversion(value: Any, default: int = 0) -> int:
        """安全的整数转换"""
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_float_conversion(value: Any, default: float = 0.0) -> float:
        """安全的浮点数转换"""
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def format_datetime(dt, format_str: str = '%Y-%m-%d %H:%M:%S') -> Optional[str]:
        """格式化日期时间"""
        if not dt:
            return None
        try:
            return dt.strftime(format_str)
        except:
            return str(dt)
    
    @staticmethod
    def truncate_string(text: str, max_length: int = 100, suffix: str = '...') -> str:
        """截断字符串"""
        if not text or len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def clean_dict(data: Dict[str, Any], remove_none: bool = True, 
                  remove_empty: bool = False) -> Dict[str, Any]:
        """清理字典数据"""
        cleaned = {}
        for key, value in data.items():
            if remove_none and value is None:
                continue
            if remove_empty and value == '':
                continue
            cleaned[key] = value
        return cleaned
    
    @staticmethod
    def batch_process(items: List[Any], batch_size: int = 100,
                     processor: Callable = None) -> List[Any]:
        """批量处理数据"""
        if not processor:
            return items
        
        results = []
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = processor(batch)
            if isinstance(batch_results, list):
                results.extend(batch_results)
            else:
                results.append(batch_results)
        
        return results

# 常用的CRUD模板
class CRUDTemplate:
    """CRUD操作模板"""
    
    def __init__(self, model_class, db_session_manager):
        self.model_class = model_class
        self.db_session_manager = db_session_manager
    
    def list_items(self, page: int = 1, page_size: int = 20, **filters):
        """列表查询模板"""
        with self.db_session_manager.get_session() as session:
            query = session.query(self.model_class)
            
            # 应用过滤条件
            for field, value in filters.items():
                if hasattr(self.model_class, field) and value is not None:
                    query = query.filter(getattr(self.model_class, field) == value)
            
            # 分页
            total = query.count()
            offset = (page - 1) * page_size
            items = query.offset(offset).limit(page_size).all()
            
            return {
                'items': items,
                'total': total,
                'page': page,
                'page_size': page_size
            }
    
    def get_item(self, item_id: int):
        """详情查询模板"""
        with self.db_session_manager.get_session() as session:
            return session.query(self.model_class).filter_by(id=item_id).first()
    
    def create_item(self, data: Dict[str, Any]):
        """创建模板"""
        with self.db_session_manager.get_session() as session:
            item = self.model_class(**data)
            session.add(item)
            session.flush()  # 获取ID
            return item
    
    def update_item(self, item_id: int, data: Dict[str, Any]):
        """更新模板"""
        with self.db_session_manager.get_session() as session:
            item = session.query(self.model_class).filter_by(id=item_id).first()
            if not item:
                return None
            
            for field, value in data.items():
                if hasattr(item, field):
                    setattr(item, field, value)
            
            return item
    
    def delete_item(self, item_id: int):
        """删除模板"""
        with self.db_session_manager.get_session() as session:
            item = session.query(self.model_class).filter_by(id=item_id).first()
            if not item:
                return False
            
            session.delete(item)
            return True

# 全局实例
common_validators = CommonValidators()
common_query_builders = CommonQueryBuilders()
common_response_handlers = CommonResponseHandlers()
common_decorators = CommonDecorators()
common_utilities = CommonUtilities()

# 便捷函数
def paginate_params(page: Any, page_size: Any) -> Dict[str, int]:
    """分页参数验证便捷函数"""
    return common_validators.validate_pagination_params(page, page_size)

def sort_params(sort_field: str, sort_order: str, allowed_fields: List[str]) -> Dict[str, str]:
    """排序参数验证便捷函数"""
    return common_validators.validate_sort_params(sort_field, sort_order, allowed_fields)

def handle_list_response(query_func: Callable, **kwargs) -> Dict[str, Any]:
    """列表响应处理便捷函数"""
    return common_response_handlers.handle_list_query(query_func, **kwargs)