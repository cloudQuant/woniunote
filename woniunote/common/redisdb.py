from datetime import datetime
import re
import os
import redis
from woniunote.common.database import dbconnect
from woniunote.common.utils import model_list
from woniunote.module.articles import Article
from woniunote.module.users import Users


def redis_connect():
    try:
        from flask import current_app
        if current_app and 'redis_client' in current_app.extensions:
            return current_app.extensions['redis_client']
        cfg = getattr(current_app, 'config', {})
        url = cfg.get('REDIS_URL') or os.getenv('REDIS_URL')
        host = cfg.get('REDIS_HOST') or os.getenv('REDIS_HOST', '127.0.0.1')
        port = int(cfg.get('REDIS_PORT') or os.getenv('REDIS_PORT', '6379'))
        dbnum = int(cfg.get('REDIS_DB') or os.getenv('REDIS_DB', '0'))
        password = cfg.get('REDIS_PASSWORD') or os.getenv('REDIS_PASSWORD')
    except Exception:
        url = os.getenv('REDIS_URL')
        host = os.getenv('REDIS_HOST', '127.0.0.1')
        port = int(os.getenv('REDIS_PORT', '6379'))
        dbnum = int(os.getenv('REDIS_DB', '0'))
        password = os.getenv('REDIS_PASSWORD')
    try:
        if url:
            red = redis.from_url(url, decode_responses=True)
            red.ping()
            return red
        pool_kwargs = {'host': host, 'port': port, 'db': dbnum, 'decode_responses': True}
        if password:
            pool_kwargs['password'] = password
        pool = redis.ConnectionPool(**pool_kwargs)
        red = redis.Redis(connection_pool=pool)
        red.ping()
        return red
    except Exception:
        return None


# def redis_mysql_string():
#     from common.database import dbconnect
#
#     red = redis_connect()  # 连接到Redis服务器
#
#     # 获取数据库连接信息
#     dbsession, md, db_base = dbconnect()
#
#     # 查询users表的所有数据，并将其转换为JSON
#     result = dbsession.query(Users).all()
#     json = model_list(result)
#
#     red.set('users', str(json))  # 将整张表的数据保存成JSON字符串


def redis_mysql_string():
    from woniunote.common.database import dbconnect

    red = redis_connect()
    if red is None:
        return

    dbsession, md, db_base = dbconnect()

    result = dbsession.query(Users).all()
    user_list = model_list(result)
    for user in user_list:
        red.set(user['username'], user['password'])


def redis_mysql_hash():
    from woniunote.common.database import dbconnect

    red = redis_connect()
    if red is None:
        return

    dbsession, md, db_base = dbconnect()

    result = dbsession.query(Users).all()
    user_list = model_list(result)
    for user in user_list:
        red.hset('users_hash', user['username'], str(user))


def redis_article_zsort():
    dbsession, md, db_base = dbconnect()
    result = dbsession.query(Article, Users.nickname).join(Users, Users.userid == Article.userid).all()

    m_list = []
    for article, nickname in result:
        m_dict = {}
        for k, v in article.__dict__.items():
            if not k.startswith('_sa_instance_state'):
                if isinstance(v, datetime):
                    v = v.strftime('%Y-%m-%d %H:%M:%S')
                elif k == 'content':
                    pattern = re.compile(r'<[^>]+>')
                    temp = pattern.sub('', v)
                    temp = temp.replace('&nbsp;', '')
                    temp = temp.replace('\r', '')
                    temp = temp.replace('\n', '')
                    temp = temp.replace('\t', '')
                    v = temp.strip()[0:80]
                m_dict[k] = v
        m_dict['nickname'] = nickname
        m_list.append(m_dict)

    red = redis_connect()
    if red is None:
        return
    for row in m_list:
        red.zadd('article', {str(row): row['articleid']})


# 为了兼容性，添加RedisManager类
class RedisManager:
    """Redis管理器"""
    
    def __init__(self, host='127.0.0.1', port=6379, db=0):
        self.pool = redis.ConnectionPool(host=host, port=port, decode_responses=True, db=db)
        self.redis = redis.Redis(connection_pool=self.pool)
    
    def get(self, key):
        """获取值"""
        return self.redis.get(key)
    
    def set(self, key, value, ex=None):
        """设置值"""
        return self.redis.set(key, value, ex=ex)
    
    def delete(self, key):
        """删除键"""
        return self.redis.delete(key)
    
    def connect(self):
        """连接Redis（兼容性方法）"""
        return self.redis


if __name__ == '__main__':
    # redis_mysql_hash()
    redis_article_zsort()
