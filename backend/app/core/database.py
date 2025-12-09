"""
数据库配置模块

本模块负责配置 SQLAlchemy 异步数据库连接，创建会话工厂，并提供获取数据库会话的依赖项。
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


# 创建异步引擎
# echo=settings.DEBUG: 在调试模式下打印 SQL 语句
# pool_pre_ping=True: 每次从连接池获取连接前进行有效性检查
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


class Base(DeclarativeBase):
    """
    SQLAlchemy 声明式基类
    
    所有数据库模型都应继承此类。
    """
    pass


async def get_db() -> AsyncSession:
    """
    获取数据库会话的依赖项
    
    用于 FastAPI 的 Depends 注入。
    
    Yields:
        AsyncSession: 数据库会话对象
        
    Note:
        事务管理由业务代码负责：
        - 业务代码需要显式调用 await db.commit() 提交
        - 发生异常时会自动回滚
        - 会话会在 finally 块中自动关闭
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
