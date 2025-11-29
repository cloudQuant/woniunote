"""
Redis 连接管理
"""
import redis.asyncio as redis
from typing import Optional
from app.core.config import settings


class RedisManager:
    """Redis连接管理器"""
    _instance: Optional["RedisManager"] = None
    _redis: Optional[redis.Redis] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(self):
        """建立Redis连接"""
        if self._redis is None:
            self._redis = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis
    
    async def disconnect(self):
        """断开Redis连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None
    
    @property
    def client(self) -> Optional[redis.Redis]:
        return self._redis


redis_manager = RedisManager()


async def get_redis() -> redis.Redis:
    """获取Redis客户端的依赖项"""
    return await redis_manager.connect()
