from flask import Blueprint, render_template, session, redirect, url_for, request
import uuid
from datetime import datetime, UTC

from woniunote.module.articles import Articles
from woniunote.module.comments import Comments
from woniunote.module.favorites import Favorites
from woniunote.module.users import Users
from woniunote.module.credits import Credits
from woniunote.common.database import ARTICLE_TYPES
from woniunote.common.simple_logger import SimpleLogger

ucenter = Blueprint("ucenter", __name__)

# 初始化用户中心模块日志记录器
ucenter_logger = SimpleLogger('ucenter')

# 生成用户中心模块跟踪ID的函数
def get_ucenter_trace_id():
    """生成用户中心模块的跟踪ID
    
    Returns:
        str: 格式为 'ucenter_yyyyMMdd_uuid' 的跟踪ID
    """
    now = datetime.now(UTC)
    date_str = now.strftime('%Y%m%d')
    return f"ucenter_{date_str}_{str(uuid.uuid4())[:8]}"


@ucenter.route('/ucenter')
def user_center():
    """用户中心首页处理函数
    
    显示用户的收藏文章列表
    
    Returns:
        Response: 渲染后的用户中心页面或重定向到首页
    """
    # 生成跟踪ID
    trace_id = get_ucenter_trace_id()
    
    # 记录用户中心访问请求
    ucenter_logger.info("用户中心访问请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'user_id': session.get('main_userid') if session.get('main_islogin') == 'true' else None
    })
    
    try:
        # 检查用户登录状态
        if session.get('main_islogin') != 'true':
            # 记录未登录访问尝试
            ucenter_logger.warning("未登录访问用户中心", {
                'trace_id': trace_id,
                'remote_addr': request.remote_addr,
                'path': request.path
            })
            return redirect(url_for('index.home'))
        
        # 获取用户ID
        userid = session.get('main_userid')
        if not userid:
            # 记录用户ID不存在
            ucenter_logger.warning("用户ID不存在", {
                'trace_id': trace_id,
                'remote_addr': request.remote_addr,
                'path': request.path,
                'session_data': str(session)
            })
            return redirect(url_for('index.home'))
        
        # 记录开始查询用户收藏
        ucenter_logger.info("查询用户收藏", {
            'trace_id': trace_id,
            'user_id': userid
        })
        
        # 获取用户收藏
        favorites = Favorites().find_by_userid(userid)
        
        if favorites:
            # 记录收藏查询结果
            ucenter_logger.info("用户收藏查询结果", {
                'trace_id': trace_id,
                'user_id': userid,
                'favorites_count': len(favorites)
            })
            
            # 获取收藏文章的详细信息
            article_ids = [f.articleid for f in favorites]
            articles = Articles.find_by_ids(article_ids)
            
            # 记录文章查询结果
            ucenter_logger.info("收藏文章查询结果", {
                'trace_id': trace_id,
                'user_id': userid,
                'article_ids': article_ids,
                'articles_count': len(articles) if articles else 0
            })
            
            # 关联收藏和文章
            result = []
            for fav in favorites:
                for art in articles:
                    if fav.articleid == art.articleid:
                        result.append((fav, art))
                        break
        else:
            # 记录没有收藏
            ucenter_logger.info("用户没有收藏", {
                'trace_id': trace_id,
                'user_id': userid
            })
            result = []
        
        # 记录最终结果
        ucenter_logger.info("用户中心收藏列表生成成功", {
            'trace_id': trace_id,
            'user_id': userid,
            'result_count': len(result)
        })
        
        # 渲染模板
        content = render_template("user-center.html", result=result)
        
        # 记录渲染成功
        ucenter_logger.info("用户中心页面渲染成功", {
            'trace_id': trace_id,
            'user_id': userid,
            'content_length': len(content) if content else 0
        })
        
        return content
    except Exception as e:
        # 记录异常
        ucenter_logger.error("用户中心访问异常", {
            'trace_id': trace_id,
            'user_id': session.get('main_userid'),
            'error': str(e),
            'error_type': type(e).__name__
        })
        return redirect(url_for('index.home'))


@ucenter.route('/user/article')
def user_article():
    """用户发布文章列表处理函数
    
    显示用户发布的文章列表
    
    Returns:
        Response: 渲染后的用户文章列表页面或重定向到首页
    """
    # 生成跟踪ID
    trace_id = get_ucenter_trace_id()
    
    # 记录用户文章列表访问请求
    ucenter_logger.info("用户文章列表访问请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'user_id': session.get('main_userid') if session.get('main_islogin') == 'true' else None
    })
    
    try:
        # 检查用户登录状态
        if session.get('main_islogin') != 'true':
            # 记录未登录访问尝试
            ucenter_logger.warning("未登录访问用户文章列表", {
                'trace_id': trace_id,
                'remote_addr': request.remote_addr,
                'path': request.path
            })
            return redirect(url_for('index.home'))
        
        # 获取用户ID
        userid = session.get("main_userid")
        if not userid:
            # 记录用户ID不存在
            ucenter_logger.warning("用户ID不存在", {
                'trace_id': trace_id,
                'remote_addr': request.remote_addr,
                'path': request.path,
                'session_data': str(session)
            })
            return redirect(url_for('index.home'))
        
        # 记录开始查询用户文章
        ucenter_logger.info("查询用户文章", {
            'trace_id': trace_id,
            'user_id': userid
        })
        
        # 获取用户文章
        articles = Articles.find_by_userid(userid)
        
        # 构建结果列表
        result = [(None, article) for article in articles] if articles else []
        
        # 记录文章查询结果
        ucenter_logger.info("用户文章查询结果", {
            'trace_id': trace_id,
            'user_id': userid,
            'articles_count': len(articles) if articles else 0,
            'result_count': len(result)
        })
        
        # 渲染模板
        content = render_template("user-center.html", result=result)
        
        # 记录渲染成功
        ucenter_logger.info("用户文章列表页面渲染成功", {
            'trace_id': trace_id,
            'user_id': userid,
            'content_length': len(content) if content else 0
        })
        
        return content
    except Exception as e:
        # 记录异常
        ucenter_logger.error("用户文章列表访问异常", {
            'trace_id': trace_id,
            'user_id': session.get('main_userid'),
            'error': str(e),
            'error_type': type(e).__name__
        })
        return redirect(url_for('index.home'))


@ucenter.route('/user/comment')
def user_comment():
    """用户评论列表处理函数
    
    显示用户发表的评论列表
    
    Returns:
        Response: 渲染后的用户评论列表页面或重定向到首页
    """
    # 生成跟踪ID
    trace_id = get_ucenter_trace_id()
    
    # 记录用户评论列表访问请求
    ucenter_logger.info("用户评论列表访问请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'user_id': session.get('main_userid') if session.get('main_islogin') == 'true' else None
    })
    
    try:
        # 检查用户登录状态
        if session.get('main_islogin') != 'true':
            # 记录未登录访问尝试
            ucenter_logger.warning("未登录访问用户评论列表", {
                'trace_id': trace_id,
                'remote_addr': request.remote_addr,
                'path': request.path
            })
            return redirect(url_for('index.home'))
        
        # 获取用户ID
        userid = session.get("main_userid")
        if not userid:
            # 记录用户ID不存在
            ucenter_logger.warning("用户ID不存在", {
                'trace_id': trace_id,
                'remote_addr': request.remote_addr,
                'path': request.path,
                'session_data': str(session)
            })
            return redirect(url_for('index.home'))
        
        # 记录开始查询用户评论
        ucenter_logger.info("查询用户评论", {
            'trace_id': trace_id,
            'user_id': userid
        })
        
        # 获取用户评论
        comments = Comments().find_by_userid(userid)
        
        if comments:
            # 记录评论查询结果
            ucenter_logger.info("用户评论查询结果", {
                'trace_id': trace_id,
                'user_id': userid,
                'comments_count': len(comments)
            })
            
            # 获取评论对应的文章信息
            article_ids = list(set(c.articleid for c in comments))
            
            # 记录开始查询相关文章
            ucenter_logger.info("查询评论相关文章", {
                'trace_id': trace_id,
                'user_id': userid,
                'article_ids': article_ids,
                'unique_article_count': len(article_ids)
            })
            
            # 获取相关文章
            articles = Articles.find_by_ids(article_ids)
            
            # 记录文章查询结果
            ucenter_logger.info("评论相关文章查询结果", {
                'trace_id': trace_id,
                'user_id': userid,
                'articles_count': len(articles) if articles else 0
            })
            
            # 关联评论和文章
            result = [(comment, article) for comment, article in zip(comments, articles)]
        else:
            # 记录没有评论
            ucenter_logger.info("用户没有评论", {
                'trace_id': trace_id,
                'user_id': userid
            })
            result = []
        
        # 记录最终结果
        ucenter_logger.info("用户评论列表生成成功", {
            'trace_id': trace_id,
            'user_id': userid,
            'result_count': len(result)
        })
        
        # 渲染模板
        content = render_template("user-center.html", result=result)
        
        # 记录渲染成功
        ucenter_logger.info("用户评论列表页面渲染成功", {
            'trace_id': trace_id,
            'user_id': userid,
            'content_length': len(content) if content else 0
        })
        
        return content
    except Exception as e:
        # 记录异常
        ucenter_logger.error("用户评论列表访问异常", {
            'trace_id': trace_id,
            'user_id': session.get('main_userid'),
            'error': str(e),
            'error_type': type(e).__name__
        })
        return redirect(url_for('index.home'))


@ucenter.route('/user/info')
def user_info():
    """用户信息页面处理函数
    
    显示用户个人信息页面
    
    Returns:
        Response: 渲染后的用户信息页面或重定向到首页
    """
    # 生成跟踪ID
    trace_id = get_ucenter_trace_id()
    
    # 记录用户信息页面访问请求
    ucenter_logger.info("用户信息页面访问请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'user_id': session.get('main_userid') if session.get('main_islogin') == 'true' else None
    })
    
    try:
        # 检查用户登录状态
        if session.get('main_islogin') != 'true':
            # 记录未登录访问尝试
            ucenter_logger.warning("未登录访问用户信息页面", {
                'trace_id': trace_id,
                'remote_addr': request.remote_addr,
                'path': request.path
            })
            return redirect(url_for('index.home'))
        
        # 获取用户ID
        userid = session.get("main_userid")
        if not userid:
            # 记录用户ID不存在
            ucenter_logger.warning("用户ID不存在", {
                'trace_id': trace_id,
                'remote_addr': request.remote_addr,
                'path': request.path,
                'session_data': str(session)
            })
            return redirect(url_for('index.home'))
        
        # 记录开始查询用户信息
        ucenter_logger.info("查询用户信息", {
            'trace_id': trace_id,
            'user_id': userid
        })
        
        # 获取用户信息
        user = Users().find_by_userid(userid)
        
        # 检查用户是否存在
        if not user:
            # 记录用户不存在
            ucenter_logger.warning("用户不存在", {
                'trace_id': trace_id,
                'user_id': userid
            })
            return redirect(url_for('index.home'))
        
        # 记录用户信息查询成功
        ucenter_logger.info("用户信息查询成功", {
            'trace_id': trace_id,
            'user_id': userid,
            'username': user.username,
            'role': user.role
        })
        
        # 渲染模板
        content = render_template("user-info.html", user=user)
        
        # 记录渲染成功
        ucenter_logger.info("用户信息页面渲染成功", {
            'trace_id': trace_id,
            'user_id': userid,
            'content_length': len(content) if content else 0
        })
        
        return content
    except Exception as e:
        # 记录异常
        ucenter_logger.error("用户信息页面访问异常", {
            'trace_id': trace_id,
            'user_id': session.get('main_userid'),
            'error': str(e),
            'error_type': type(e).__name__
        })
        return redirect(url_for('index.home'))


@ucenter.route('/user/credit')
def user_credit():
    """用户积分页面处理函数
    
    显示用户积分记录页面
    
    Returns:
        Response: 渲染后的用户积分页面或重定向到首页
    """
    # 生成跟踪ID
    trace_id = get_ucenter_trace_id()
    
    # 记录用户积分页面访问请求
    ucenter_logger.info("用户积分页面访问请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'user_id': session.get('main_userid') if session.get('main_islogin') == 'true' else None
    })
    
    try:
        # 检查用户登录状态
        if session.get('main_islogin') != 'true':
            # 记录未登录访问尝试
            ucenter_logger.warning("未登录访问用户积分页面", {
                'trace_id': trace_id,
                'remote_addr': request.remote_addr,
                'path': request.path
            })
            return redirect(url_for('index.home'))
        
        # 获取用户ID
        userid = session.get("main_userid")
        if not userid:
            # 记录用户ID不存在
            ucenter_logger.warning("用户ID不存在", {
                'trace_id': trace_id,
                'remote_addr': request.remote_addr,
                'path': request.path,
                'session_data': str(session)
            })
            return redirect(url_for('index.home'))
        
        # 记录开始查询用户积分
        ucenter_logger.info("查询用户积分", {
            'trace_id': trace_id,
            'user_id': userid
        })
        
        # 获取用户积分记录
        credits = Credits().find_by_userid(userid)
        
        # 记录积分查询结果
        ucenter_logger.info("用户积分查询结果", {
            'trace_id': trace_id,
            'user_id': userid,
            'credits_count': len(credits) if credits else 0
        })
        
        # 渲染模板
        content = render_template("user-credit.html", credits=credits)
        
        # 记录渲染成功
        ucenter_logger.info("用户积分页面渲染成功", {
            'trace_id': trace_id,
            'user_id': userid,
            'content_length': len(content) if content else 0
        })
        
        return content
    except Exception as e:
        # 记录异常
        ucenter_logger.error("用户积分页面访问异常", {
            'trace_id': trace_id,
            'user_id': session.get('main_userid'),
            'error': str(e),
            'error_type': type(e).__name__
        })
        return redirect(url_for('index.home'))


@ucenter.route('/user/draft')
def user_draft():
    """用户草稿列表处理函数
    
    显示编辑角色用户的草稿列表
    
    Returns:
        Response: 渲染后的用户草稿列表页面或重定向到首页
    """
    # 生成跟踪ID
    trace_id = get_ucenter_trace_id()
    
    # 记录用户草稿列表访问请求
    ucenter_logger.info("用户草稿列表访问请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'user_id': session.get('main_userid') if session.get('main_islogin') == 'true' else None,
        'role': session.get('main_role')
    })
    
    try:
        # 检查用户登录状态
        if session.get('main_islogin') != 'true':
            # 记录未登录访问尝试
            ucenter_logger.warning("未登录访问用户草稿列表", {
                'trace_id': trace_id,
                'remote_addr': request.remote_addr,
                'path': request.path
            })
            return redirect(url_for('index.home'))
        
        # 获取用户ID
        userid = session.get("main_userid")
        if not userid:
            # 记录用户ID不存在
            ucenter_logger.warning("用户ID不存在", {
                'trace_id': trace_id,
                'remote_addr': request.remote_addr,
                'path': request.path,
                'session_data': str(session)
            })
            return redirect(url_for('index.home'))
        
        # 检查用户角色
        if session.get('main_role') != 'editor':
            # 记录非编辑角色访问尝试
            ucenter_logger.warning("非编辑角色访问草稿列表", {
                'trace_id': trace_id,
                'remote_addr': request.remote_addr,
                'user_id': userid,
                'role': session.get('main_role')
            })
            return redirect(url_for('index.home'))
        
        # 记录开始查询用户草稿
        ucenter_logger.info("查询用户草稿", {
            'trace_id': trace_id,
            'user_id': userid
        })
        
        # 获取用户草稿
        drafts = Articles.find_drafts_by_userid(userid)
        
        # 构建结果列表
        result = [(None, draft) for draft in drafts] if drafts else []
        
        # 记录草稿查询结果
        ucenter_logger.info("用户草稿查询结果", {
            'trace_id': trace_id,
            'user_id': userid,
            'drafts_count': len(drafts) if drafts else 0,
            'result_count': len(result)
        })
        
        # 渲染模板
        content = render_template("user-center.html", result=result)
        
        # 记录渲染成功
        ucenter_logger.info("用户草稿列表页面渲染成功", {
            'trace_id': trace_id,
            'user_id': userid,
            'content_length': len(content) if content else 0
        })
        
        return content
    except Exception as e:
        # 记录异常
        ucenter_logger.error("用户草稿列表访问异常", {
            'trace_id': trace_id,
            'user_id': session.get('main_userid'),
            'error': str(e),
            'error_type': type(e).__name__
        })
        return redirect(url_for('index.home'))


@ucenter.route('/user/post')
def user_post():
    """用户发布文章页面处理函数
    
    显示用户发布文章的表单页面
    
    Returns:
        Response: 渲染后的发布文章页面或重定向到首页
    """
    # 生成跟踪ID
    trace_id = get_ucenter_trace_id()
    
    # 记录用户发布文章页面访问请求
    ucenter_logger.info("用户发布文章页面访问请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'user_id': session.get('main_userid') if session.get('main_islogin') == 'true' else None,
        'role': session.get('main_role')
    })
    
    try:
        # 检查用户登录状态
        if session.get('main_islogin') != 'true':
            # 记录未登录访问尝试
            ucenter_logger.warning("未登录访问用户发布文章页面", {
                'trace_id': trace_id,
                'remote_addr': request.remote_addr,
                'path': request.path
            })
            return redirect(url_for('index'))
        
        # 获取用户ID
        userid = session.get("main_userid")
        if not userid:
            # 记录用户ID不存在
            ucenter_logger.warning("用户ID不存在", {
                'trace_id': trace_id,
                'remote_addr': request.remote_addr,
                'path': request.path,
                'session_data': str(session)
            })
            return redirect(url_for('index.home'))
        
        # 记录准备发布文章页面
        ucenter_logger.info("准备发布文章页面", {
            'trace_id': trace_id,
            'user_id': userid,
            'article_types_count': len(ARTICLE_TYPES) if ARTICLE_TYPES else 0
        })
        
        # 渲染模板
        content = render_template("user-post.html", article_type=ARTICLE_TYPES, result=[{'type': None}])
        
        # 记录渲染成功
        ucenter_logger.info("用户发布文章页面渲染成功", {
            'trace_id': trace_id,
            'user_id': userid,
            'content_length': len(content) if content else 0
        })
        
        return content
    except Exception as e:
        # 记录异常
        ucenter_logger.error("用户发布文章页面访问异常", {
            'trace_id': trace_id,
            'user_id': session.get('main_userid'),
            'error': str(e),
            'error_type': type(e).__name__
        })
        return redirect(url_for('index'))
