from flask import Blueprint, request, session
import uuid
import datetime

from woniunote.module.favorites import Favorites
from woniunote.common.simple_logger import SimpleLogger

favorite = Blueprint('favorite', __name__)

# 初始化收藏模块日志记录器
favorite_logger = SimpleLogger('favorite')

# 生成收藏模块跟踪ID的函数
def get_favorite_trace_id():
    """生成收藏模块的跟踪ID
    
    Returns:
        str: 格式为 'favorite_yyyyMMdd_uuid' 的跟踪ID
    """
    now = datetime.datetime.now()
    date_str = now.strftime('%Y%m%d')
    return f"favorite_{date_str}_{str(uuid.uuid4())[:8]}"


@favorite.route('/favorite', methods=['POST'])
def add_favorite():
    """添加收藏的处理函数
    
    处理用户对文章的收藏请求，包括登录检查和收藏插入操作
    
    Returns:
        str: 收藏添加结果状态码
    """
    # 生成跟踪ID
    trace_id = get_favorite_trace_id()
    
    try:
        # 获取收藏参数
        articleid = request.form.get('articleid')
        userid = session.get('main_userid')
        
        # 记录收藏请求
        favorite_logger.info("添加收藏请求", {
            'trace_id': trace_id,
            'user_id': userid,
            'article_id': articleid,
            'remote_addr': request.remote_addr,
            'method': request.method
        })
        
        # 检查用户是否已登录
        if not session.get('main_islogin'):
            # 记录未登录访问
            favorite_logger.warning("未登录用户尝试添加收藏", {
                'trace_id': trace_id,
                'article_id': articleid,
                'remote_addr': request.remote_addr
            })
            return 'not-login'
        
        # 添加收藏
        favorite_instance = Favorites()
        result = favorite_instance.insert_favorite(articleid)
        
        if result:
            # 记录收藏成功
            favorite_logger.info("添加收藏成功", {
                'trace_id': trace_id,
                'user_id': userid,
                'article_id': articleid
            })
            return 'favorite-pass'
        else:
            # 记录收藏失败
            favorite_logger.warning("添加收藏失败", {
                'trace_id': trace_id,
                'user_id': userid,
                'article_id': articleid,
                'reason': 'database_operation_failed'
            })
            return 'favorite-fail'
    except Exception as e:
        # 记录异常
        favorite_logger.error("添加收藏异常", {
            'trace_id': trace_id,
            'article_id': articleid if 'articleid' in locals() else None,
            'user_id': session.get('main_userid'),
            'error': str(e),
            'error_type': type(e).__name__
        })
        return 'favorite-fail'


@favorite.route('/favorite/<int:articleid>', methods=['DELETE'])
def cancel_favorite(articleid):
    """取消收藏的处理函数
    
    处理用户取消文章收藏的请求，包括登录检查和收藏删除操作
    
    Args:
        articleid (int): 要取消收藏的文章ID
        
    Returns:
        str: 取消收藏结果状态码
    """
    # 生成跟踪ID
    trace_id = get_favorite_trace_id()
    
    try:
        # 获取用户ID
        userid = session.get('main_userid')
        
        # 记录取消收藏请求
        favorite_logger.info("取消收藏请求", {
            'trace_id': trace_id,
            'user_id': userid,
            'article_id': articleid,
            'remote_addr': request.remote_addr,
            'method': request.method
        })
        
        # 检查用户是否已登录
        if not session.get('main_islogin'):
            # 记录未登录访问
            favorite_logger.warning("未登录用户尝试取消收藏", {
                'trace_id': trace_id,
                'article_id': articleid,
                'remote_addr': request.remote_addr
            })
            return 'not-login'
        
        # 取消收藏
        favorite_instance = Favorites()
        result = favorite_instance.cancel_favorite(articleid)
        
        if result:
            # 记录取消收藏成功
            favorite_logger.info("取消收藏成功", {
                'trace_id': trace_id,
                'user_id': userid,
                'article_id': articleid
            })
            return 'cancel-pass'
        else:
            # 记录取消收藏失败
            favorite_logger.warning("取消收藏失败", {
                'trace_id': trace_id,
                'user_id': userid,
                'article_id': articleid,
                'reason': 'database_operation_failed'
            })
            return 'cancel-fail'
    except Exception as e:
        # 记录异常
        favorite_logger.error("取消收藏异常", {
            'trace_id': trace_id,
            'article_id': articleid,
            'user_id': session.get('main_userid'),
            'error': str(e),
            'error_type': type(e).__name__
        })
        return 'cancel-fail'
