from flask import Blueprint, render_template, abort, request
from woniunote.module.articles import Articles
from woniunote.common.timer import can_use_minute
import math
from datetime import datetime, UTC
from woniunote.common.redisdb import redis_connect
import traceback

index = Blueprint("index", __name__)


@index.route('/')
@index.route('/index')
def home():
    try:
        # 下述代码跟之前版本保持不变，正常查询数据库
        result = Articles.find_limit_with_users(-10, 10)
        total = math.ceil(Articles.get_total_count() / 10)

        last, most, recommended = Articles.find_last_most_recommended()
        
        html_file = 'index.html'
        content = render_template(html_file, result=result, page=1, total=total,
                                can_use_minute=can_use_minute(),
                                last_articles=last, most_articles=most, recommended_articles=recommended)
        return content
    except Exception as e:
        print(e)
        traceback.print_exc()


@index.route('/home')
def get_home():
    try:
        # 下述代码跟之前版本保持不变，正常查询数据库
        result = Articles.find_limit_with_users(-10, 10)
        # result = article.find_all()
        total = math.ceil(Articles.get_total_count() / 10)

        last, most, recommended = Articles.find_last_most_recommended()
        # content = render_template('index.html', result=result, page=1, total=total)
        html_file = 'index.html'
        content = render_template(html_file, result=result, page=1, total=total,
                                  can_use_minute=can_use_minute(),
                                  last_articles=last, most_articles=most, recommended_articles=recommended)
        # content = render_template('index.html', result=result, page=1, total=total,
        #                        contents=[last, most,recommended])
        # 如果是第一个用户访问，而静态文件不存在，则生成一个
        # with open('./template/index-static/index-1.html', mode='w', encoding='utf-8') as f:
        #     f.write(content)
        # print("begin to get_home")
        return content
    except Exception as e:
        print(e)
        traceback.print_exc()


@index.route('/page/<int:page>')
def paginate(page):
    try:
        start = (page - 1) * 10  # Calculate the correct start index
        result = Articles.find_limit_with_users(start, 10)
        # result = [i[0] for i in result]
        total = math.ceil(Articles.get_total_count() / 10)

        last, most, recommended = Articles.find_last_most_recommended()
        _current_time = datetime.now(UTC)
        html_file = 'index.html'
        content = render_template(html_file, result=result, page=page, total=total,
                                  can_use_minute=can_use_minute(),
                                  last_articles=last, most_articles=most, recommended_articles=recommended)
        return content
    except Exception as e:
        print(e)
        traceback.print_exc()


@index.route('/type/<int:class_type>/<int:page>')
def classify(class_type, page):
    # print("class_type", class_type, "classify run")
    try:
        start = (page - 1) * 10
        article = Articles()
        result = article.find_by_type(class_type, start, 10)
        total = math.ceil(article.get_count_by_type(class_type) / 10)
        last, most, recommended = article.find_last_most_recommended()
        html_file = 'type.html'
        return render_template(html_file,
                               result=result,
                               page=page,
                               total=total,
                               can_use_minute=can_use_minute(),
                               type=class_type,
                               last_articles=last,
                               most_articles=most,
                               recommended_articles=recommended)
    except Exception as e:
        print("出现错误")
        print(e)
        traceback.print_exc()

@index.route('/search/<int:page>-<keyword>')
def search(page, keyword):
    try:
        keyword = keyword.strip()
        if keyword is None or keyword == '' or '%' in keyword or len(keyword) > 10:
            abort(404)

        start = (page - 1) * 10
        article = Articles()
        result = article.find_by_headline(keyword, start, 10)
        total = math.ceil(article.get_count_by_headline(keyword) / 10)
        last, most, recommended = article.find_last_most_recommended()
        html_file = 'search.html'
        return render_template(html_file, result=result, page=page, total=total,
                               can_use_minute=can_use_minute(),
                               last_articles=last, most_articles=most, recommended_articles=recommended,
                               keyword=keyword)
    except Exception as e:
        print(e)
        traceback.print_exc()


@index.route('/recommend')
def recommend():
    try:
        article = Articles()
        last, most, recommended = article.find_last_most_recommended()
        html_file = 'side.html'
        return render_template(html_file, last_articles=last, most_articles=most,
                               can_use_minute=can_use_minute(),
                               recommended_articles=recommended)
    except Exception as e:
        print(e)
        traceback.print_exc()


# ============== Redis ================== #
# 重构index控制器中的代码，新增以下两个方法


@index.route('/redis')
def home_redis():
    try:
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
        html_file = 'index-redis.html'
        return render_template(html_file, article_list=article_list, page=1, total=total)
    except Exception as e:
        print(e)
        traceback.print_exc()

@index.route('/redis/page/<int:page>')
def paginate_redis(page):
    try:
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
        html_file = 'index-redis.html'
        return render_template(html_file, article_list=article_list, page=page, total=total)
    except Exception as e:
        print(e)
        traceback.print_exc()

# ================== 静态化处理 ======================#
@index.route('/static')
def all_static():
    try:
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
            html_file = 'index.html'
            content = render_template(html_file, result=result, page=page, total=total,
                                      can_use_minute=can_use_minute(),
                                      last_articles=last, most_articles=most, recommended_articles=recommended)

            # 将渲染后的内容写入静态文件, 其实content本身就是标准的HTML页面
            # with open(f'./template/index-static/index-{page}.html', mode='w', encoding='utf-8') as f:
            #     f.write(content)

        return '文章列表页面分页静态化处理完成'  # 最后简单响应给前面一个提示信息
    except Exception as e:
        print(e)
        traceback.print_exc()
