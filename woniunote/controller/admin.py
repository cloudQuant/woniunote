from flask import Blueprint, render_template, session
from woniunote.module.articles import Articles
import math
import traceback

admin = Blueprint("admin", __name__)


@admin.before_request
def before_admin():
    try:
        if session.get('islogin') != 'true' or session.get('role') != 'admin':
            return 'perm-denied'
    except Exception as e:
        print(e)
        traceback.print_exc()


# 为系统管理首页填充文章列表，并绘制分页栏
@admin.route('/admin')
def sys_admin():
    try:
        pagesize = 50
        articles_instance = Articles()
        result = articles_instance.find_all_except_draft(0, pagesize)
        total = math.ceil(articles_instance.get_count_except_draft() / pagesize)
        html_file = 'system-admin.html'
        return render_template(html_file, page=1, result=result, total=total)
    except Exception as e:
        print(e)
        traceback.print_exc()

# 为系统管理首页的文章列表进行分页查询
@admin.route('/admin/article/<int:page>')
def admin_article(page):
    try:
        pagesize = 50
        start = (page - 1) * pagesize
        articles_instance = Articles()
        result = articles_instance.find_all_except_draft(start, pagesize)
        total = math.ceil(articles_instance.get_count_except_draft() / pagesize)
        html_file = 'system-admin.html'
        return render_template(html_file, page=page, result=result, total=total)
    except Exception as e:
        print(e)
        traceback.print_exc()

# 按照文章进行分类搜索的后台接口
@admin.route('/admin/type/<int:type>-<int:page>')
def admin_search_type(admin_type, page):
    try:
        pagesize = 50
        start = (page - 1) * pagesize
        result, total = Articles().find_by_type_except_draft(start, pagesize, admin_type)
        total = math.ceil(total / pagesize)
        html_file = 'system-admin.html'
        return render_template(html_file, page=page, result=result, total=total)
    except Exception as e:
        print(e)
        traceback.print_exc()

# 按照文章标题进行模糊查询的后台接口
@admin.route('/admin/search/<keyword>')
def admin_search_headline(keyword):
    try:
        result = Articles().find_by_headline_except_draft(keyword)
        html_file = 'system-admin.html'
        return render_template(html_file, page=1, result=result, total=1)
    except Exception as e:
        print(e)
        traceback.print_exc()

# 文章的隐藏切换接口
@admin.route('/admin/article/hide/<int:articleid>')
def admin_article_hide(articleid):
    try:
        hidden = Articles().switch_hidden(articleid)
        return str(hidden)
    except Exception as e:
        print(e)
        traceback.print_exc()


# 文章的推荐切换接口
@admin.route('/admin/article/recommend/<int:articleid>')
def admin_article_recommend(articleid):
    try:
        recommended = Articles().switch_recommended(articleid)
        return str(recommended)
    except Exception as e:
        print(e)
        traceback.print_exc()


# 文章的审核切换接口
@admin.route('/admin/article/check/<int:articleid>')
def admin_article_check(articleid):
    try:
        checked = Articles().switch_checked(articleid)
        return str(checked)
    except Exception as e:
        print(e)
        traceback.print_exc()
