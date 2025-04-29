from flask import Blueprint, render_template, session, request
from woniunote.module.articles import Articles
from woniunote.common.simple_logger import get_simple_logger
import math
import traceback
import uuid

# 初始化日志记录器
admin_logger = get_simple_logger('admin_controller')

# 生成跟踪ID
def generate_trace_id():
    return str(uuid.uuid4())

# 获取当前跟踪ID
_thread_local_trace_id = {}
def get_admin_trace_id():
    if 'trace_id' not in _thread_local_trace_id:
        _thread_local_trace_id['trace_id'] = generate_trace_id()
    return _thread_local_trace_id['trace_id']

admin = Blueprint("admin", __name__)


@admin.before_request
def before_admin():
    # 生成跟踪ID
    trace_id = get_admin_trace_id()
    
    try:
        # 获取请求路径和方法
        path = request.path
        method = request.method
        
        # 记录请求信息
        admin_logger.info("管理员请求", {
            'trace_id': trace_id,
            'path': path,
            'method': method,
            'remote_addr': request.remote_addr
        })
        
        # 检查管理员权限
        if session.get('islogin') != 'true' or session.get('role') != 'admin':
            admin_logger.warning("非管理员访问管理页面", {
                'trace_id': trace_id,
                'path': path,
                'session_islogin': session.get('islogin'),
                'session_role': session.get('role'),
                'remote_addr': request.remote_addr
            })
            return 'perm-denied'
    except Exception as e:
        admin_logger.error("管理员请求处理异常", {
            'trace_id': trace_id,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


# 为系统管理首页填充文章列表，并绘制分页栏
@admin.route('/admin')
def sys_admin():
    # 生成跟踪ID
    trace_id = get_admin_trace_id()
    
    try:
        # 记录访问管理首页
        admin_logger.info("访问管理首页", {
            'trace_id': trace_id,
            'remote_addr': request.remote_addr,
            'user_id': session.get('userid')
        })
        
        pagesize = 50
        articles_instance = Articles()
        result = articles_instance.find_all_except_draft(0, pagesize)
        total = math.ceil(articles_instance.get_count_except_draft() / pagesize)
        html_file = 'system-admin.html'
        
        # 记录数据查询结果
        admin_logger.info("管理首页数据查询", {
            'trace_id': trace_id,
            'page': 1,
            'pagesize': pagesize,
            'total_articles': total,
            'articles_count': len(result) if result else 0
        })
        
        return render_template(html_file, page=1, result=result, total=total)
    except Exception as e:
        # 记录异常
        admin_logger.error("管理首页异常", {
            'trace_id': trace_id,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        # 返回空页面或错误页面
        return render_template('error.html', error_message="系统管理页面加载失败")

# 为系统管理首页的文章列表进行分页查询
@admin.route('/admin/article/<int:page>')
def admin_article(page):
    # 生成跟踪ID
    trace_id = get_admin_trace_id()
    
    try:
        # 记录分页请求
        admin_logger.info("管理员文章分页请求", {
            'trace_id': trace_id,
            'page': page,
            'remote_addr': request.remote_addr,
            'user_id': session.get('userid')
        })
        
        pagesize = 50
        start = (page - 1) * pagesize
        articles_instance = Articles()
        result = articles_instance.find_all_except_draft(start, pagesize)
        total = math.ceil(articles_instance.get_count_except_draft() / pagesize)
        html_file = 'system-admin.html'
        
        # 记录数据查询结果
        admin_logger.info("管理员文章分页数据", {
            'trace_id': trace_id,
            'page': page,
            'pagesize': pagesize,
            'start_index': start,
            'total_pages': total,
            'articles_count': len(result) if result else 0
        })
        
        return render_template(html_file, page=page, result=result, total=total)
    except Exception as e:
        # 记录异常
        admin_logger.error("管理员文章分页异常", {
            'trace_id': trace_id,
            'page': page,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        # 返回错误页面
        return render_template('error.html', error_message="文章列表加载失败")

# 按照文章进行分类搜索的后台接口
@admin.route('/admin/type/<int:type>-<int:page>')
def admin_search_type(admin_type, page):
    # 生成跟踪ID
    trace_id = get_admin_trace_id()
    
    try:
        # 记录按类型搜索请求
        admin_logger.info("管理员按类型搜索文章", {
            'trace_id': trace_id,
            'article_type': admin_type,
            'page': page,
            'remote_addr': request.remote_addr,
            'user_id': session.get('userid')
        })
        
        pagesize = 50
        start = (page - 1) * pagesize
        result, total = Articles().find_by_type_except_draft(start, pagesize, admin_type)
        total = math.ceil(total / pagesize)
        html_file = 'system-admin.html'
        
        # 记录数据查询结果
        admin_logger.info("管理员按类型搜索结果", {
            'trace_id': trace_id,
            'article_type': admin_type,
            'page': page,
            'pagesize': pagesize,
            'start_index': start,
            'total_pages': total,
            'articles_count': len(result) if result else 0
        })
        
        return render_template(html_file, page=page, result=result, total=total)
    except Exception as e:
        # 记录异常
        admin_logger.error("管理员按类型搜索异常", {
            'trace_id': trace_id,
            'article_type': admin_type,
            'page': page,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        # 返回错误页面
        return render_template('error.html', error_message="按类型搜索文章失败")

# 按照文章标题进行模糊查询的后台接口
@admin.route('/admin/search/<keyword>')
def admin_search_headline(keyword):
    # 生成跟踪ID
    trace_id = get_admin_trace_id()
    
    try:
        # 记录按标题搜索请求
        admin_logger.info("管理员按标题搜索文章", {
            'trace_id': trace_id,
            'keyword': keyword,
            'remote_addr': request.remote_addr,
            'user_id': session.get('userid')
        })
        
        result = Articles().find_by_headline_except_draft(keyword)
        html_file = 'system-admin.html'
        
        # 记录搜索结果
        admin_logger.info("管理员按标题搜索结果", {
            'trace_id': trace_id,
            'keyword': keyword,
            'articles_count': len(result) if result else 0
        })
        
        return render_template(html_file, page=1, result=result, total=1)
    except Exception as e:
        # 记录异常
        admin_logger.error("管理员按标题搜索异常", {
            'trace_id': trace_id,
            'keyword': keyword,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        # 返回错误页面
        return render_template('error.html', error_message="按标题搜索文章失败")

# 文章的隐藏切换接口
@admin.route('/admin/article/hide/<int:articleid>')
def admin_article_hide(articleid):
    # 生成跟踪ID
    trace_id = get_admin_trace_id()
    
    try:
        # 记录文章隐藏切换请求
        admin_logger.info("管理员切换文章隐藏状态", {
            'trace_id': trace_id,
            'article_id': articleid,
            'remote_addr': request.remote_addr,
            'user_id': session.get('userid')
        })
        
        hidden = Articles().switch_hidden(articleid)
        
        # 记录操作结果
        admin_logger.info("管理员切换文章隐藏状态成功", {
            'trace_id': trace_id,
            'article_id': articleid,
            'new_hidden_status': hidden
        })
        
        return str(hidden)
    except Exception as e:
        # 记录异常
        admin_logger.error("管理员切换文章隐藏状态异常", {
            'trace_id': trace_id,
            'article_id': articleid,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        # 返回错误信息
        return "error"


# 文章的推荐切换接口
@admin.route('/admin/article/recommend/<int:articleid>')
def admin_article_recommend(articleid):
    # 生成跟踪ID
    trace_id = get_admin_trace_id()
    
    try:
        # 记录文章推荐切换请求
        admin_logger.info("管理员切换文章推荐状态", {
            'trace_id': trace_id,
            'article_id': articleid,
            'remote_addr': request.remote_addr,
            'user_id': session.get('userid')
        })
        
        recommended = Articles().switch_recommended(articleid)
        
        # 记录操作结果
        admin_logger.info("管理员切换文章推荐状态成功", {
            'trace_id': trace_id,
            'article_id': articleid,
            'new_recommended_status': recommended
        })
        
        return str(recommended)
    except Exception as e:
        # 记录异常
        admin_logger.error("管理员切换文章推荐状态异常", {
            'trace_id': trace_id,
            'article_id': articleid,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        # 返回错误信息
        return "error"


# 文章的审核切换接口
@admin.route('/admin/article/check/<int:articleid>')
def admin_article_check(articleid):
    # 生成跟踪ID
    trace_id = get_admin_trace_id()
    
    try:
        # 记录文章审核切换请求
        admin_logger.info("管理员切换文章审核状态", {
            'trace_id': trace_id,
            'article_id': articleid,
            'remote_addr': request.remote_addr,
            'user_id': session.get('userid')
        })
        
        checked = Articles().switch_checked(articleid)
        
        # 记录操作结果
        admin_logger.info("管理员切换文章审核状态成功", {
            'trace_id': trace_id,
            'article_id': articleid,
            'new_checked_status': checked
        })
        
        return str(checked)
    except Exception as e:
        # 记录异常
        admin_logger.error("管理员切换文章审核状态异常", {
            'trace_id': trace_id,
            'article_id': articleid,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        # 返回错误信息
        return "error"
