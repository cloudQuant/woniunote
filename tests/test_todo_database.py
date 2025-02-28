import pytest
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from woniunote.common.create_database import Item, Category

# 测试配置
@pytest.fixture
def test_config():
    return {
        "SQLALCHEMY_DATABASE_URI": 'mysql+pymysql://testuser:testpass@localhost/test_woniunote',  # Using in-memory SQLite for testing
        'CATEGORY_NAMES': ["收件箱", "已完成", "购物清单", "工作清单", "学习清单", "写作清单"]
    }

# 创建测试用的 Flask 应用
@pytest.fixture
def test_app(test_config):
    # 创建新的 Flask 应用
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.urandom(24)
    
    # 配置数据库连接
    app.config['SQLALCHEMY_DATABASE_URI'] = test_config["SQLALCHEMY_DATABASE_URI"]
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_POOL_SIZE'] = 100
    
    # 返回配置好的应用
    return app

# 创建测试用的数据库连接和初始数据
@pytest.fixture
def test_db(test_app):
    # 创建新的 SQLAlchemy 实例
    db = SQLAlchemy(test_app)
    
    # 定义模型
    class TestItem(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        body = db.Column(db.Text)
        category_id = db.Column(
            db.Integer, db.ForeignKey('test_category.id'), default=1)

    class TestCategory(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(64))
        items = db.relationship('TestItem', backref='category')
    
    # 在应用上下文中创建表和初始数据
    with test_app.app_context():
        db.create_all()
        
        # 创建测试分类
        inbox = TestCategory(name=u'收件箱')
        done = TestCategory(name=u'已完成')
        shopping_list = TestCategory(name=u'购物清单')
        work_list = TestCategory(name=u'工作清单')
        
        # 创建测试项目
        item1 = TestItem(body=u'sleep 30min')
        item2 = TestItem(body=u'晒太阳')
        item3 = TestItem(body=u'写作练习30分钟')
        item4 = TestItem(body=u'3瓶牛奶', category=shopping_list)
        item5 = TestItem(body=u'5个苹果', category=shopping_list)
        item6 = TestItem(body=u'浇花', category=done)
        item7 = TestItem(body=u'done to do test', category=work_list)
        
        # 添加到数据库
        db.session.add_all([
            inbox, done, shopping_list, work_list,
            item1, item2, item3, item4, item5, item6, item7
        ])
        db.session.commit()
    
    yield db
    
    # 清理数据库
    with test_app.app_context():
        db.drop_all()

# 测试数据库初始化
def test_db_initialization(test_db, test_app):
    """测试数据库是否正确初始化"""
    with test_app.app_context():
        # 查询分类和项目
        categories = test_db.session.query(test_db.Model.metadata.tables['test_category']).all()
        items = test_db.session.query(test_db.Model.metadata.tables['test_item']).all()
        
        # 验证数据
        assert len(categories) == 4  # 初始化了4个分类
        assert len(items) == 7  # 初始化了7个项目

# 测试分类相关功能
def test_categories(test_db, test_app):
    """测试分类功能"""
    with test_app.app_context():
        # 获取所有分类
        categories_table = test_db.Model.metadata.tables['test_category']
        categories = test_db.session.query(categories_table).all()
        
        # 验证分类名称
        category_names = [category[1] for category in categories]  # 列1是name列
        assert '收件箱' in category_names
        assert '已完成' in category_names
        assert '购物清单' in category_names
        assert '工作清单' in category_names

# 测试项目相关功能
def test_items(test_db, test_app):
    """测试项目功能"""
    with test_app.app_context():
        # 获取所有项目
        items_table = test_db.Model.metadata.tables['test_item']
        items = test_db.session.query(items_table).all()
        
        # 验证项目内容
        item_bodies = [item[1] for item in items]  # 列1是body列
        assert 'sleep 30min' in item_bodies
        assert '晒太阳' in item_bodies
        assert '写作练习30分钟' in item_bodies
        assert '3瓶牛奶' in item_bodies
        assert '5个苹果' in item_bodies

# 测试分类和项目的关联关系
def test_category_item_relationship(test_db, test_app):
    """测试分类和项目的关联关系"""
    with test_app.app_context():
        # 查询购物清单分类
        category_table = test_db.Model.metadata.tables['test_category']
        shopping_list = test_db.session.query(category_table).filter_by(name='购物清单').first()
        shopping_list_id = shopping_list[0]  # 列0是id列
        
        # 查询该分类下的所有项目
        items_table = test_db.Model.metadata.tables['test_item']
        items = test_db.session.query(items_table).filter_by(category_id=shopping_list_id).all()
        
        # 验证项目数量和内容
        assert len(items) == 2  # 购物清单下有2个项目
        item_bodies = [item[1] for item in items]  # 列1是body列
        assert '3瓶牛奶' in item_bodies
        assert '5个苹果' in item_bodies

# 测试项目CRUD操作
def test_item_crud(test_db, test_app):
    """测试项目的增删改查操作"""
    with test_app.app_context():
        # 添加新项目
        items_table = test_db.Model.metadata.tables['test_item']
        category_table = test_db.Model.metadata.tables['test_category']
        
        # 查找学习清单分类ID（如果不存在则创建）
        study_list = test_db.session.query(category_table).filter_by(name='学习清单').first()
        if not study_list:
            result = test_db.session.execute(
                category_table.insert().values(name='学习清单')
            )
            test_db.session.commit()
            study_list_id = result.inserted_primary_key[0]
        else:
            study_list_id = study_list[0]
            
        # 添加新项目
        test_db.session.execute(
            items_table.insert().values(
                body='学习Python', 
                category_id=study_list_id
            )
        )
        test_db.session.commit()
        
        # 查询并验证添加的项目
        new_item = test_db.session.query(items_table).filter_by(body='学习Python').first()
        assert new_item is not None
        assert new_item[1] == '学习Python'  # 列1是body列
        assert new_item[2] == study_list_id  # 列2是category_id列
        
        # 更新项目
        test_db.session.execute(
            items_table.update().
            where(items_table.c.body == '学习Python').
            values(body='学习Python高级编程')
        )
        test_db.session.commit()
        
        # 查询并验证更新后的项目
        updated_item = test_db.session.query(items_table).filter_by(body='学习Python高级编程').first()
        assert updated_item is not None
        
        # 删除项目
        test_db.session.execute(
            items_table.delete().where(items_table.c.body == '学习Python高级编程')
        )
        test_db.session.commit()
        
        # 验证项目已删除
        deleted_item = test_db.session.query(items_table).filter_by(body='学习Python高级编程').first()
        assert deleted_item is None
