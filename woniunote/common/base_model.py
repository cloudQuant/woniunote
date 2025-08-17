"""
基础数据访问类
统一数据库连接和基础查询操作，减少重复代码
集成资源管理和会话管理，防止内存泄露
"""
import traceback
from typing import Any, Dict, List, Optional, Type, Union
from functools import wraps
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .database import db
from .simple_logger import get_simple_logger
from .trace_id_manager import TraceIdManager
from .error_handler import DatabaseException
from .session_manager import SessionManager, safe_database_operation
from .resource_manager import resource_monitor
from .memory_monitor import track_object, untrack_object

class BaseModel:
    """基础数据访问类"""
    
    def __init__(self, model_name: str = None):
        """
        初始化基础模型
        
        Args:
            model_name: 模型名称，用于日志记录
        """
        self.model_name = model_name or self.__class__.__name__
        self.logger = get_simple_logger(f'{self.model_name.lower()}_model')
        self.session = db.session
        
        # 初始化会话管理器
        self.session_manager = SessionManager(self.session)
        
        # 跟踪模型实例
        track_object(self, f'model_{self.model_name.lower()}')
    
    def __del__(self):
        """析构函数 - 确保资源清理"""
        try:
            untrack_object(self, f'model_{self.model_name.lower()}')
        except:
            pass  # 避免析构器异常
    
    def _generate_trace_id(self) -> str:
        """生成跟踪ID"""
        return TraceIdManager.generate_trace_id(self.model_name.lower())
    
    def _log_operation(self, operation: str, trace_id: str, **kwargs):
        """记录操作日志"""
        log_data = {
            'trace_id': trace_id,
            'operation': operation,
            'model': self.model_name,
            **kwargs
        }
        self.logger.info(f"{self.model_name} {operation}", log_data)
    
    def _log_error(self, operation: str, trace_id: str, error: Exception, **kwargs):
        """记录错误日志"""
        log_data = {
            'trace_id': trace_id,
            'operation': operation,
            'model': self.model_name,
            'error': str(error),
            'error_type': type(error).__name__,
            **kwargs
        }
        self.logger.error(f"{self.model_name} {operation} 失败", log_data)
    
    @safe_database_operation('find_by_id')
    @resource_monitor('database_query')
    def find_by_id(self, model_class: Type, entity_id: Any) -> Optional[Any]:
        """
        根据ID查找实体
        
        Args:
            model_class: SQLAlchemy模型类
            entity_id: 实体ID
            
        Returns:
            实体对象或None
        """
        trace_id = self._generate_trace_id()
        
        with self.session_manager.managed_session(trace_id, 'find_by_id') as session:
            self._log_operation('find_by_id', trace_id, entity_id=entity_id)
            
            result = session.query(model_class).filter(
                model_class.id == entity_id
            ).first()
            
            if result:
                self._log_operation('find_by_id_success', trace_id, 
                                  entity_id=entity_id, found=True)
                # 跟踪查询结果
                track_object(result, f'{model_class.__name__}_entity')
            else:
                self._log_operation('find_by_id_not_found', trace_id,
                                  entity_id=entity_id, found=False)
            
            return result
    
    def find_by_field(self, model_class: Type, field_name: str, 
                     field_value: Any, first_only: bool = True) -> Union[Any, List[Any], None]:
        """
        根据字段查找实体
        
        Args:
            model_class: SQLAlchemy模型类
            field_name: 字段名
            field_value: 字段值
            first_only: 是否只返回第一个结果
            
        Returns:
            实体对象、实体列表或None
        """
        trace_id = self._generate_trace_id()
        
        try:
            self._log_operation('find_by_field', trace_id, 
                              field_name=field_name, field_value=field_value,
                              first_only=first_only)
            
            query = self.session.query(model_class).filter(
                getattr(model_class, field_name) == field_value
            )
            
            if first_only:
                result = query.first()
                found = result is not None
            else:
                result = query.all()
                found = len(result) > 0
            
            self._log_operation('find_by_field_success', trace_id,
                              field_name=field_name, field_value=field_value,
                              found=found, count=len(result) if isinstance(result, list) else (1 if result else 0))
            
            return result
            
        except SQLAlchemyError as e:
            self._log_error('find_by_field', trace_id, e,
                          field_name=field_name, field_value=field_value)
            raise DatabaseException(
                f"根据{field_name}查找{self.model_name}失败",
                operation='find_by_field',
                details={'field_name': field_name, 'field_value': field_value, 'error': str(e)}
            )
    
    def find_by_conditions(self, model_class: Type, conditions: Dict[str, Any],
                          limit: int = None, offset: int = None) -> List[Any]:
        """
        根据多个条件查找实体
        
        Args:
            model_class: SQLAlchemy模型类
            conditions: 查询条件字典
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            实体列表
        """
        trace_id = self._generate_trace_id()
        
        try:
            self._log_operation('find_by_conditions', trace_id,
                              conditions=conditions, limit=limit, offset=offset)
            
            query = self.session.query(model_class)
            
            # 应用查询条件
            for field_name, field_value in conditions.items():
                if hasattr(model_class, field_name):
                    query = query.filter(getattr(model_class, field_name) == field_value)
            
            # 应用限制和偏移
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            result = query.all()
            
            self._log_operation('find_by_conditions_success', trace_id,
                              conditions=conditions, count=len(result))
            
            return result
            
        except SQLAlchemyError as e:
            self._log_error('find_by_conditions', trace_id, e, conditions=conditions)
            raise DatabaseException(
                f"根据条件查找{self.model_name}失败",
                operation='find_by_conditions',
                details={'conditions': conditions, 'error': str(e)}
            )
    
    def create(self, model_class: Type, data: Dict[str, Any]) -> Any:
        """
        创建新实体
        
        Args:
            model_class: SQLAlchemy模型类
            data: 实体数据
            
        Returns:
            创建的实体对象
        """
        trace_id = self._generate_trace_id()
        
        try:
            self._log_operation('create', trace_id, data_keys=list(data.keys()))
            
            # 创建实体
            entity = model_class(**data)
            self.session.add(entity)
            self.session.commit()
            
            self._log_operation('create_success', trace_id, entity_id=getattr(entity, 'id', None))
            
            return entity
            
        except SQLAlchemyError as e:
            self.session.rollback()
            self._log_error('create', trace_id, e, data_keys=list(data.keys()))
            raise DatabaseException(
                f"创建{self.model_name}失败",
                operation='create',
                details={'data': data, 'error': str(e)}
            )
    
    def update_by_id(self, model_class: Type, entity_id: Any, data: Dict[str, Any]) -> bool:
        """
        根据ID更新实体
        
        Args:
            model_class: SQLAlchemy模型类
            entity_id: 实体ID
            data: 更新数据
            
        Returns:
            是否更新成功
        """
        trace_id = self._generate_trace_id()
        
        try:
            self._log_operation('update_by_id', trace_id,
                              entity_id=entity_id, data_keys=list(data.keys()))
            
            # 查找实体
            entity = self.session.query(model_class).filter(
                model_class.id == entity_id
            ).first()
            
            if not entity:
                self._log_operation('update_by_id_not_found', trace_id, entity_id=entity_id)
                return False
            
            # 更新字段
            for field_name, field_value in data.items():
                if hasattr(entity, field_name):
                    setattr(entity, field_name, field_value)
            
            self.session.commit()
            
            self._log_operation('update_by_id_success', trace_id, entity_id=entity_id)
            
            return True
            
        except SQLAlchemyError as e:
            self.session.rollback()
            self._log_error('update_by_id', trace_id, e,
                          entity_id=entity_id, data_keys=list(data.keys()))
            raise DatabaseException(
                f"更新{self.model_name}失败",
                operation='update_by_id',
                details={'entity_id': entity_id, 'data': data, 'error': str(e)}
            )
    
    def delete_by_id(self, model_class: Type, entity_id: Any) -> bool:
        """
        根据ID删除实体
        
        Args:
            model_class: SQLAlchemy模型类
            entity_id: 实体ID
            
        Returns:
            是否删除成功
        """
        trace_id = self._generate_trace_id()
        
        try:
            self._log_operation('delete_by_id', trace_id, entity_id=entity_id)
            
            # 查找并删除实体
            entity = self.session.query(model_class).filter(
                model_class.id == entity_id
            ).first()
            
            if not entity:
                self._log_operation('delete_by_id_not_found', trace_id, entity_id=entity_id)
                return False
            
            self.session.delete(entity)
            self.session.commit()
            
            self._log_operation('delete_by_id_success', trace_id, entity_id=entity_id)
            
            return True
            
        except SQLAlchemyError as e:
            self.session.rollback()
            self._log_error('delete_by_id', trace_id, e, entity_id=entity_id)
            raise DatabaseException(
                f"删除{self.model_name}失败",
                operation='delete_by_id',
                details={'entity_id': entity_id, 'error': str(e)}
            )
    
    def count(self, model_class: Type, conditions: Dict[str, Any] = None) -> int:
        """
        统计实体数量
        
        Args:
            model_class: SQLAlchemy模型类
            conditions: 查询条件（可选）
            
        Returns:
            实体数量
        """
        trace_id = self._generate_trace_id()
        
        try:
            self._log_operation('count', trace_id, conditions=conditions)
            
            query = self.session.query(model_class)
            
            # 应用查询条件
            if conditions:
                for field_name, field_value in conditions.items():
                    if hasattr(model_class, field_name):
                        query = query.filter(getattr(model_class, field_name) == field_value)
            
            count = query.count()
            
            self._log_operation('count_success', trace_id, count=count)
            
            return count
            
        except SQLAlchemyError as e:
            self._log_error('count', trace_id, e, conditions=conditions)
            raise DatabaseException(
                f"统计{self.model_name}数量失败",
                operation='count',
                details={'conditions': conditions, 'error': str(e)}
            )
    
    def execute_raw_query(self, sql: str, params: Dict[str, Any] = None) -> List[Dict]:
        """
        执行原生SQL查询
        
        Args:
            sql: SQL语句
            params: 查询参数
            
        Returns:
            查询结果列表
        """
        trace_id = self._generate_trace_id()
        
        try:
            self._log_operation('execute_raw_query', trace_id, 
                              sql_length=len(sql), has_params=bool(params))
            
            result = self.session.execute(sql, params or {})
            
            # 转换为字典列表
            columns = result.keys()
            rows = []
            for row in result:
                rows.append(dict(zip(columns, row)))
            
            self._log_operation('execute_raw_query_success', trace_id, row_count=len(rows))
            
            return rows
            
        except SQLAlchemyError as e:
            self._log_error('execute_raw_query', trace_id, e, sql_length=len(sql))
            raise DatabaseException(
                f"执行原生SQL查询失败",
                operation='execute_raw_query',
                details={'sql': sql[:100] + '...' if len(sql) > 100 else sql, 'error': str(e)}
            )

def database_operation(operation_name: str = None):
    """数据库操作装饰器，统一错误处理"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            op_name = operation_name or func.__name__
            trace_id = self._generate_trace_id() if hasattr(self, '_generate_trace_id') else TraceIdManager.generate_simple_trace_id()
            
            try:
                if hasattr(self, '_log_operation'):
                    self._log_operation(f'{op_name}_start', trace_id)
                
                result = func(self, *args, **kwargs)
                
                if hasattr(self, '_log_operation'):
                    self._log_operation(f'{op_name}_success', trace_id)
                
                return result
                
            except Exception as e:
                if hasattr(self, 'session'):
                    try:
                        self.session.rollback()
                    except:
                        pass
                
                if hasattr(self, '_log_error'):
                    self._log_error(op_name, trace_id, e)
                
                if isinstance(e, DatabaseException):
                    raise
                else:
                    raise DatabaseException(
                        f"数据库操作失败: {op_name}",
                        operation=op_name,
                        details={'error': str(e)}
                    )
        
        return wrapper
    return decorator

# 创建全局基础模型实例
base_model = BaseModel('global')