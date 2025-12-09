"""
Redis 连接管理模块

本模块负责管理 Redis 连接，提供单例模式的连接管理器。
"""
import redis.asyncio as redis
from typing import Optional
from app.core.config import settings


class RedisManager:
    """
    Redis 连接管理器
    
    使用单例模式管理 Redis 连接池。
    """
    _instance: Optional["RedisManager"] = None
    _redis: Optional[redis.Redis] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(self):
        """
        建立 Redis 连接
        
        如果连接已存在，则直接返回。
        
        Returns:
            redis.Redis: Redis 客户端实例
        """
        if self._redis is None:
            self._redis = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis
    
    async def disconnect(self):
        """
        断开 Redis 连接
        
        关闭连接池并释放资源。
        """
        if self._redis:
            await self._redis.close()
            self._redis = None
    
    @property
    def client(self) -> Optional[redis.Redis]:
        """
        获取 Redis 客户端
        
        Returns:
            Optional[redis.Redis]: Redis 客户端实例，如果未连接则为 None
        """
        return self._redis


redis_manager = RedisManager()


async def get_redis() -> redis.Redis:
    """
    获取 Redis 客户端的依赖项
    
    用于 FastAPI 的 Depends 注入。
    
    Returns:
        redis.Redis: Redis 客户端实例
    """
    return await redis_manager.connect()
