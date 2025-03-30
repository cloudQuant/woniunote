"""
初始化WoniuNote测试数据库
从test_config.yaml读取数据库配置并创建所需的表结构和基础数据，
使用与woniunote/common/create_database.py相同的表结构
"""
import os
import sys
import yaml
import hashlib
import datetime
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# 设置项目根目录
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

print("初始化WoniuNote测试数据库...")

# 读取配置文件
config_path = os.path.join(project_root, 'configs', 'test_config.yaml')
with open(config_path, 'r', encoding='utf-8') as file:
    config = yaml.safe_load(file)

# 获取数据库连接URI
db_uri = config['database']['SQLALCHEMY_DATABASE_URI']
print(f"数据库连接URI: {db_uri}")

# 创建数据库引擎
engine = create_engine(db_uri)

# 创建基类
Base = declarative_base()

# 定义与create_database.py完全匹配的模型类
class User(Base):
    __tablename__ = 'users'
    
    userid = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    username = Column(String(50), nullable=False)
    password = Column(String(32), nullable=False)
    nickname = Column(String(30))
    avatar = Column(String(20))
    qq = Column(String(15))
    role = Column(String(10), nullable=False)
    credit = Column(Integer, default=50)
    createtime = Column(DateTime, default=datetime.datetime.now)
    updatetime = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    
    def __repr__(self):
        return f"<User(userid={self.userid}, username='{self.username}', role='{self.role}')>"


class Article(Base):
    __tablename__ = 'article'
    
    articleid = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    userid = Column(Integer, ForeignKey("users.userid"), nullable=False)
    type = Column(Integer, nullable=False)  # 注意: 使用Integer类型
    headline = Column(String(100), nullable=False)  # 注意: 使用headline而非title
    content = Column(Text(16777216))
    thumbnail = Column(String(30))
    credit = Column(Integer, default=0)
    readcount = Column(Integer, default=0)
    replycount = Column(Integer, default=0)
    recommended = Column(Integer, default=0)
    hidden = Column(Integer, default=0)
    drafted = Column(Integer, default=0)
    checked = Column(Integer, default=1)
    createtime = Column(DateTime, default=datetime.datetime.now)
    updatetime = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    
    def __repr__(self):
        return f"<Article(articleid={self.articleid}, headline='{self.headline}')>"


class Comment(Base):
    __tablename__ = 'comment'
    
    commentid = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    userid = Column(Integer, ForeignKey("users.userid"), nullable=False)
    articleid = Column(Integer, ForeignKey("article.articleid"), nullable=False)
    content = Column(Text(65536), nullable=False)
    ipaddr = Column(String(30))
    replyid = Column(Integer)
    agreecount = Column(Integer, default=0)
    opposecount = Column(Integer, default=0)
    hidden = Column(Integer, default=0)
    createtime = Column(DateTime, default=datetime.datetime.now)
    updatetime = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    
    def __repr__(self):
        return f"<Comment(commentid={self.commentid}, articleid={self.articleid}, userid={self.userid})>"


class Favorite(Base):
    __tablename__ = 'favorite'
    
    favoriteid = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    userid = Column(Integer, ForeignKey("users.userid"), nullable=False)
    articleid = Column(Integer, ForeignKey("article.articleid"), nullable=False)
    canceled = Column(Integer, default=0)
    createtime = Column(DateTime, default=datetime.datetime.now)
    updatetime = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    
    def __repr__(self):
        return f"<Favorite(favoriteid={self.favoriteid}, articleid={self.articleid}, userid={self.userid})>"


class Credit(Base):
    __tablename__ = 'credit'
    
    creditid = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    userid = Column(Integer, ForeignKey("users.userid"), nullable=False)
    category = Column(String(10))
    target = Column(Integer)
    credit = Column(Integer)
    createtime = Column(DateTime, default=datetime.datetime.now)
    updatetime = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    
    def __repr__(self):
        return f"<Credit(creditid={self.creditid}, userid={self.userid}, category='{self.category}')>"


class Category(Base):
    __tablename__ = 'category'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(64))
    
    items = relationship('Item', backref='category')
    
    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"


class Item(Base):
    __tablename__ = 'item'
    
    id = Column(Integer, primary_key=True)
    body = Column(Text)
    category_id = Column(Integer, ForeignKey('category.id'), default=1)
    
    def __repr__(self):
        return f"<Item(id={self.id}, category_id={self.category_id})>"


class CardCategory(Base):
    __tablename__ = 'cardcategory'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(64))
    
    cards = relationship('Card', backref='cardcategory')
    
    def __repr__(self):
        return f"<CardCategory(id={self.id}, name='{self.name}')>"


class Card(Base):
    __tablename__ = 'card'
    
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    type = Column(Integer, default=1)
    headline = Column(Text(200), nullable=False)
    content = Column(Text(16777216), default="")
    createtime = Column(DateTime, default=datetime.datetime.now)
    updatetime = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    donetime = Column(DateTime)
    usedtime = Column(Integer, default=0)
    begintime = Column(DateTime)
    endtime = Column(DateTime)
    cardcategory_id = Column(Integer, ForeignKey('cardcategory.id'), default=1)
    
    def __repr__(self):
        return f"<Card(id={self.id}, headline='{self.headline}')>"


# 创建数据库表
def create_tables():
    """创建所有表"""
    try:
        print("尝试创建数据库表...")
        Base.metadata.create_all(engine)
        print("✅ 数据库表创建成功")
        return True
    except Exception as e:
        print(f"❌ 创建数据库表失败: {e}")
        return False


# 添加测试数据
def add_test_data():
    """添加基础测试数据"""
    # 创建会话
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("添加测试数据...")
        
        # 添加用户
        admin_user = User(
            username='admin@example.com',
            password='e10adc3949ba59abbe56e057f20f883e',  # MD5 of '123456'
            nickname='管理员',
            avatar='avatar1.jpg',
            qq='12345678',
            role='admin',
            credit=500
        )
        
        editor_user = User(
            username='editor@example.com',
            password='e10adc3949ba59abbe56e057f20f883e',  # MD5 of '123456'
            nickname='编辑',
            avatar='avatar2.jpg',
            qq='87654321',
            role='editor',
            credit=300
        )
        
        regular_user = User(
            username='user@example.com',
            password='e10adc3949ba59abbe56e057f20f883e',  # MD5 of '123456'
            nickname='普通用户',
            avatar='avatar3.jpg',
            qq='98765432',
            role='user',
            credit=100
        )
        
        session.add_all([admin_user, editor_user, regular_user])
        session.commit()
        print("✅ 用户数据添加成功")
        
        # 添加文章
        admin_article = Article(
            userid=admin_user.userid,
            headline='管理员测试文章',
            content='这是管理员发布的测试文章内容，用于测试数据库功能。',
            type=2,  # 使用整数类型
            thumbnail='thumb1.jpg',
            readcount=10,
            replycount=1
        )
        
        editor_article = Article(
            userid=editor_user.userid,
            headline='编辑测试文章',
            content='这是编辑发布的测试文章内容，用于测试数据库功能。',
            type=1,  # 使用整数类型
            thumbnail='thumb2.jpg',
            readcount=5,
            replycount=1
        )
        
        user_article = Article(
            userid=regular_user.userid,
            headline='普通用户测试文章',
            content='这是普通用户发布的测试文章内容，用于测试数据库功能。',
            type=1,  # 使用整数类型
            thumbnail='thumb3.jpg',
            readcount=2,
            replycount=1
        )
        
        session.add_all([admin_article, editor_article, user_article])
        session.commit()
        print("✅ 文章数据添加成功")
        
        # 添加评论
        admin_comment = Comment(
            articleid=user_article.articleid,
            userid=admin_user.userid,
            content='这是管理员对普通用户文章的评论。',
            ipaddr='127.0.0.1',
            agreecount=2,
            opposecount=0
        )
        
        editor_comment = Comment(
            articleid=admin_article.articleid,
            userid=editor_user.userid,
            content='这是编辑对管理员文章的评论。',
            ipaddr='127.0.0.1',
            agreecount=1,
            opposecount=0
        )
        
        user_comment = Comment(
            articleid=editor_article.articleid,
            userid=regular_user.userid,
            content='这是普通用户对编辑文章的评论。',
            ipaddr='127.0.0.1',
            agreecount=0,
            opposecount=0
        )
        
        session.add_all([admin_comment, editor_comment, user_comment])
        session.commit()
        print("✅ 评论数据添加成功")
        
        # 添加收藏
        user_favorite1 = Favorite(
            articleid=admin_article.articleid,
            userid=regular_user.userid,
            canceled=0
        )
        
        user_favorite2 = Favorite(
            articleid=editor_article.articleid,
            userid=regular_user.userid,
            canceled=0
        )
        
        editor_favorite = Favorite(
            articleid=admin_article.articleid,
            userid=editor_user.userid,
            canceled=0
        )
        
        session.add_all([user_favorite1, user_favorite2, editor_favorite])
        session.commit()
        print("✅ 收藏数据添加成功")
        
        # 添加积分记录
        user_credit = Credit(
            userid=regular_user.userid,
            category='post',
            target=user_article.articleid,
            credit=5
        )
        
        editor_credit = Credit(
            userid=editor_user.userid,
            category='post',
            target=editor_article.articleid,
            credit=5
        )
        
        session.add_all([user_credit, editor_credit])
        session.commit()
        print("✅ 积分数据添加成功")
        
        # 添加分类数据
        category1 = Category(name='默认分类')
        category2 = Category(name='学习笔记')
        category3 = Category(name='生活随笔')
        
        session.add_all([category1, category2, category3])
        session.commit()
        
        # 添加项目数据
        item1 = Item(body='测试项目1', category_id=category1.id)
        item2 = Item(body='学习笔记项目', category_id=category2.id)
        item3 = Item(body='生活随笔项目', category_id=category3.id)
        
        session.add_all([item1, item2, item3])
        session.commit()
        print("✅ 分类和项目数据添加成功")
        
        # 添加卡片分类
        card_category1 = CardCategory(name='默认卡片分类')
        card_category2 = CardCategory(name='工作')
        card_category3 = CardCategory(name='生活')
        
        session.add_all([card_category1, card_category2, card_category3])
        session.commit()
        
        # 添加卡片数据
        now = datetime.datetime.now()
        tomorrow = now + datetime.timedelta(days=1)
        next_week = now + datetime.timedelta(days=7)
        
        card1 = Card(
            headline='测试卡片1',
            content='这是测试卡片1的内容',
            type=1,
            begintime=now,
            endtime=tomorrow,
            cardcategory_id=card_category1.id
        )
        
        card2 = Card(
            headline='工作安排',
            content='完成项目进度报告',
            type=2,
            begintime=now,
            endtime=next_week,
            cardcategory_id=card_category2.id
        )
        
        card3 = Card(
            headline='生活计划',
            content='周末购物清单',
            type=3,
            begintime=now,
            endtime=next_week,
            cardcategory_id=card_category3.id
        )
        
        session.add_all([card1, card2, card3])
        session.commit()
        print("✅ 卡片分类和卡片数据添加成功")
        
        return True
    except Exception as e:
        print(f"❌ 添加测试数据失败: {e}")
        session.rollback()
        return False
    finally:
        session.close()


# 主函数
def main():
    """主函数"""
    # 创建表
    if not create_tables():
        return 1
    
    # 添加测试数据
    if not add_test_data():
        return 1
    
    print("\n✅ 数据库初始化完成！")
    return 0


if __name__ == "__main__":
    sys.exit(main())
