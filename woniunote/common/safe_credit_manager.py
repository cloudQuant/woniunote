"""
安全的积分管理模块
提供线程安全的积分操作和事务管理
"""
import time
import threading
from contextlib import contextmanager
from typing import Optional, Union
from sqlalchemy import text
from woniunote.common.database import dbconnect
from woniunote.common.unified_logging import get_simple_logger
from woniunote.common.unified_error_handler import handle_database_errors

logger = get_simple_logger('safe_credit_manager')

class SafeCreditManager:
    """安全积分管理器"""
    
    def __init__(self):
        self.lock = threading.RLock()  # 可重入锁
        dbsession, _, _ = dbconnect()
        self.dbsession = dbsession
    
    @contextmanager
    def transaction(self):
        """数据库事务上下文管理器"""
        try:
            yield self.dbsession
            self.dbsession.commit()
        except Exception:
            self.dbsession.rollback()
            raise
    
    @handle_database_errors(fallback_return=False)
    def update_credit_atomic(self, userid: Union[int, str], credit_change: int, 
                           reason: str = None, max_retries: int = 3) -> bool:
        """
        原子性更新用户积分
        
        Args:
            userid: 用户ID
            credit_change: 积分变化量（可为负数）
            reason: 积分变化原因
            max_retries: 最大重试次数
            
        Returns:
            bool: 更新是否成功
        """
        with self.lock:
            for attempt in range(max_retries):
                try:
                    with self.transaction():
                        # 使用行锁进行原子更新
                        update_sql = text("""
                            UPDATE users 
                            SET credit = credit + :credit_change,
                                updated_at = NOW()
                            WHERE userid = :userid
                            AND (credit + :credit_change) >= 0
                        """)
                        
                        result = self.dbsession.execute(update_sql, {
                            'userid': userid,
                            'credit_change': credit_change
                        })
                        
                        if result.rowcount == 0:
                            # 检查是否是因为积分不足
                            current_credit = self._get_user_credit(userid)
                            if current_credit is None:
                                logger.error("用户不存在", {'userid': userid})
                                return False
                            elif current_credit + credit_change < 0:
                                logger.warning("积分不足", {
                                    'userid': userid,
                                    'current_credit': current_credit,
                                    'credit_change': credit_change,
                                    'reason': reason
                                })
                                return False
                        
                        # 记录积分变化日志
                        self._log_credit_change(userid, credit_change, reason)
                        
                        logger.info("积分更新成功", {
                            'userid': userid,
                            'credit_change': credit_change,
                            'reason': reason,
                            'attempt': attempt + 1
                        })
                        
                        return True
                        
                except Exception as e:
                    logger.warning(f"积分更新失败，尝试 {attempt + 1}/{max_retries}", {
                        'userid': userid,
                        'credit_change': credit_change,
                        'error': str(e)
                    })
                    
                    if attempt == max_retries - 1:
                        raise
                    
                    # 短暂等待后重试
                    time.sleep(0.1 * (attempt + 1))
            
            return False
    
    def _get_user_credit(self, userid: Union[int, str]) -> Optional[int]:
        """获取用户当前积分"""
        try:
            result = self.dbsession.execute(
                text("SELECT credit FROM users WHERE userid = :userid"),
                {'userid': userid}
            ).fetchone()
            
            return result[0] if result else None
        except Exception as e:
            logger.error(f"获取用户积分失败: {e}", {'userid': userid})
            return None
    
    def _log_credit_change(self, userid: Union[int, str], credit_change: int, reason: str):
        """记录积分变化"""
        try:
            # 如果有积分变化日志表，在这里插入记录
            log_sql = text("""
                INSERT INTO credit_logs (userid, credit_change, reason, created_at)
                VALUES (:userid, :credit_change, :reason, NOW())
            """)
            
            self.dbsession.execute(log_sql, {
                'userid': userid,
                'credit_change': credit_change,
                'reason': reason or 'Unknown'
            })
            
        except Exception as e:
            # 积分日志失败不应影响积分更新
            logger.warning(f"积分日志记录失败: {e}", {
                'userid': userid,
                'credit_change': credit_change,
                'reason': reason
            })
    
    @handle_database_errors(fallback_return=None)
    def get_credit_with_lock(self, userid: Union[int, str]) -> Optional[int]:
        """
        使用锁获取用户积分（用于需要一致性的场景）
        
        Args:
            userid: 用户ID
            
        Returns:
            int: 用户积分，失败返回None
        """
        with self.lock:
            try:
                # 使用共享锁读取
                result = self.dbsession.execute(
                    text("SELECT credit FROM users WHERE userid = :userid LOCK IN SHARE MODE"),
                    {'userid': userid}
                ).fetchone()
                
                return result[0] if result else None
                
            except Exception as e:
                logger.error(f"获取用户积分失败: {e}", {'userid': userid})
                return None
    
    @handle_database_errors(fallback_return=False)
    def batch_update_credits(self, updates: list) -> bool:
        """
        批量更新积分
        
        Args:
            updates: 更新列表，每个元素为 (userid, credit_change, reason)
            
        Returns:
            bool: 是否全部更新成功
        """
        with self.lock:
            try:
                with self.transaction():
                    for userid, credit_change, reason in updates:
                        success = self.update_credit_atomic(userid, credit_change, reason, max_retries=1)
                        if not success:
                            logger.error("批量积分更新失败", {
                                'userid': userid,
                                'credit_change': credit_change,
                                'reason': reason
                            })
                            raise Exception(f"用户 {userid} 积分更新失败")
                    
                    logger.info("批量积分更新成功", {
                        'update_count': len(updates)
                    })
                    return True
                    
            except Exception as e:
                logger.error(f"批量积分更新异常: {e}")
                return False
    
    def validate_credit_operation(self, userid: Union[int, str], 
                                credit_change: int) -> tuple:
        """
        验证积分操作的合法性
        
        Args:
            userid: 用户ID
            credit_change: 积分变化量
            
        Returns:
            tuple: (是否有效, 错误信息)
        """
        # 验证用户ID
        try:
            userid = int(userid)
            if userid <= 0:
                return False, "无效的用户ID"
        except (ValueError, TypeError):
            return False, "用户ID必须为正整数"
        
        # 验证积分变化量
        try:
            credit_change = int(credit_change)
        except (ValueError, TypeError):
            return False, "积分变化量必须为整数"
        
        # 验证积分变化范围
        if abs(credit_change) > 10000:  # 单次变化不超过10000
            return False, "单次积分变化量过大"
        
        # 如果是扣分，检查当前积分是否足够
        if credit_change < 0:
            current_credit = self._get_user_credit(userid)
            if current_credit is None:
                return False, "用户不存在"
            if current_credit + credit_change < 0:
                return False, f"积分不足，当前积分: {current_credit}"
        
        return True, ""

# 全局积分管理器实例
credit_manager = SafeCreditManager()

# 便捷函数
def update_user_credit(userid: Union[int, str], credit_change: int, 
                      reason: str = None) -> bool:
    """便捷函数：更新用户积分"""
    return credit_manager.update_credit_atomic(userid, credit_change, reason)

def get_user_credit(userid: Union[int, str]) -> Optional[int]:
    """便捷函数：获取用户积分"""
    return credit_manager.get_credit_with_lock(userid)

def validate_credit_operation(userid: Union[int, str], 
                            credit_change: int) -> tuple:
    """便捷函数：验证积分操作"""
    return credit_manager.validate_credit_operation(userid, credit_change)