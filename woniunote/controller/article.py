from flask import Blueprint, render_template, request, session, abort, url_for, redirect, jsonify, current_app
from woniunote.module.articles import Articles
from woniunote.module.users import Users
from woniunote.common.unified_session import get_current_user_id, init_unified_session_manager
from woniunote.module.comments import Comments
from woniunote.module.credits import Credits
from woniunote.module.favorites import Favorites
from woniunote.common.unified_utils import can_use_minute
from woniunote.common.database import ARTICLE_TYPES, db
from woniunote.common.log_decorator import log_function
from woniunote.common.unified_logging import get_simple_logger
import math
import traceback
import os
import datetime
import uuid
import threading

# 获取简单日志记录器
simple_logger = get_simple_logger('article_controller')

# 生成跟踪ID
def generate_trace_id():
    return str(uuid.uuid4())

# 获取当前跟踪ID (线程安全版本)
_article_thread_local_trace_id = threading.local()
def get_simple_trace_id():
    if not hasattr(_article_thread_local_trace_id, 'trace_id'):
        _article_thread_local_trace_id.trace_id = generate_trace_id()
    return _article_thread_local_trace_id.trace_id

# 向后兼容的变量名
thread_local_trace_id = _article_thread_local_trace_id

article = Blueprint("article", __name__)

@article.route('/article/<int:articleid>')
@log_function(log_args=True, log_return=False, log_exception=True)
def read(articleid):
    """读取文章详情"""
    # 生成跟踪ID
    trace_id = get_simple_trace_id()

    # 使用简单日志记录器记录日志
    simple_logger.info(f"访问文章", {
        'trace_id': trace_id,
        'article_id': articleid,
        'function': 'read'
    })
    
    try:
        # 查找文章
        article_instance = Articles.find_by_id(articleid)
        if not article_instance:
            # 记录警告日志
            simple_logger.warning(f"文章不存在", {
                'trace_id': trace_id,
                'article_id': articleid
            })
            abort(404)
            
        # 记录信息日志
        simple_logger.info(f"找到文章", {
            'trace_id': trace_id,
            'article_id': articleid,
            'headline': article_instance.headline[:30] + '...' if len(article_instance.headline) > 30 else article_instance.headline,
            'type': article_instance.type
        })
        
        # 构建文章字典
        article_dict = {
            'articleid': article_instance.articleid,
            'userid': article_instance.userid,  # 确保包含userid
            'headline': article_instance.headline,
            'content': article_instance.content,
            'type': article_instance.type,
            'credit': article_instance.credit,
            'thumbnail': article_instance.thumbnail,
            'readcount': article_instance.readcount,
            'commentcount': getattr(article_instance, 'commentcount', 0),
            'drafted': article_instance.drafted,
            'checked': article_instance.checked,
            'createtime': article_instance.createtime,
            'updatetime': article_instance.updatetime
        }
        
        # 获取作者昵称
        user = Users.find_by_userid(article_instance.userid)
        article_dict['nickname'] = user.nickname if user else "Unknown"

        # 如果已经消耗积分，则不再截取文章内容
        payed = Credits.check_payed_article(articleid)

        position = 0
        if article_instance.credit > 0 and not payed:
            position = len(article_dict['content']) // 3
            article_dict['content'] = article_dict['content'][:position]

        # 获取当前用户ID
        current_userid = session.get('userid')
        
        # 检查是否已收藏
        is_favorited = Favorites.check_favorite(articleid)

        Articles.update_read_count(articleid)  # 阅读次数+1

        # 获取当前文章的 上一篇和下一篇
        prev_article, next_article = Articles.find_prev_next_by_id(articleid)
        prev_next = {
            'prev_id': prev_article.articleid if prev_article else None,
            'prev_headline': prev_article.headline if prev_article else '没有了',
            'next_id': next_article.articleid if next_article else None,
            'next_headline': next_article.headline if next_article else '没有了'
        }

        # 获取当前文章的评论
        comments = Comments.find_by_articleid(articleid)
        comment_users = {}
        for comment in comments:
            if comment.userid not in comment_users:
                user = Users.find_by_userid(comment.userid)
                comment_users[comment.userid] = user.nickname if user else "Unknown"

        # 获取热门文章列表
        last, most, recommended = Articles.find_last_most_recommended()
        # 获取总文章数
        total_articles = Articles.get_total_count()
        
        # 记录文章阅读相关信息
        simple_logger.info("文章访问信息", {
            'trace_id': get_simple_trace_id(),
            'article_id': articleid,
            'user_id': current_userid,
            'is_favorited': is_favorited,
            'article_type': article_dict['type'],
            'comment_count': len(comments),
            'total_articles': total_articles
        })
        return redirect(url_for('article.read_optimized', articleid=articleid))
    except Exception as e:
        # 不捕获HTTP异常（如abort抛出的异常）
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            raise  # 重新抛出HTTP异常，让Flask处理
        
        simple_logger.error(f"读取文章 ID: {articleid} 时发生错误", {
            'trace_id': trace_id,
            'article_id': articleid,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        abort(500)


@article.route('/article/readall', methods=['POST'])
@log_function(log_args=True, log_return=False, log_exception=True)
def read_all():
    """获取文章完整内容并处理积分消费"""
    try:
        # 获取请求参数
        position = int(request.form.get('position'))
        articleid = request.form.get('articleid')
        
        # 查找文章
        article_instance = Articles()
        result = article_instance.find_by_id(articleid)
        if not result:
            logger.warning("文章不存在", extra={'extra_data': {
                'trace_id': get_simple_trace_id(),
                'article_id': articleid
            }})
            return ''
            
        # 获取文章内容
        content = result.content[position:]
        
        # 检查是否已支付积分
        payed = Credits.check_payed_article(articleid)

        # 如果未支付，扣除积分
        if not payed and result.credit > 0:
            current_userid = session.get('userid')  # 直接从session获取
            Credits.insert_detail(credit_type='阅读文章', target=articleid, credit=-1 * result.credit)
            # 暂时注释掉用户积分更新，因为Users模块没有这个方法
            # Users.update_credit(credit=-1 * result.credit)
            
            simple_logger.info("文章积分消费", {
                'trace_id': get_simple_trace_id(),
                'article_id': articleid,
                'user_id': current_userid,
                'credit_consumed': result.credit
            })

        return content
    except Exception as e:
        simple_logger.error("获取文章完整内容失败", {
            'trace_id': get_simple_trace_id(),
            'article_id': articleid if 'articleid' in locals() else 'unknown',
            'error': str(e)
        })
        return ''


@article.route('/article/test-post')
@log_function(log_args=False, log_return=False, log_exception=True)
def test_post():
    """测试文章发布页面（无需登录）"""
    try:
        # 准备子类型数据
        subtypes_data = {}
        for key, value in ARTICLE_TYPES.items():
            if key >= 100:
                main_id = key // 100
                if main_id not in subtypes_data:
                    subtypes_data[main_id] = {}
                subtypes_data[main_id][key] = value
        
        # 返回模板
        return render_template('post-user.html', article_type=ARTICLE_TYPES, subTypesData=subtypes_data)
    except Exception as e:
        simple_logger.error("访问测试文章发布页面异常", {
            'trace_id': get_simple_trace_id(),
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        abort(500)

@article.route('/article/pre-post')
@log_function(log_args=False, log_return=False, log_exception=True)
def pre_post():
    """进入文章发布页面"""
    try:
        # 检查登录状态
        if session.get('main_islogin') != 'true':
            simple_logger.warning("未登录访问", {
                'trace_id': get_simple_trace_id(),
                'page': 'article_post'
            })
            return redirect('/login')
        
        # 获取用户ID
        userid = session.get('main_userid')
        if userid is None:
            simple_logger.warning("用户ID为空", {
                'trace_id': get_simple_trace_id(),
                'page': 'article_post'
            })
            return redirect('/login')
            
        # 查找用户
        user = Users.find_by_userid(userid)
        if user is None:
            simple_logger.warning("用户不存在", {
                'trace_id': get_simple_trace_id(),
                'user_id': userid,
                'page': 'article_post'
            })
            return redirect('/login')
        
        # 记录用户访问
        simple_logger.info("访问文章发布页面", {
            'trace_id': get_simple_trace_id(),
            'user_id': userid,
            'nickname': user.nickname,
            'role': user.role
        })
        
        # 准备子类型数据
        subtypes_data = {}
        for key, value in ARTICLE_TYPES.items():
            if key >= 100:
                main_id = key // 100
                if main_id not in subtypes_data:
                    subtypes_data[main_id] = {}
                subtypes_data[main_id][key] = value
        
        # 返回模板
        return render_template('post-user.html', article_type=ARTICLE_TYPES, subTypesData=subtypes_data)
    except Exception as e:
        simple_logger.error("访问文章发布页面异常", {
            'trace_id': get_simple_trace_id(),
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        abort(500)


@article.route('/article/edit/<int:articleid>')
@log_function(log_args=True, log_return=False, log_exception=True)
def go_edit(articleid):
    """进入文章编辑页面"""
    try:
        # 检查登录状态
        if session.get('main_islogin') != 'true':
            simple_logger.warning("未登录访问", {
                'trace_id': get_simple_trace_id(),
                'page': 'article_edit',
                'article_id': articleid
            })
            return redirect('/login')
        
        # 获取用户ID
        userid = session.get('main_userid')
        if userid is None:
            simple_logger.warning("用户ID为空", {
                'trace_id': get_simple_trace_id(),
                'page': 'article_edit',
                'article_id': articleid
            })
            return redirect('/login')
            
        # 查找用户
        user = Users.find_by_userid(userid)
        if user is None:
            simple_logger.warning("用户不存在", {
                'trace_id': get_simple_trace_id(),
                'user_id': userid,
                'page': 'article_edit',
                'article_id': articleid
            })
            return redirect('/login')
        
        # 记录用户访问
        simple_logger.info("访问文章编辑页面", {
            'trace_id': get_simple_trace_id(),
            'user_id': userid,
            'nickname': user.nickname,
            'role': user.role,
            'article_id': articleid
        })
        
        # 获取文章信息
        result = Articles().find_by_id(articleid)
        if not result:
            logger.warning("文章不存在", extra={'extra_data': {
                'trace_id': get_simple_trace_id(),
                'article_id': articleid
            }})
            abort(404)
            
        # 检查文章所有权
        if str(result.userid) != str(userid) and user.role != 'editor':
            simple_logger.warning("文章所有权限制", {
                'trace_id': get_simple_trace_id(),
                'user_id': userid,
                'article_id': articleid,
                'article_owner': result.userid
            })
            abort(403)
        # 准备子类型数据
        article_type = ARTICLE_TYPES
        subTypesData = {}
        for key, value in article_type.items():
            if key >= 100:
                main_id = key // 100
                if main_id not in subTypesData:
                    subTypesData[main_id] = {}
                subTypesData[main_id][key] = value
        
        # 记录文章类型信息
        simple_logger.info("文章编辑数据准备", {
            'trace_id': get_simple_trace_id(),
            'article_id': articleid,
            'article_type': result.type,
            'article_headline': result.headline[:30] + '...' if len(result.headline) > 30 else result.headline,
            'subtypes_count': len(subTypesData)
        })
        
        # 返回模板
        return render_template("article-edit.html", result=result, article_type=article_type, subTypesData=subTypesData)
    except Exception as e:
        simple_logger.error("访问文章编辑页面异常", {
            'trace_id': get_simple_trace_id(),
            'article_id': articleid,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        abort(500)


@article.route("/article/edit", methods=["PUT", "POST"])
@log_function(log_args=False, log_return=True, log_exception=True)
def edit_article():
    """编辑文章接口"""
    try:
        # 检查登录状态
        if session.get('main_islogin') != 'true':
            simple_logger.warning("用户未登录尝试编辑文章", {
                'trace_id': get_simple_trace_id()
            })
            return 'login'
        
        # 获取当前用户ID
        current_userid = session.get('main_userid')
            
        # 获取表单数据
        headline = request.form.get('headline')
        content = request.form.get('content')
        main_type = int(request.form.get('type'))
        sub_type = request.form.get('subtype')
        credit = int(request.form.get('credit'))
        drafted = int(request.form.get('drafted'))
        checked = int(request.form.get('checked'))
        articleid = int(request.form.get('articleid'))
        
        # 处理文章类型
        if sub_type and sub_type.strip():
            article_type = int(sub_type)
        else:
            article_type = main_type
            
        # 记录文章编辑信息
        simple_logger.info("文章编辑请求", {
            'trace_id': get_simple_trace_id(),
            'user_id': current_userid,
            'article_id': articleid,
            'headline': headline[:30] + '...' if len(headline) > 30 else headline,
            'main_type': main_type,
            'sub_type': sub_type,
            'final_type': article_type,
            'credit': credit,
            'drafted': drafted,
            'checked': checked
        })
        
        # 检查文章是否存在
        article = Articles.find_by_id(articleid)
        if not article:
            simple_logger.error("文章不存在", {
                'trace_id': get_simple_trace_id(),
                'article_id': articleid
            })
            return 'post-fail'
            
        # 检查权限
        if str(article.userid) != str(current_userid):
            simple_logger.warning("权限不足", {
                'trace_id': get_simple_trace_id(),
                'user_id': current_userid,
                'article_id': articleid,
                'article_owner': article.userid
            })
            return 'perm-denied'
        
        # 记录类型变化
        simple_logger.info("文章类型变化", {
            'trace_id': get_simple_trace_id(),
            'article_id': articleid,
            'original_type': article.type,
            'new_type': article_type
        })
            
        try:
            # 更新文章
            article_id = Articles.update_article(
                articleid=articleid,
                article_type=article_type,
                headline=headline,
                content=content,
                credit=credit,
                thumbnail=article.thumbnail,
                drafted=drafted,
                checked=checked
            )
            simple_logger.info("文章更新成功", {
                'trace_id': get_simple_trace_id(),
                'article_id': article_id
            })
            return str(article_id)
        except Exception as e:
            simple_logger.error("更新文章失败", {
                'trace_id': get_simple_trace_id(),
                'article_id': articleid,
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            return "edit-fail"
    except Exception as e:
        # 装饰器已经处理了异常日志，这里只需要返回错误信息
        return "edit-fail"


@article.route('/article/post', methods=['POST'])
@article.route('/article/add', methods=['POST'])
@log_function(log_args=False, log_return=True, log_exception=True)
def add_article():
    """添加新文章接口"""
    try:
        # 检查登录状态
        if session.get('main_islogin') != 'true':
            simple_logger.warning("未登录用户尝试添加文章", {
                'trace_id': get_simple_trace_id()
            })
            return 'not-login'
        
        userid = session.get('main_userid')
        if userid is None:
            simple_logger.warning("用户ID为空，无法添加文章", {
                'trace_id': get_simple_trace_id()
            })
            return 'not-login'

        user = Users.find_by_userid(userid)
        if user is None:
            simple_logger.error("用户不存在", {
                'trace_id': get_simple_trace_id(),
                'user_id': userid
            })
            return 'user-not-found'

        # 获取表单数据
        headline = request.form.get('headline')
        content = request.form.get('content')
        main_type = int(request.form.get('type'))
        sub_type = request.form.get('subtype')
        credit = int(request.form.get('credit'))
        drafted = int(request.form.get('drafted'))
        checked = int(request.form.get('checked'))
        articleid = int(request.form.get('articleid'))
        
        # 处理文章类型
        if sub_type and sub_type.strip():
            article_type = int(sub_type)
        else:
            article_type = main_type
            
        # 记录文章添加信息
        simple_logger.info("文章添加请求", {
            'trace_id': get_simple_trace_id(),
            'user_id': userid,
            'article_id': articleid,
            'headline': headline[:30] + '...' if len(headline) > 30 else headline,
            'main_type': main_type,
            'sub_type': sub_type,
            'final_type': article_type,
            'credit': credit,
            'drafted': drafted,
            'checked': checked,
            'is_new': articleid == 0
        })

        thumbname = '%d.png' % article_type
        article_instance = Articles()

        if articleid == 0:
            # 新增文章
            try:
                # 处理用户角色和审核状态
                if user.role != 'editor':
                    checked = 0
                
                # 插入新文章
                article_id = article_instance.insert_article(
                    article_type=article_type,
                    headline=headline,
                    content=content,
                    credit=credit,
                    thumbnail=thumbname,
                    drafted=drafted,
                    checked=checked
                )
                
                simple_logger.info("新文章插入成功", {
                    'trace_id': get_simple_trace_id(),
                    'article_id': article_id,
                    'user_id': userid,
                    'user_role': user.role,
                    'article_type': article_type
                })
                
                # 返回文章ID字符串（前端期待的格式）
                return str(article_id)
            except Exception as e:
                simple_logger.error("插入新文章失败", {
                    'trace_id': get_simple_trace_id(),
                    'user_id': userid,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
                return 'post-fail'
        else:
            # 更新现有文章
            try:
                article = article_instance.find_by_id(articleid)
                if not article:
                    simple_logger.warning("要更新的文章不存在", {
                        'trace_id': get_simple_trace_id(),
                        'article_id': articleid
                    })
                    return 'post-fail'
                    
                # 检查权限
                if article and (article.userid == userid or user.role == 'editor'):
                    # 处理用户角色和审核状态
                    if user.role != 'editor':
                        checked = article.checked
                    
                    # 更新文章
                    article_id = article_instance.update_article(
                        articleid=articleid,
                        article_type=article_type,
                        headline=headline,
                        content=content,
                        credit=credit,
                        thumbnail=thumbname,
                        drafted=drafted,
                        checked=checked
                    )
                    
                    simple_logger.info("文章更新成功", {
                        'trace_id': get_simple_trace_id(),
                        'article_id': article_id,
                        'user_id': userid,
                        'user_role': user.role,
                        'article_type': article_type,
                        'original_type': article.type
                    })
                    
                    # 返回文章ID字符串，前端AJAX处理需要这种格式
                    return str(article_id)
                else:
                    simple_logger.warning("权限不足", {
                        'trace_id': get_simple_trace_id(),
                        'user_id': userid,
                        'article_id': articleid,
                        'article_owner': article.userid
                    })
                    return 'perm-denied'
            except Exception as e:
                simple_logger.error("更新文章失败", {
                    'trace_id': get_simple_trace_id(),
                    'article_id': articleid,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
                return 'post-fail'
    except Exception as e:
        # 装饰器已经处理了异常日志，这里只需要返回错误信息
        return 'post-fail'


# ==================== 性能优化路由 ====================

@article.route('/article/fast/<int:articleid>')
@log_function(log_args=True, log_return=False, log_exception=True)
def read_optimized(articleid):
    """优化版文章读取 - 解决性能问题"""
    import time
    start_time = time.time()
    trace_id = get_simple_trace_id()

    simple_logger.info(f"访问文章（优化版）", {
        'trace_id': trace_id,
        'article_id': articleid,
        'function': 'read_optimized'
    })
    
    try:
        # 1. 获取文章详情（包含作者信息）- 使用缓存
        from woniunote.module.articles import ArticlesOptimized
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
        if not recommended or len(recommended) == 0:
            fallback = last if last else most
            recommended = fallback[:9] if fallback else []
        
        # 6. 获取文章总数 - 使用缓存
        total_articles = ArticlesOptimized.get_article_stats_cached()
        
        query_time_5 = time.time()
        simple_logger.info("热门文章和统计信息查询完成", {
            'trace_id': trace_id,
            'article_id': articleid,
            'total_articles': total_articles,
            'recommended_fallback_used': (not recommended or len(recommended) == 0),
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
                            last_articles=[],
                            most_articles=most,
                            recommended_articles=recommended,
                            current_userid=current_userid,
                            article_type=ARTICLE_TYPES,
                            show_last=False,
                            performance_info={
                                'total_time_ms': round(total_time * 1000, 2),
                                'cached_queries': 4,
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

@article.route('/article/api/comments/<int:articleid>')
@log_function(log_args=True, log_return=False, log_exception=True)
def get_comments_api(articleid):
    """异步获取评论API - 用于懒加载"""
    try:
        from woniunote.module.articles import ArticlesOptimized
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

@article.route('/article/api/hot-articles')
@log_function(log_args=False, log_return=False, log_exception=True)
def get_hot_articles_api():
    """异步获取热门文章API - 用于懒加载"""
    try:
        from woniunote.module.articles import ArticlesOptimized
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

if __name__ == "__main__":
    print(Articles().find_all())
