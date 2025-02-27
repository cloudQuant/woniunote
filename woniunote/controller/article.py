from flask import Blueprint, render_template, request, session, abort, url_for
from woniunote.module.articles import Articles
from woniunote.module.users import Users
from woniunote.common.session_util import get_current_user_id, is_logged_in
from woniunote.module.comments import Comments
from woniunote.module.credits import Credits
from woniunote.module.favorites import Favorites
from woniunote.common.timer import can_use_minute
from woniunote.common.database import ARTICLE_TYPES
import math
import traceback

article = Blueprint("article", __name__)

@article.route('/article/<int:articleid>')
@article.route('/article/<int:articleid>/<int:current_page>')
def read(articleid, current_page=1):
    print(f" Entering read function for article {articleid}, page {current_page}")
    try:
        print(f" Attempting to find article {articleid}")
        article = Articles().find_by_id(articleid)
        if not article:
            print(f" Article {articleid} not found")
            abort(404)
        print(f" Found article {articleid}: {article.headline[:30]}...")
        
        # 构建文章字典
        article_dict = {
            'articleid': article.articleid,
            'userid': article.userid,  # 确保包含userid
            'headline': article.headline,
            'content': article.content,
            'type': article.type,
            'credit': article.credit,
            'thumbnail': article.thumbnail,
            'readcount': article.readcount,
            'commentcount': getattr(article, 'commentcount', 0),
            'drafted': article.drafted,
            'checked': article.checked,
            'createtime': article.createtime,
            'updatetime': article.updatetime
        }
        
        # 获取作者昵称
        user = Users().find_by_userid(article.userid)
        article_dict['nickname'] = user.nickname if user else "Unknown"

        # 如果已经消耗积分，则不再截取文章内容
        payed = Credits().check_payed_article(articleid)

        position = 0
        if article.credit > 0 and not payed:
            position = len(article_dict['content']) // 3
            article_dict['content'] = article_dict['content'][:position]

        # 获取当前用户ID
        current_userid = get_current_user_id()
        
        # 检查是否已收藏
        is_favorited = Favorites().check_favorite(articleid)

        Articles().update_read_count(articleid)  # 阅读次数+1

        # 获取当前文章的 上一篇和下一篇
        prev_next = Articles().find_prev_next_by_id(articleid)

        # 获取当前文章的评论
        comments = Comments().find_by_articleid(articleid)
        comment_users = {}
        for comment in comments:
            if comment.userid not in comment_users:
                user = Users().find_by_userid(comment.userid)
                comment_users[comment.userid] = user.nickname if user else "Unknown"

        # 获取热门文章列表
        article_instance = Articles()
        last, most, recommended = article_instance.find_last_most_recommended()
        # 获取总文章数
        total_articles = Articles.get_total_count()
        print(f" 系统总文章数: {total_articles}")

        return render_template('article-user.html',
                            total = total_articles,
                            current_page = current_page,
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
                            current_userid=current_userid)
    except Exception as e:
        print("Error in read:", e)
        traceback.print_exc()
        abort(500)


@article.route('/article/readall', methods=['POST'])
def read_all():
    try:
        position = int(request.form.get('position'))
        articleid = request.form.get('articleid')
        article_instance = Articles()
        result = article_instance.find_by_id(articleid)
        content = result[0].content[position:]

        payed = Credits().check_payed_article(articleid)
        if not payed:
            Credits().insert_detail(credit_type='阅读文章', target=articleid, credit=-1 * result[0].credit)
            Users().update_credit(credit=-1 * result[0].credit)

        return content
    except Exception as e:
        print(e)
        traceback.print_exc()


@article.route('/article/prepost')
def pre_post():
    print("begin to run prepost")
    try:
        article_type = ARTICLE_TYPES
        subTypesData = {}
        for key, value in article_type.items():
            if key >= 100:
                main_id = key // 100
                if main_id not in subTypesData:
                    subTypesData[main_id] = {}
                subTypesData[main_id][key] = value
        html_file = 'post-user.html'
        return render_template(html_file, article_type=article_type, subTypesData=subTypesData)
    except Exception as e:
        print(e)
        traceback.print_exc()


@article.route('/article/edit/<int:articleid>')
def go_edit(articleid):
    print("begin to edit articleid:", articleid)
    try:
        result = Articles().find_by_id(articleid)
        print("result:", result)
        target_html = "article-edit.html"
        article_type = ARTICLE_TYPES
        subTypesData = {}
        for key, value in article_type.items():
            if key >= 100:
                main_id = key // 100
                if main_id not in subTypesData:
                    subTypesData[main_id] = {}
                subTypesData[main_id][key] = value
        return render_template(target_html, result=result, article_type=article_type, subTypesData=subTypesData)
    except Exception as e:
        print(e)
        traceback.print_exc()


@article.route("/article/edit", methods=["PUT", "POST"])
def edit_article():
    try:
        # 检查用户是否登录
        if not session.get('main_islogin') == 'true':
            return 'perm-denied'
            
        # 获取表单数据
        headline = request.form.get('headline')
        content = request.form.get('content')
        article_type = int(request.form.get('type'))
        credit = int(request.form.get('credit'))
        drafted = int(request.form.get('drafted'))
        checked = int(request.form.get('checked'))
        articleid = int(request.form.get('articleid'))
        
        # 检查文章是否存在
        article = Articles.find_by_id(articleid)
        if not article:
            return 'post-fail'
            
        # 检查是否是文章作者
        current_userid = session.get('main_userid')
        if str(article.userid) != str(current_userid):
            return 'perm-denied'
            
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
            return str(article_id)
        except Exception as e:
            print("edit", articleid, e)
            return "edit-fail"
    except Exception as e:
        print(e)
        traceback.print_exc()
        return "edit-fail"


@article.route('/article/add', methods=['POST'])
def add_article():
    try:
        if not is_logged_in():
            return 'not-login'
        
        userid = get_current_user_id()
        if userid is None:
            return 'not-login'
            
        user = Users().find_by_userid(userid)
        if user is None:
            return 'user-not-found'

        headline = request.form.get('headline')
        content = request.form.get('content')
        article_type = int(request.form.get('type'))
        credit = int(request.form.get('credit'))
        drafted = int(request.form.get('drafted'))
        checked = int(request.form.get('checked'))
        articleid = int(request.form.get('articleid'))

        thumbname = '%d.png' % article_type
        article_instance = Articles()

        if articleid == 0:
            try:
                if user.role != 'editor':
                    checked = 0
                
                article_id = article_instance.insert_article(
                    article_type=article_type,
                    headline=headline,
                    content=content,
                    credit=credit,
                    thumbnail=thumbname,
                    drafted=drafted,
                    checked=checked,
                    userid=userid  
                )
                return str(article_id)
            except Exception as e:
                print('post-fail', e)
                return 'post-fail'
        else:
            try:
                article = article_instance.find_by_id(articleid)
                if article and (article.userid == userid or user.role == 'editor'):
                    if user.role != 'editor':
                        checked = article.checked
                    
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
                    return str(article_id)
                else:
                    return 'perm-denied'
            except Exception as e:
                print('post-fail', e)
                return 'post-fail'
    except Exception as e:
        print(e)
        traceback.print_exc()
        return 'error'


if __name__ == "__main__":
    print(Articles().find_all())
