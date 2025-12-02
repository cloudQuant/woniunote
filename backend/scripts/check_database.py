"""
使用后端配置检查数据库连接和表信息的脚本

用法（在项目根目录）：
    cd backend
    python -m scripts.check_database
"""

import asyncio
from typing import List, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


async def get_current_database(conn) -> str:
    result = await conn.execute(text("SELECT DATABASE()"))
    return result.scalar() or ""


async def get_tables(conn) -> List[str]:
    result = await conn.execute(text("SHOW TABLES"))
    return [row[0] for row in result.fetchall()]


async def get_table_count(conn, table: str) -> int:
    try:
        result = await conn.execute(text(f"SELECT COUNT(*) FROM `{table}`"))
        return int(result.scalar() or 0)
    except Exception:  # pragma: no cover - 仅用于手动检查
        return -1


async def inspect_database() -> None:
    print("=== WoniuNote 数据库检查脚本 ===")
    print(f"使用的 DATABASE_URL: {settings.DATABASE_URL}")
    print()

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )

    try:
        async with engine.connect() as conn:
            print("✅ 成功连接到数据库服务器")

            db_name = await get_current_database(conn)
            print(f"当前数据库: {db_name or '(未选择)'}")
            print()

            tables = await get_tables(conn)
            if not tables:
                print("⚠ 当前数据库中没有发现任何表")
            else:
                print(f"共发现 {len(tables)} 个数据表：")
                table_counts: List[Tuple[str, int]] = []
                for t in tables:
                    count = await get_table_count(conn, t)
                    table_counts.append((t, count))

                for name, count in table_counts:
                    if count >= 0:
                        print(f"  - {name}: {count} 行")
                    else:
                        print(f"  - {name}: (无法统计行数，可能没有权限或表有问题)")

    except Exception as e:  # pragma: no cover - 手工排查用
        print("❌ 数据库连接或查询失败：")
        print(repr(e))
    finally:
        await engine.dispose()


def main() -> None:
    asyncio.run(inspect_database())


if __name__ == "__main__":
    main()


