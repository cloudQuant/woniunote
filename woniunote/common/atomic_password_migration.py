#!/usr/bin/env python3
"""
原子密码迁移管理器
确保密码从MD5迁移到bcrypt时的事务原子性
"""

import time
import traceback
from typing import Optional, Tuple, Dict, Any
from contextlib import contextmanager
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from woniunote.common.db_connection_manager import get_db_session
from woniunote.common.secure_password import verify_password_with_migration, hash_password
from woniunote.common.unified_logging import get_simple_logger

logger = get_simple_logger('atomic_password_migration')

class AtomicPasswordMigration:
    """原子密码迁移管理器"""
    
    def __init__(self):
        self.migration_stats = {
            'total_attempts': 0,
            'successful_migrations': 0,
            'failed_migrations': 0,
            'already_migrated': 0
        }
    
    @contextmanager
    def migration_session(self, user_id: int, username: str):
        """
        密码迁移会话管理器，确保事务原子性
        
        Args:
            user_id: 用户ID
            username: 用户名
        """
        migration_start_time = time.time()
        migration_id = f"{user_id}_{int(migration_start_time)}"
        
        logger.info("开始密码迁移事务", {
            'migration_id': migration_id,
            'user_id': user_id,
            'username': username
        })
        
        session = None
        try:
            with get_db_session() as session:
                # 加行级锁防止并发修改
                user_record = session.execute(
                    text("SELECT userid, username, password, role, nickname FROM users WHERE userid = :user_id FOR UPDATE"),
                    {'user_id': user_id}
                ).fetchone()
                
                if not user_record:
                    logger.error("用户记录不存在", {
                        'migration_id': migration_id,
                        'user_id': user_id
                    })
                    raise ValueError(f"用户ID {user_id} 不存在")
                
                yield {
                    'session': session,
                    'user_record': user_record,
                    'migration_id': migration_id
                }
                
                # 如果到这里说明迁移成功
                logger.info("密码迁移事务提交成功", {
                    'migration_id': migration_id,
                    'user_id': user_id,
                    'duration_ms': round((time.time() - migration_start_time) * 1000, 2)
                })
                
        except SQLAlchemyError as e:
            logger.error("密码迁移数据库异常", {
                'migration_id': migration_id,
                'user_id': user_id,
                'error': str(e),
                'error_type': type(e).__name__
            })
            self.migration_stats['failed_migrations'] += 1
            raise
            
        except Exception as e:
            logger.error("密码迁移未知异常", {
                'migration_id': migration_id,
                'user_id': user_id,
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            self.migration_stats['failed_migrations'] += 1
            raise
    
    def verify_and_migrate_password(self, user_id: int, username: str, 
                                   provided_password: str, stored_hash: str) -> Tuple[bool, Dict[str, Any]]:
        """
        验证密码并进行原子迁移
        
        Args:
            user_id: 用户ID
            username: 用户名
            provided_password: 用户提供的密码
            stored_hash: 存储的密码哈希
            
        Returns:
            Tuple[bool, Dict]: (验证是否成功, 迁移信息)
        """
        self.migration_stats['total_attempts'] += 1
        
        # 首先验证密码
        is_valid, needs_migration, new_hash = verify_password_with_migration(
            provided_password, stored_hash
        )
        
        if not is_valid:
            return False, {'migrated': False, 'reason': 'invalid_password'}
        
        # 如果不需要迁移，直接返回成功
        if not needs_migration:
            self.migration_stats['already_migrated'] += 1
            return True, {'migrated': False, 'reason': 'already_modern_hash'}
        
        # 需要迁移，进行原子迁移操作
        try:
            with self.migration_session(user_id, username) as migration_context:
                session = migration_context['session']
                user_record = migration_context['user_record']
                migration_id = migration_context['migration_id']
                
                # 再次检查密码是否仍然需要迁移（防止并发迁移）
                current_stored_hash = user_record[2]  # password字段
                current_is_valid, current_needs_migration, current_new_hash = verify_password_with_migration(
                    provided_password, current_stored_hash
                )
                
                if not current_is_valid:
                    logger.error("迁移过程中密码验证失败", {
                        'migration_id': migration_id,
                        'user_id': user_id
                    })
                    return False, {'migrated': False, 'reason': 'password_changed_during_migration'}
                
                if not current_needs_migration:
                    logger.info("密码已被其他进程迁移", {
                        'migration_id': migration_id,
                        'user_id': user_id
                    })
                    self.migration_stats['already_migrated'] += 1
                    return True, {'migrated': False, 'reason': 'already_migrated_by_other_process'}
                
                # 执行原子密码更新
                update_result = session.execute(
                    text("UPDATE users SET password = :new_password, updatetime = NOW() WHERE userid = :user_id AND password = :old_password"),
                    {'new_password': current_new_hash, 'user_id': user_id, 'old_password': current_stored_hash}
                )
                
                if update_result.rowcount != 1:
                    logger.error("密码更新失败，可能被并发修改", {
                        'migration_id': migration_id,
                        'user_id': user_id,
                        'affected_rows': update_result.rowcount
                    })
                    raise ValueError("密码更新失败，可能存在并发冲突")
                
                # 验证迁移结果
                verification_result = session.execute(
                    text("SELECT password FROM users WHERE userid = :user_id"),
                    {'user_id': user_id}
                ).fetchone()
                
                if not verification_result or verification_result[0] != current_new_hash:
                    logger.error("密码迁移验证失败", {
                        'migration_id': migration_id,
                        'user_id': user_id
                    })
                    raise ValueError("密码迁移验证失败")
                
                self.migration_stats['successful_migrations'] += 1
                
                logger.info("密码迁移成功", {
                    'migration_id': migration_id,
                    'user_id': user_id,
                    'username': username,
                    'old_hash_type': 'MD5',
                    'new_hash_type': 'bcrypt'
                })
                
                return True, {
                    'migrated': True,
                    'migration_id': migration_id,
                    'old_hash_type': 'MD5',
                    'new_hash_type': 'bcrypt'
                }
                
        except Exception as e:
            logger.error("密码迁移异常", {
                'user_id': user_id,
                'username': username,
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            return False, {'migrated': False, 'reason': f'migration_error: {str(e)}'}
    
    def batch_migrate_passwords(self, user_batch_size: int = 100) -> Dict[str, Any]:
        """
        批量迁移密码（管理员功能）
        
        Args:
            user_batch_size: 批处理大小
            
        Returns:
            Dict: 迁移统计信息
        """
        batch_stats = {
            'total_users_processed': 0,
            'migrations_attempted': 0,
            'migrations_successful': 0,
            'migrations_failed': 0,
            'already_migrated': 0,
            'start_time': time.time()
        }
        
        try:
            with get_db_session() as session:
                # 查找需要迁移的用户（MD5哈希长度通常为32字符）
                users_to_migrate = session.execute(
                    text("SELECT userid, username, password FROM users WHERE LENGTH(password) = 32 LIMIT :batch_size"),
                    {'batch_size': user_batch_size}
                ).fetchall()
                
                batch_stats['total_users_processed'] = len(users_to_migrate)
                
                logger.info("开始批量密码迁移", {
                    'total_users': len(users_to_migrate),
                    'batch_size': user_batch_size
                })
                
                for user_record in users_to_migrate:
                    user_id, username, password_hash = user_record
                    
                    try:
                        # 注意：批量迁移不能验证明文密码，只能标记需要在下次登录时迁移
                        # 这里我们创建一个迁移标记而不是实际迁移密码
                        session.execute(
                            text("UPDATE users SET migration_pending = TRUE WHERE userid = :user_id"),
                            {'user_id': user_id}
                        )
                        
                        batch_stats['migrations_successful'] += 1
                        
                        logger.debug("标记用户需要密码迁移", {
                            'user_id': user_id,
                            'username': username
                        })
                        
                    except Exception as e:
                        batch_stats['migrations_failed'] += 1
                        logger.error("标记用户迁移失败", {
                            'user_id': user_id,
                            'username': username,
                            'error': str(e)
                        })
                
                batch_stats['duration_seconds'] = time.time() - batch_stats['start_time']
                
                logger.info("批量密码迁移完成", batch_stats)
                
                return batch_stats
                
        except Exception as e:
            logger.error("批量密码迁移异常", {
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            return {**batch_stats, 'error': str(e)}
    
    def get_migration_stats(self) -> Dict[str, Any]:
        """获取迁移统计信息"""
        return {
            **self.migration_stats,
            'success_rate': (
                self.migration_stats['successful_migrations'] / 
                max(self.migration_stats['total_attempts'], 1)
            ) * 100
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.migration_stats = {
            'total_attempts': 0,
            'successful_migrations': 0,
            'failed_migrations': 0,
            'already_migrated': 0
        }

# 全局实例
atomic_password_migration = AtomicPasswordMigration()

# 便捷函数
def verify_and_migrate_user_password(user_id: int, username: str, 
                                    provided_password: str, stored_hash: str) -> Tuple[bool, Dict[str, Any]]:
    """便捷函数：验证并迁移用户密码"""
    return atomic_password_migration.verify_and_migrate_password(
        user_id, username, provided_password, stored_hash
    )

def get_password_migration_stats() -> Dict[str, Any]:
    """便捷函数：获取密码迁移统计"""
    return atomic_password_migration.get_migration_stats()