from flask import Blueprint, render_template, abort
from woniunote.module.articles import Articles
from woniunote.common.timer import can_use_minute
import math
from datetime import datetime
from woniunote.common.redisdb import redis_connect

index = Blueprint("index", __name__)


@index.route('/')
def home():
    # print("begin to home")
    # 判断是否存在该页面，如果存在则直接响应，否则正常查询数据库
    # now ignore this 
    # if os.path.exists('./template/index-static/index-1.html'):
    #     return render_template('index-static/index-1.html')

    # 下述代码跟之前版本保持不变，正常查询数据库
    article = Articles()
    result = article.find_limit_with_users(-10, 10)
    total = math.ceil(article.get_total_count() / 10)

    last, most, recommended = article.find_last_most_recommended()
    # content = render_template('index.html', result=result, page=1, total=total)
    content = render_template('index.html', result=result, page=1, total=total,
                              can_use_minute=can_use_minute(),
                              last_articles=last, most_articles=most, recommended_articles=recommended)
    # content =  render_template('index.html', result=result, page=1, total=total,
    #                        contents=[last,most,recommended])
    # 如果是第一个用户访问，而静态文件不存在，则生成一个
    # with open('./template/index-static/index-1.html', mode='w', encoding='utf-8') as file:
    #     file.write(content)
    # print("begin to home",[i['Article'].headline for i in result])

    return content


@index.route('/index')
def get_index():
    # 判断是否存在该页面，如果存在则直接响应，否则正常查询数据库
    # now ignore this 
    # if os.path.exists('./template/index-static/index-1.html'):
    #     return render_template('index-static/index-1.html')

    # 下述代码跟之前版本保持不变，正常查询数据库
    article = Articles()
    result = article.find_limit_with_users(-10, 10)
    # result = article.find_all()
    total = math.ceil(article.get_total_count() / 10)

    last, most, recommended = article.find_last_most_recommended()
    # content = render_template('index.html', result=result, page=1, total=total)
    content = render_template('index.html', result=result, page=1, total=total,
                              can_use_minute=can_use_minute(),
                              last_articles=last, most_articles=most, recommended_articles=recommended)
    # content =  render_template('index.html', result=result, page=1, total=total,
    #                        contents=[last,most,recommended])
    # 如果是第一个用户访问，而静态文件不存在，则生成一个
    # with open('./template/index-static/index-1.html', mode='w', encoding='utf-8') as file:
    #     file.write(content)
    # print("begin to index")
    return content


@index.route('/home')
def get_home():
    # 判断是否存在该页面，如果存在则直接响应，否则正常查询数据库
    # now ignore this 
    # if os.path.exists('./template/index-static/index-1.html'):
    #     return render_template('index-static/index-1.html')

    # 下述代码跟之前版本保持不变，正常查询数据库
    article = Articles()
    result = article.find_limit_with_users(-10, 10)
    # result = article.find_all()
    total = math.ceil(article.get_total_count() / 10)

    last, most, recommended = article.find_last_most_recommended()
    # content = render_template('index.html', result=result, page=1, total=total)
    content = render_template('index.html', result=result, page=1, total=total,
                              can_use_minute=can_use_minute(),
                              last_articles=last, most_articles=most, recommended_articles=recommended)
    # content =  render_template('index.html', result=result, page=1, total=total,
    #                        contents=[last,most,recommended])
    # 如果是第一个用户访问，而静态文件不存在，则生成一个
    # with open('./template/index-static/index-1.html', mode='w', encoding='utf-8') as file:
    #     file.write(content)
    # print("begin to get_home")
    return content


@index.route('/page/<int:page>')
def paginate(page):
    start = -1 * page * 10  # 1==>0, 2==>10
    article = Articles()
    result = article.find_limit_with_users(start, 10)
    # result = article.find_all()
    total = math.ceil(article.get_total_count() / 10)

    last, most, recommended = article.find_last_most_recommended()
    _current_time = datetime.utcnow()
    # content = render_template('index.html', result=result, page=1, total=total)
    content = render_template('index.html', result=result, page=page, total=total,
                              can_use_minute=can_use_minute(),
                              last_articles=last, most_articles=most, recommended_articles=recommended)
    # content =  render_template('index.html', result=result, page=1, total=total,
    #                        contents=[last,most,recommended])
    # 如果是第一个用户访问，而静态文件不存在，则生成一个
    # with open('./template/index-static/index-1.html', mode='w', encoding='utf-8') as file:
    #     file.write(content)
    # print("page",page,"start",start,[i['Article'].headline for i in result])
    return content


@index.route('/type/<int:type>-<int:page>')
def classify(class_type, page):
    start = (page - 1) * 10
    article = Articles()
    result = article.find_by_type(class_type, start, 10)
    total = math.ceil(article.get_count_by_type(class_type) / 10)
    last, most, recommended = article.find_last_most_recommended()
    return render_template('type.html',
                           result=result,
                           page=page,
                           total=total,
                           can_use_minute=can_use_minute(),
                           type=class_type,
                           last_articles=last,
                           most_articles=most,
                           recommended_articles=recommended)


@index.route('/search/<int:page>-<keyword>')
def search(page, keyword):
    keyword = keyword.strip()
    if keyword is None or keyword == '' or '%' in keyword or len(keyword) > 10:
        abort(404)

    start = (page - 1) * 10
    article = Articles()
    result = article.find_by_headline(keyword, start, 10)
    total = math.ceil(article.get_count_by_headline(keyword) / 10)
    last, most, recommended = article.find_last_most_recommended()

    return render_template('search.html', result=result, page=page, total=total,
                           can_use_minute=can_use_minute(),
                           last_articles=last, most_articles=most, recommended_articles=recommended,
                           keyword=keyword)


@index.route('/recommend')
def recommend():
    article = Articles()
    last, most, recommended = article.find_last_most_recommended()
    return render_template('side.html', last_articles=last, most_articles=most,
                           can_use_minute=can_use_minute(),
                           recommended_articles=recommended)


# ============== Redis ================== #
# 重构index控制器中的代码，新增以下两个方法


@index.route('/redis')
def home_redis():
    red = redis_connect()
    # 获取有序集合article的总数量
    count = red.zcard('article')
    total = math.ceil(count / 10)
    # 利用zrevrange从有序集合中倒序取0-9共10条数据，即最新文章
    result = red.zrevrange('article', 0, 9)
    # 由于加载进来的每一条数据是一个字符串，需要使用eval函数将其转换为字典
    article_list = []
    for row in result:
        article_list.append(eval(row))

    return render_template('index-redis.html', article_list=article_list, page=1, total=total)


@index.route('/redis/page/<int:page>')
def paginate_redis(page):
    pagesize = 10
    start = (page - 1) * pagesize  # 根据当前页码定义数据的起始位置

    red = redis_connect()
    count = red.zcard('article')
    total = math.ceil(count / 10)
    result = red.zrevrange('article', start, start + pagesize - 1)
    article_list = []
    for row in result:
        article_list.append(eval(row))
    # 将相关数据传递给模板页面，从模板引擎调用
    return render_template('index-redis.html', article_list=article_list, page=page, total=total)


# ================== 静态化处理 ======================#
@index.route('/static')
def all_static():
    pagesize = 10
    article = Articles()
    # 先计算一共有多少页，处理逻辑与分页接口一致
    total = math.ceil(article.get_total_count() / pagesize)
    last, most, recommended = article.find_last_most_recommended()
    # 遍历每一页的内容，从数据库中查询出来，渲染到对应页面中
    for page in range(1, total + 1):
        start = (page - 1) * pagesize
        result = article.find_limit_with_users(start, pagesize)

        # 将当前页面正常渲染，但不响应给前端，而是将渲染后的内容写入静态文件
        content = render_template('index.html', result=result, page=page, total=total,
                                  can_use_minute=can_use_minute(),
                                  last_articles=last, most_articles=most, recommended_articles=recommended)

        # 将渲染后的内容写入静态文件,其实content本身就是标准的HTML页面
        # with open(f'./template/index-static/index-{page}.html', mode='w', encoding='utf-8') as file:
        #     file.write(content)

    return '文章列表页面分页静态化处理完成'  # 最后简单响应给前面一个提示信息
