import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError


def test_db_connection():
    """测试数据库连接是否成功"""
    # 数据库 URI 配置
    SQLALCHEMY_DATABASE_URI = ("mysql://woniunote_user:Woniunote_password1!@localhost:3306/woniunote?"
                               "charset=utf8&autocommit=true")
    try:
        engine = create_engine(SQLALCHEMY_DATABASE_URI)
        # 尝试连接数据库
        with engine.connect() as connection:
            result = connection.execute(text("SELECT * from woniunote.users"))
            result = result.fetchall()
            assert len(result) > 0
    except OperationalError as e:
        pytest.fail(f"数据库连接失败：{e}")


if __name__ == "__main__":
    test_db_connection()
