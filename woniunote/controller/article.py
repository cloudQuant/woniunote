from flask import Blueprint, render_template, request, session, abort, url_for, redirect
from woniunote.module.articles import Articles
from woniunote.module.users import Users
from woniunote.common.session_util import get_current_user_id
from woniunote.module.comments import Comments
from woniunote.module.credits import Credits
from woniunote.module.favorites import Favorites
from woniunote.common.timer import can_use_minute
from woniunote.common.database import ARTICLE_TYPES
from woniunote.common.log_decorator import log_function
from woniunote.common.simple_logger import get_simple_logger
import math
import traceback
import os
import datetime
import uuid

# 获取简单日志记录器
simple_logger = get_simple_logger('article_controller')

# 生成跟踪ID
def generate_trace_id():
    return str(uuid.uuid4())

# 获取当前跟踪ID
_thread_local_trace_id = {}
def get_simple_trace_id():
    if 'trace_id' not in _thread_local_trace_id:
        _thread_local_trace_id['trace_id'] = generate_trace_id()
    return _thread_local_trace_id['trace_id']

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
        article_instance = Articles().find_by_id(articleid)
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
            'commentcount': getattr(article, 'commentcount', 0),
            'drafted': article_instance.drafted,
            'checked': article_instance.checked,
            'createtime': article_instance.createtime,
            'updatetime': article_instance.updatetime
        }
        
        # 获取作者昵称
        user = Users.find_by_userid(article_instance.userid)
        article_dict['nickname'] = user.nickname if user else "Unknown"

        # 如果已经消耗积分，则不再截取文章内容
        payed = Credits().check_payed_article(articleid)

        position = 0
        if article_instance.credit > 0 and not payed:
            position = len(article_dict['content']) // 3
            article_dict['content'] = article_dict['content'][:position]

        # 获取当前用户ID
        current_userid = get_current_user_id()
        
        # 检查是否已收藏
        is_favorited = Favorites().check_favorite(articleid)

        Articles.update_read_count(articleid)  # 阅读次数+1

        # 获取当前文章的 上一篇和下一篇
        prev_next = Articles.find_prev_next_by_id(articleid)

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
        return render_template('article-user.html',
                            total = total_articles,
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
                            article_type=ARTICLE_TYPES)
    except Exception as e:
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
        payed = Credits().check_payed_article(articleid)
        
        # 如果未支付，扣除积分
        if not payed and result.credit > 0:
            current_userid = get_current_user_id()
            Credits().insert_detail(credit_type='阅读文章', target=articleid, credit=-1 * result.credit)
            Users().update_credit(credit=-1 * result.credit)
            
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
        user = Users().find_by_userid(userid)
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
        user = Users().find_by_userid(userid)
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
            
        user = Users().find_by_userid(userid)
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
                
                # 返回文章ID字符串，前端AJAX处理需要这种格式
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
        return 'error'


if __name__ == "__main__":
    print(Articles().find_all())
