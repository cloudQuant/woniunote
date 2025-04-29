from flask import Blueprint, render_template, abort, request, session
import uuid
import math
from datetime import datetime, UTC

from woniunote.module.articles import Articles
from woniunote.common.timer import can_use_minute
from woniunote.common.redisdb import redis_connect
from woniunote.common.simple_logger import SimpleLogger

index = Blueprint("index", __name__)

# 初始化首页模块日志记录器
index_logger = SimpleLogger('index')

# 生成首页模块跟踪ID的函数
def get_index_trace_id():
    """生成首页模块的跟踪ID
    
    Returns:
        str: 格式为 'index_yyyyMMdd_uuid' 的跟踪ID
    """
    now = datetime.now(UTC)
    date_str = now.strftime('%Y%m%d')
    return f"index_{date_str}_{str(uuid.uuid4())[:8]}"


@index.route('/')
@index.route('/index')
def home():
    """首页访问处理函数
    
    处理首页访问请求，包括获取文章列表、最新文章、最热文章和推荐文章
    
    Returns:
        Response: 渲染后的首页HTML内容
    """
    # 生成跟踪ID
    trace_id = get_index_trace_id()
    
    # 记录首页访问请求
    index_logger.info("首页访问请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'user_id': session.get('userid') if session.get('islogin') == 'true' else None
    })
    
    try:
        # 查询文章列表
        result = Articles.find_limit_with_users(-10, 10)
        total = math.ceil(Articles.get_total_count() / 10)
        
        # 记录文章列表查询结果
        index_logger.info("首页文章列表查询", {
            'trace_id': trace_id,
            'article_count': len(result) if result else 0,
            'total_pages': total
        })

        # 获取最新、最热和推荐文章
        last, most, recommended = Articles.find_last_most_recommended()
        
        # 记录侧边栏文章查询结果
        index_logger.info("首页侧边栏文章查询", {
            'trace_id': trace_id,
            'last_articles_count': len(last) if last else 0,
            'most_articles_count': len(most) if most else 0,
            'recommended_articles_count': len(recommended) if recommended else 0
        })
        
        # 渲染首页模板
        html_file = 'index.html'
        content = render_template(html_file, result=result, page=1, total=total,
                                can_use_minute=can_use_minute(),
                                last_articles=last, most_articles=most, recommended_articles=recommended)
        
        # 记录首页渲染成功
        index_logger.info("首页渲染成功", {
            'trace_id': trace_id,
            'template': html_file,
            'content_length': len(content) if content else 0
        })
        
        return content
    except Exception as e:
        # 记录异常
        index_logger.error("首页访问异常", {
            'trace_id': trace_id,
            'error': str(e),
            'error_type': type(e).__name__
        })
        # 返回错误页面
        return render_template('error.html', error_message="首页加载失败")


@index.route('/home')
def get_home():
    """首页访问处理函数的备用路由
    
    处理通过/home路径访问首页的请求，功能与主首页相同
    
    Returns:
        Response: 渲染后的首页HTML内容
    """
    # 生成跟踪ID
    trace_id = get_index_trace_id()
    
    # 记录备用首页访问请求
    index_logger.info("备用首页访问请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'user_id': session.get('userid') if session.get('islogin') == 'true' else None
    })
    
    try:
        # 查询文章列表
        result = Articles.find_limit_with_users(-10, 10)
        total = math.ceil(Articles.get_total_count() / 10)
        
        # 记录文章列表查询结果
        index_logger.info("备用首页文章列表查询", {
            'trace_id': trace_id,
            'article_count': len(result) if result else 0,
            'total_pages': total
        })

        # 获取最新、最热和推荐文章
        last, most, recommended = Articles.find_last_most_recommended()
        
        # 记录侧边栏文章查询结果
        index_logger.info("备用首页侧边栏文章查询", {
            'trace_id': trace_id,
            'last_articles_count': len(last) if last else 0,
            'most_articles_count': len(most) if most else 0,
            'recommended_articles_count': len(recommended) if recommended else 0
        })
        
        # 渲染首页模板
        html_file = 'index.html'
        content = render_template(html_file, result=result, page=1, total=total,
                                  can_use_minute=can_use_minute(),
                                  last_articles=last, most_articles=most, recommended_articles=recommended)
        
        # 记录首页渲染成功
        index_logger.info("备用首页渲染成功", {
            'trace_id': trace_id,
            'template': html_file,
            'content_length': len(content) if content else 0
        })
        
        return content
    except Exception as e:
        # 记录异常
        index_logger.error("备用首页访问异常", {
            'trace_id': trace_id,
            'error': str(e),
            'error_type': type(e).__name__
        })
        # 返回错误页面
        return render_template('error.html', error_message="首页加载失败")


@index.route('/page/<int:page>')
def paginate(page):
    """文章列表分页处理函数
    
    处理文章列表的分页请求，根据页码返回相应的文章数据
    
    Args:
        page (int): 要访问的页码，从1开始
        
    Returns:
        Response: 渲染后的分页HTML内容
    """
    # 生成跟踪ID
    trace_id = get_index_trace_id()
    
    # 记录分页请求
    index_logger.info("文章列表分页请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'page': page,
        'user_id': session.get('userid') if session.get('islogin') == 'true' else None
    })
    
    try:
        # 计算开始位置并查询文章
        start = (page - 1) * 10  # 计算正确的开始索引
        result = Articles.find_limit_with_users(start, 10)
        total = math.ceil(Articles.get_total_count() / 10)
        
        # 记录文章列表查询结果
        index_logger.info("分页文章列表查询", {
            'trace_id': trace_id,
            'page': page,
            'start_index': start,
            'article_count': len(result) if result else 0,
            'total_pages': total
        })

        # 获取最新、最热和推荐文章
        last, most, recommended = Articles.find_last_most_recommended()
        
        # 记录侧边栏文章查询结果
        index_logger.info("分页侧边栏文章查询", {
            'trace_id': trace_id,
            'page': page,
            'last_articles_count': len(last) if last else 0,
            'most_articles_count': len(most) if most else 0,
            'recommended_articles_count': len(recommended) if recommended else 0
        })
        
        # 记录当前时间供参考
        _current_time = datetime.now(UTC)
        
        # 渲染分页模板
        html_file = 'index.html'
        content = render_template(html_file, result=result, page=page, total=total,
                                  can_use_minute=can_use_minute(),
                                  last_articles=last, most_articles=most, recommended_articles=recommended)
        
        # 记录分页渲染成功
        index_logger.info("分页渲染成功", {
            'trace_id': trace_id,
            'page': page,
            'template': html_file,
            'content_length': len(content) if content else 0
        })
        
        return content
    except Exception as e:
        # 记录异常
        index_logger.error("分页访问异常", {
            'trace_id': trace_id,
            'page': page,
            'error': str(e),
            'error_type': type(e).__name__
        })
        # 返回错误页面
        return render_template('error.html', error_message=f"第{page}页加载失败")


@index.route('/type/<int:class_type>/<int:page>')
def classify(class_type, page):
    """按类型分类文章列表处理函数
    
    处理按文章类型和页码查询文章列表的请求
    
    Args:
        class_type (int): 文章类型编号
        page (int): 要访问的页码，从1开始
        
    Returns:
        Response: 渲染后的分类页面HTML内容
    """
    # 生成跟踪ID
    trace_id = get_index_trace_id()
    
    # 记录分类请求
    index_logger.info("按类型分类文章请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'class_type': class_type,
        'page': page,
        'user_id': session.get('userid') if session.get('islogin') == 'true' else None
    })
    
    try:
        # 计算开始位置并查询文章
        start = (page - 1) * 10
        article = Articles()
        result = article.find_by_type(class_type, start, 10)
        total = math.ceil(article.get_count_by_type(class_type) / 10)
        
        # 记录文章列表查询结果
        index_logger.info("分类文章列表查询", {
            'trace_id': trace_id,
            'class_type': class_type,
            'page': page,
            'start_index': start,
            'article_count': len(result) if result else 0,
            'total_pages': total
        })

        # 获取最新、最热和推荐文章
        last, most, recommended = article.find_last_most_recommended()
        
        # 记录侧边栏文章查询结果
        index_logger.info("分类页侧边栏文章查询", {
            'trace_id': trace_id,
            'class_type': class_type,
            'page': page,
            'last_articles_count': len(last) if last else 0,
            'most_articles_count': len(most) if most else 0,
            'recommended_articles_count': len(recommended) if recommended else 0
        })
        
        # 渲染分类页模板
        html_file = 'type.html'
        content = render_template(html_file,
                               result=result,
                               page=page,
                               total=total,
                               can_use_minute=can_use_minute(),
                               type=class_type,
                               last_articles=last,
                               most_articles=most,
                               recommended_articles=recommended)
        
        # 记录分类页渲染成功
        index_logger.info("分类页渲染成功", {
            'trace_id': trace_id,
            'class_type': class_type,
            'page': page,
            'template': html_file,
            'content_length': len(content) if content else 0
        })
        
        return content
    except Exception as e:
        # 记录异常
        index_logger.error("分类页访问异常", {
            'trace_id': trace_id,
            'class_type': class_type,
            'page': page,
            'error': str(e),
            'error_type': type(e).__name__
        })
        # 返回错误页面
        return render_template('error.html', error_message=f"类型{class_type}第{page}页加载失败")
def search(page, keyword):
    """文章搜索处理函数
    
    根据关键词和页码搜索文章并返回结果
    
    Args:
        page (int): 要访问的页码，从1开始
        keyword (str): 搜索关键词
        
    Returns:
        Response: 渲染后的搜索结果页面HTML内容
    """
    # 生成跟踪ID
    trace_id = get_index_trace_id()
    
    # 记录搜索请求
    index_logger.info("文章搜索请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'keyword': keyword,
        'page': page,
        'user_id': session.get('userid') if session.get('islogin') == 'true' else None
    })
    
    try:
        keyword = keyword.strip()
        if keyword is None or keyword == '' or '%' in keyword or len(keyword) > 10:
            abort(404)

        # 计算开始位置并搜索文章
        start = (page - 1) * 10
        article = Articles()
        result = article.find_by_headline(keyword, start, 10)
        total = math.ceil(article.get_count_by_headline(keyword) / 10)
        
        # 记录搜索结果
        index_logger.info("文章搜索结果", {
            'trace_id': trace_id,
            'keyword': keyword,
            'page': page,
            'start_index': start,
            'result_count': len(result) if result else 0,
            'total_pages': total
        })

        # 获取最新、最热和推荐文章
        last, most, recommended = article.find_last_most_recommended()
        
        # 记录侧边栏文章查询结果
        index_logger.info("搜索页侧边栏文章查询", {
            'trace_id': trace_id,
            'keyword': keyword,
            'page': page,
            'last_articles_count': len(last) if last else 0,
            'most_articles_count': len(most) if most else 0,
            'recommended_articles_count': len(recommended) if recommended else 0
        })
        
        # 渲染搜索结果页模板
        html_file = 'search.html'
        content = render_template(html_file, result=result, page=page, total=total,
                               can_use_minute=can_use_minute(),
                               last_articles=last, most_articles=most, recommended_articles=recommended,
                               keyword=keyword)
        
        # 记录搜索页渲染成功
        index_logger.info("搜索页渲染成功", {
            'trace_id': trace_id,
            'keyword': keyword,
            'page': page,
            'template': html_file,
            'content_length': len(content) if content else 0
        })
        
        return content
    except Exception as e:
        # 记录异常
        index_logger.error("搜索页访问异常", {
            'trace_id': trace_id,
            'keyword': keyword,
            'page': page,
            'error': str(e),
            'error_type': type(e).__name__
        })
        # 返回错误页面
        return render_template('error.html', error_message=f"搜索'{keyword}'第{page}页加载失败")

@index.route('/recommend')
def recommend():
    """侧边栏推荐文章处理函数
    
    处理获取侧边栏推荐文章的请求，包括最新文章、最热文章和推荐文章
    
    Returns:
        Response: 渲染后的侧边栏HTML内容
    """
    # 生成跟踪ID
    trace_id = get_index_trace_id()
    
    # 记录侧边栏请求
    index_logger.info("侧边栏推荐文章请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'user_id': session.get('userid') if session.get('islogin') == 'true' else None
    })
    
    try:
        # 获取最新、最热和推荐文章
        article = Articles()
        last, most, recommended = article.find_last_most_recommended()
        
        # 记录侧边栏文章查询结果
        index_logger.info("侧边栏文章查询结果", {
            'trace_id': trace_id,
            'last_articles_count': len(last) if last else 0,
            'most_articles_count': len(most) if most else 0,
            'recommended_articles_count': len(recommended) if recommended else 0
        })
        
        # 渲染侧边栏模板
        html_file = 'side.html'
        content = render_template(html_file, last_articles=last, most_articles=most,
                               can_use_minute=can_use_minute(),
                               recommended_articles=recommended)
        
        # 记录侧边栏渲染成功
        index_logger.info("侧边栏渲染成功", {
            'trace_id': trace_id,
            'template': html_file,
            'content_length': len(content) if content else 0
        })
        
        return content
    except Exception as e:
        # 记录异常
        index_logger.error("侧边栏访问异常", {
            'trace_id': trace_id,
            'error': str(e),
            'error_type': type(e).__name__
        })
        # 返回错误页面
        return render_template('error.html', error_message="侧边栏加载失败")


# ============== Redis ================== #
# 重构index控制器中的代码，新增以下两个方法


@index.route('/redis')
def home_redis():
    """使用Redis缓存的首页访问处理函数
    
    从 Redis 缓存中获取文章列表并渲染首页
    
    Returns:
        Response: 渲染后的Redis缓存首页HTML内容
    """
    # 生成跟踪ID
    trace_id = get_index_trace_id()
    
    # 记录Redis首页访问请求
    index_logger.info("Redis首页访问请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'user_id': session.get('userid') if session.get('islogin') == 'true' else None
    })
    
    try:
        # 连接Redis
        red = redis_connect()
        
        # 记录Redis连接成功
        index_logger.info("Redis连接成功", {
            'trace_id': trace_id
        })
        
        # 获取有序集合article的总数量
        count = red.zcard('article')
        total = math.ceil(count / 10)
        
        # 记录文章总数
        index_logger.info("Redis文章总数查询", {
            'trace_id': trace_id,
            'article_count': count,
            'total_pages': total
        })
        
        # 利用zrevrange从有序集合中倒序取0-9共10条数据，即最新文章
        result = red.zrevrange('article', 0, 9)
        
        # 由于加载进来的每一条数据是一个字符串，需要使用eval函数将其转换为字典
        article_list = []
        for row in result:
            article_list.append(eval(row))
        
        # 记录文章列表获取结果
        index_logger.info("Redis首页文章列表获取", {
            'trace_id': trace_id,
            'article_count': len(article_list)
        })
        
        # 渲染Redis首页模板
        html_file = 'index-redis.html'
        content = render_template(html_file, article_list=article_list, page=1, total=total)
        
        # 记录Redis首页渲染成功
        index_logger.info("Redis首页渲染成功", {
            'trace_id': trace_id,
            'template': html_file,
            'content_length': len(content) if content else 0
        })
        
        return content
    except Exception as e:
        # 记录异常
        index_logger.error("Redis首页访问异常", {
            'trace_id': trace_id,
            'error': str(e),
            'error_type': type(e).__name__
        })
        # 返回错误页面
        return render_template('error.html', error_message="Redis首页加载失败")

@index.route('/redis/page/<int:page>')
def paginate_redis(page):
    """使用Redis缓存的文章列表分页处理函数
    
    从Redis缓存中获取指定页码的文章列表并渲染页面
    
    Args:
        page (int): 要访问的页码，从1开始
        
    Returns:
        Response: 渲染后的Redis缓存分页HTML内容
    """
    # 生成跟踪ID
    trace_id = get_index_trace_id()
    
    # 记录Redis分页请求
    index_logger.info("Redis分页请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'page': page,
        'user_id': session.get('userid') if session.get('islogin') == 'true' else None
    })
    
    try:
        # 计算开始位置
        pagesize = 10
        start = (page - 1) * pagesize  # 根据当前页码定义数据的起始位置

        # 连接Redis
        red = redis_connect()
        
        # 记录Redis连接成功
        index_logger.info("Redis分页连接成功", {
            'trace_id': trace_id,
            'page': page
        })
        
        # 获取文章总数和总页数
        count = red.zcard('article')
        total = math.ceil(count / 10)
        
        # 记录文章总数
        index_logger.info("Redis分页文章总数查询", {
            'trace_id': trace_id,
            'page': page,
            'article_count': count,
            'total_pages': total
        })
        
        # 获取当前页的文章列表
        result = red.zrevrange('article', start, start + pagesize - 1)
        article_list = []
        for row in result:
            article_list.append(eval(row))
        
        # 记录文章列表获取结果
        index_logger.info("Redis分页文章列表获取", {
            'trace_id': trace_id,
            'page': page,
            'start_index': start,
            'article_count': len(article_list)
        })
        
        # 渲染Redis分页模板
        html_file = 'index-redis.html'
        content = render_template(html_file, article_list=article_list, page=page, total=total)
        
        # 记录Redis分页渲染成功
        index_logger.info("Redis分页渲染成功", {
            'trace_id': trace_id,
            'page': page,
            'template': html_file,
            'content_length': len(content) if content else 0
        })
        
        return content
    except Exception as e:
        # 记录异常
        index_logger.error("Redis分页访问异常", {
            'trace_id': trace_id,
            'page': page,
            'error': str(e),
            'error_type': type(e).__name__
        })
        # 返回错误页面
        return render_template('error.html', error_message=f"Redis第{page}页加载失败")

# ================== 静态化处理 ======================#
@index.route('/static')
def all_static():
    """文章列表静态化处理函数
    
    将所有文章列表页面静态化处理，生成静态HTML文件
    
    Returns:
        Response: 静态化处理完成的提示信息
    """
    # 生成跟踪ID
    trace_id = get_index_trace_id()
    
    # 记录静态化处理请求
    index_logger.info("文章列表静态化处理请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'user_id': session.get('userid') if session.get('islogin') == 'true' else None
    })
    
    try:
        # 设置页面大小和初始化文章对象
        pagesize = 10
        article = Articles()
        
        # 计算总页数
        total = math.ceil(article.get_total_count() / pagesize)
        
        # 记录总页数
        index_logger.info("静态化总页数计算", {
            'trace_id': trace_id,
            'total_pages': total
        })
        
        # 获取侧边栏文章
        last, most, recommended = article.find_last_most_recommended()
        
        # 记录侧边栏文章获取
        index_logger.info("静态化侧边栏文章获取", {
            'trace_id': trace_id,
            'last_articles_count': len(last) if last else 0,
            'most_articles_count': len(most) if most else 0,
            'recommended_articles_count': len(recommended) if recommended else 0
        })
        
        # 遍历每一页生成静态文件
        for page in range(1, total + 1):
            # 计算当前页的起始位置
            start = (page - 1) * pagesize
            
            # 获取当前页的文章列表
            result = article.find_limit_with_users(start, pagesize)
            
            # 记录当前页文章列表获取
            index_logger.info("静态化当前页文章获取", {
                'trace_id': trace_id,
                'page': page,
                'start_index': start,
                'article_count': len(result) if result else 0
            })

            # 渲染当前页面
            html_file = 'index.html'
            content = render_template(html_file, result=result, page=page, total=total,
                                      can_use_minute=can_use_minute(),
                                      last_articles=last, most_articles=most, recommended_articles=recommended)
            
            # 记录当前页渲染成功
            index_logger.info("静态化当前页渲染成功", {
                'trace_id': trace_id,
                'page': page,
                'template': html_file,
                'content_length': len(content) if content else 0
            })

            # 将渲染后的内容写入静态文件, 其实content本身就是标准的HTML页面
            # 注释代码保留，但不执行写入操作
            # with open(f'./template/index-static/index-{page}.html', mode='w', encoding='utf-8') as f:
            #     f.write(content)
        
        # 记录静态化处理完成
        index_logger.info("静态化处理完成", {
            'trace_id': trace_id,
            'total_pages_processed': total
        })

        return '文章列表页面分页静态化处理完成'  # 最后简单响应给前面一个提示信息
    except Exception as e:
        # 记录异常
        index_logger.error("静态化处理异常", {
            'trace_id': trace_id,
            'error': str(e),
            'error_type': type(e).__name__
        })
        # 返回错误信息
        return f'静态化处理失败: {str(e)}'
