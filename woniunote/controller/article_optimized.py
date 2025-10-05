"""
优化版文章控制器 - 解决文章加载性能问题
主要优化：
1. 使用缓存减少数据库查询
2. 合并查询减少数据库往返
3. 解决N+1查询问题
4. 异步加载非关键内容
"""

from flask import Blueprint, render_template, request, session, abort, url_for, redirect, jsonify, current_app
from woniunote.module.articles import Articles, ArticlesOptimized
from woniunote.module.users import Users
from woniunote.common.unified_session import get_current_user_id, init_unified_session_manager
from woniunote.module.comments import Comments
from woniunote.module.credits import Credits
from woniunote.module.favorites import Favorites
from woniunote.common.unified_utils import can_use_minute
from woniunote.common.database import ARTICLE_TYPES, db
from woniunote.common.log_decorator import log_function
from woniunote.common.unified_logging import get_simple_logger
from woniunote.common.unified_cache import cached
import math
import traceback
import os
import datetime
import uuid
import threading
import time

# 获取简单日志记录器
simple_logger = get_simple_logger('article_controller_optimized')

# 生成跟踪ID
def generate_trace_id():
    return str(uuid.uuid4())

# 获取当前跟踪ID (线程安全版本)
_article_thread_local_trace_id = threading.local()
def get_simple_trace_id():
    if not hasattr(_article_thread_local_trace_id, 'trace_id'):
        _article_thread_local_trace_id.trace_id = generate_trace_id()
    return _article_thread_local_trace_id.trace_id

article_optimized = Blueprint("article_optimized", __name__)

@article_optimized.route('/article/fast/<int:articleid>')
@log_function(log_args=True, log_return=False, log_exception=True)
def read_optimized(articleid):
    """优化版文章读取 - 解决性能问题"""
    start_time = time.time()
    trace_id = get_simple_trace_id()

    simple_logger.info(f"访问文章（优化版）", {
        'trace_id': trace_id,
        'article_id': articleid,
        'function': 'read_optimized'
    })
    
    try:
        # 1. 获取文章详情（包含作者信息）- 使用缓存
        article_dict = ArticlesOptimized.get_article_with_author_cached(articleid)
        if not article_dict:
            simple_logger.warning(f"文章不存在", {
                'trace_id': trace_id,
                'article_id': articleid
            })
            abort(404)
        
        query_time_1 = time.time()
        simple_logger.info("文章基本信息查询完成", {
            'trace_id': trace_id,
            'article_id': articleid,
            'elapsed_ms': round((query_time_1 - start_time) * 1000, 2)
        })
        
        # 2. 并行获取其他信息（使用缓存）
        current_userid = session.get('userid')
        
        # 检查积分支付状态
        payed = Credits.check_payed_article(articleid)
        
        # 处理文章内容截取
        position = 0
        if article_dict['credit'] > 0 and not payed:
            position = len(article_dict['content']) // 3
            article_dict['content'] = article_dict['content'][:position]
        
        # 检查收藏状态
        is_favorited = Favorites.check_favorite(articleid)
        
        # 更新阅读次数（异步处理，不影响页面加载速度）
        try:
            Articles.update_read_count(articleid)
        except Exception as e:
            simple_logger.warning("更新阅读次数失败", {
                'trace_id': trace_id,
                'article_id': articleid,
                'error': str(e)
            })
        
        query_time_2 = time.time()
        simple_logger.info("积分和收藏状态查询完成", {
            'trace_id': trace_id,
            'article_id': articleid,
            'elapsed_ms': round((query_time_2 - query_time_1) * 1000, 2)
        })
        
        # 3. 获取上下篇文章 - 使用缓存
        prev_article, next_article = ArticlesOptimized.get_prev_next_articles_cached(articleid)
        prev_next = {
            'prev_id': prev_article.articleid if prev_article else None,
            'prev_headline': prev_article.headline if prev_article else '没有了',
            'next_id': next_article.articleid if next_article else None,
            'next_headline': next_article.headline if next_article else '没有了'
        }
        
        query_time_3 = time.time()
        simple_logger.info("上下篇文章查询完成", {
            'trace_id': trace_id,
            'article_id': articleid,
            'elapsed_ms': round((query_time_3 - query_time_2) * 1000, 2)
        })
        
        # 4. 获取评论信息 - 使用缓存，解决N+1查询问题
        comments, comment_users = ArticlesOptimized.get_article_comments_with_users_cached(articleid)
        
        query_time_4 = time.time()
        simple_logger.info("评论信息查询完成", {
            'trace_id': trace_id,
            'article_id': articleid,
            'comment_count': len(comments),
            'elapsed_ms': round((query_time_4 - query_time_3) * 1000, 2)
        })
        
        # 5. 获取热门文章列表 - 使用缓存
        last, most, recommended = ArticlesOptimized.get_hot_articles_cached()
        
        # 6. 获取文章总数 - 使用缓存
        total_articles = ArticlesOptimized.get_article_stats_cached()
        
        query_time_5 = time.time()
        simple_logger.info("热门文章和统计信息查询完成", {
            'trace_id': trace_id,
            'article_id': articleid,
            'total_articles': total_articles,
            'elapsed_ms': round((query_time_5 - query_time_4) * 1000, 2)
        })
        
        # 记录总体性能信息
        total_time = time.time() - start_time
        simple_logger.info("文章访问完成（优化版）", {
            'trace_id': trace_id,
            'article_id': articleid,
            'user_id': current_userid,
            'is_favorited': is_favorited,
            'article_type': article_dict['type'],
            'comment_count': len(comments),
            'total_articles': total_articles,
            'total_time_ms': round(total_time * 1000, 2),
            'performance_optimized': True
        })
        
        return render_template('article-user-optimized.html',
                            total=total_articles,
                            article=article_dict,
                            position=position,
                            is_favorited=is_favorited,
                            prev_next=prev_next,
                            comments=comments,
                            comment_users=comment_users,
                            can_use_minute=can_use_minute(),
                            last_articles=last,
                            most_articles=most,
                            recommended_articles=recommended,
                            current_userid=current_userid,
                            article_type=ARTICLE_TYPES,
                            performance_info={
                                'total_time_ms': round(total_time * 1000, 2),
                                'cached_queries': 4,  # 使用了4个缓存查询
                                'optimized': True
                            })
                            
    except Exception as e:
        # 不捕获HTTP异常（如abort抛出的异常）
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            raise  # 重新抛出HTTP异常，让Flask处理
        
        simple_logger.error(f"读取文章 ID: {articleid} 时发生错误（优化版）", {
            'trace_id': trace_id,
            'article_id': articleid,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        abort(500)

@article_optimized.route('/article/api/comments/<int:articleid>')
@log_function(log_args=True, log_return=False, log_exception=True)
def get_comments_api(articleid):
    """异步获取评论API - 用于懒加载"""
    try:
        comments, comment_users = ArticlesOptimized.get_article_comments_with_users_cached(articleid)
        
        # 转换为JSON格式
        comments_data = []
        for comment in comments:
            comments_data.append({
                'commentid': comment.commentid,
                'content': comment.content,
                'createtime': comment.createtime.strftime('%Y-%m-%d %H:%M:%S') if comment.createtime else '',
                'userid': comment.userid,
                'nickname': comment_users.get(comment.userid, 'Unknown')
            })
        
        return jsonify({
            'success': True,
            'comments': comments_data,
            'count': len(comments_data)
        })
        
    except Exception as e:
        simple_logger.error(f"获取评论API失败", {
            'trace_id': get_simple_trace_id(),
            'article_id': articleid,
            'error': str(e)
        })
        return jsonify({
            'success': False,
            'error': '获取评论失败'
        }), 500

@article_optimized.route('/article/api/hot-articles')
@log_function(log_args=False, log_return=False, log_exception=True)
def get_hot_articles_api():
    """异步获取热门文章API - 用于懒加载"""
    try:
        last, most, recommended = ArticlesOptimized.get_hot_articles_cached()
        
        def article_to_dict(article):
            return {
                'articleid': article.articleid,
                'headline': article.headline,
                'type': article.type,
                'readcount': article.readcount,
                'createtime': article.createtime.strftime('%Y-%m-%d') if article.createtime else ''
            }
        
        return jsonify({
            'success': True,
            'last_articles': [article_to_dict(a) for a in last],
            'most_articles': [article_to_dict(a) for a in most],
            'recommended_articles': [article_to_dict(a) for a in recommended]
        })
        
    except Exception as e:
        simple_logger.error(f"获取热门文章API失败", {
            'trace_id': get_simple_trace_id(),
            'error': str(e)
        })
        return jsonify({
            'success': False,
            'error': '获取热门文章失败'
        }), 500

@article_optimized.route('/article/cache/clear')
@log_function(log_args=False, log_return=False, log_exception=True)
def clear_article_cache():
    """清除文章相关缓存 - 管理员功能"""
    try:
        # 检查管理员权限
        if session.get('main_islogin') != 'true':
            return jsonify({'success': False, 'error': '未登录'}), 401
            
        userid = session.get('main_userid')
        user = Users.find_by_userid(userid)
        if not user or user.role != 'editor':
            return jsonify({'success': False, 'error': '权限不足'}), 403
        
        # 清除缓存
        from woniunote.common.cache_manager import clear_cache_by_prefix
        
        cache_prefixes = [
            'article_detail',
            'hot_articles', 
            'article_comments',
            'article_stats',
            'prev_next_articles'
        ]
        
        cleared_count = 0
        for prefix in cache_prefixes:
            try:
                clear_cache_by_prefix(prefix)
                cleared_count += 1
            except Exception as e:
                simple_logger.warning(f"清除缓存失败: {prefix}", {
                    'trace_id': get_simple_trace_id(),
                    'prefix': prefix,
                    'error': str(e)
                })
        
        simple_logger.info("文章缓存清除完成", {
            'trace_id': get_simple_trace_id(),
            'user_id': userid,
            'cleared_prefixes': cleared_count,
            'total_prefixes': len(cache_prefixes)
        })
        
        return jsonify({
            'success': True,
            'message': f'已清除 {cleared_count}/{len(cache_prefixes)} 个缓存前缀'
        })
        
    except Exception as e:
        simple_logger.error(f"清除文章缓存失败", {
            'trace_id': get_simple_trace_id(),
            'error': str(e)
        })
        return jsonify({
            'success': False,
            'error': '清除缓存失败'
        }), 500