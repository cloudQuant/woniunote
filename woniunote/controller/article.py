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
        result = Articles().find_by_id(articleid)
        if not result:
            print(f" Article {articleid} not found")
            abort(404)
        print(f" Found article {articleid}: {result.headline[:30]}...")
        article_dict = {}
        for k, v in result.__dict__.items():
            if not k.startswith('_sa_instance_state'):
                article_dict[k] = v
        
        # 获取作者昵称
        user = Users().find_by_userid(result.userid)
        article_dict['nickname'] = user.nickname if user else "Unknown"

        # 如果已经消耗积分，则不再截取文章内容
        payed = Credits().check_payed_article(articleid)

        position = 0
        if not payed:
            content = article_dict['content']
            # temp = content[0:int(len(content)/2)]
            temp = content[0:]
            position = temp.rindex('</p>') + 4
            article_dict['content'] = temp[0:position]

        Articles().update_read_count(articleid)  # 阅读次数+1

        is_favorited = Favorites().check_favorite(articleid)

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
        # 新增：获取总文章数
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
                            recommended_articles=recommended)
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

        # 如果已经消耗积分，则不再扣除
        payed = Credits().check_payed_article(articleid)
        if not payed:
            # 添加积分明细
            Credits().insert_detail(credit_type='阅读文章', target=articleid, credit=-1 * result[0].credit)
            # 减少用户表的剩余积分
            Users().update_credit(credit=-1 * result[0].credit)

        return content
    except Exception as e:
        print(e)
        traceback.print_exc()


@article.route('/article/prepost')
def pre_post():
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


# 编辑文章的前端页面渲染
@article.route('/article/edit/<int:articleid>')
def go_edit(articleid):
    # print("go to edit article")
    try:
        result = Articles().find_by_id(articleid)
        # print("go_edit", articleid)
        # print("result = ", result)
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


# 处理文章编辑请求
@article.route("/article/edit", methods=["PUT", "POST"])
def edit_article():
    # print("begin to edit article")
    try:
        headline = request.form.get('headline')
        content = request.form.get('content')
        article_type = int(request.form.get('type'))
        credit = int(request.form.get('credit'))
        drafted = int(request.form.get('drafted'))
        checked = int(request.form.get('checked'))
        articleid = int(request.form.get('articleid'))
        article_instance = Articles()
        # print("new_headline", headline)
        try:
            row = article_instance.find_by_id(articleid)
            article_id = article_instance.update_article(articleid=articleid,
                                                         article_type=article_type,
                                                         headline=headline,
                                                         content=content,
                                                         credit=credit,
                                                         thumbnail=row[0].thumbnail,
                                                         drafted=row[0].drafted,
                                                         checked=row[0].checked)
            return str(article_id)
        except Exception as e:
            print("edit", articleid, e)
            return "edit-fail"
    except Exception as e:
        print(e)
        traceback.print_exc()


@article.route('/article/add', methods=['POST'])
def add_article():
    try:
        # 检查用户是否登录
        if not is_logged_in():
            return 'not-login'
        
        # 获取当前用户信息
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
        # print(f"headline:{headline},article_type:{article_type},articleid:{articleid}")
        if user.role == 'editor':
            # 权限合格，可以执行发布文章的代码
            # 首先为文章生成缩略图，优先从内容中找，找不到则随机生成一张
            # url_list = parse_image_url(content)
            # if len(url_list) > 0:   # 表示文章中存在图片
            #     thumbname = generate_thumb(url_list)
            # else:
            #     # 如果文章中没有图片，则根据文章类别指定一张缩略图
            #     thumbname = '%d.png' % type
            thumbname = '%d.png' % article_type
            article_instance = Articles()
            # 再判断articleid是否为0，如果为0则表示是新数据
            if articleid == 0:
                try:
                    article_id = article_instance.insert_article(article_type=article_type,
                                                                 headline=headline,
                                                                 content=content,
                                                                 credit=credit,
                                                                 thumbnail=thumbname,
                                                                 drafted=drafted,
                                                                 checked=checked)

                    # 新增文章成功后，将已经静态化的文章列表页面全部删除，便于生成新的静态文件
                    # list = os.listdir('./template/index-static/')
                    # for file in list:
                    #     os.remove('./template/index-static/' + file)
                    #
                    # print("id",str(id))
                    return str(article_id)
                except Exception as e:
                    print('post-fail', e)
                    return 'post-fail'
            else:
                # 如果是已经添加过的文章，则做修改操作
                try:
                    article_id = article_instance.update_article(articleid=articleid,
                                                                 article_type=article_type,
                                                                 headline=headline,
                                                                 content=content,
                                                                 credit=credit,
                                                                 thumbnail=thumbname,
                                                                 drafted=drafted,
                                                                 checked=checked)
                    return str(article_id)
                except Exception as e:
                    print('post-fail', e)
                    return 'post-fail'

        # 如果角色不是作者，则只能投稿，不能正式发布
        elif checked == 1:
            return 'perm-denied'
        else:
            return 'perm-denied'
    except Exception as e:
        print(e)
        traceback.print_exc()


if __name__ == "__main__":
    print(Articles().find_all())
