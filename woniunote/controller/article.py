from flask import Blueprint, abort, render_template, request, session

from woniunote.module.articles import Articles
from woniunote.module.comments import Comments
from woniunote.module.credits import Credits
from woniunote.module.favorites import Favorites
from woniunote.module.users import Users
from woniunote.common.timer import can_use_minute
import math

article = Blueprint("article", __name__)


@article.route('/article/<int:articleid>')
def read(articleid):
    try:
        result = Articles().find_by_id(articleid)
        # print(articleid,result)
        if result is None:
            abort(404)
    except Exception as e:
        print("read", articleid, e)
        abort(500)

    article_dict = {}
    for k, v in result[0].__dict__.items():
        if not k.startswith('_sa_instance_state'):
            article_dict[k] = v
    article_dict['nickname'] = result[1]

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

    # 显示当前文章对应的评论
    # comment_user = Comment().find_limit_with_user(articleid, 0, 50)

    # comment_list = Comment().get_comment_user_list(articleid, 0, 10)
    #
    count = Comments().get_count_by_article(articleid)
    total = math.ceil(count / 10)
    article_instance = Articles()
    last, most, recommended = article_instance.find_last_most_recommended()

    return render_template('article-user.html', article=article_dict, position=position, payed=payed,
                           is_favorited=is_favorited, prev_next=prev_next,
                           can_use_minute=can_use_minute(),
                           total=total, last_articles=last, most_articles=most,
                           recommended_articles=recommended
                           )


@article.route('/readall', methods=['POST'])
def read_all():
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


@article.route('/prepost')
def pre_post():
    return render_template('post-user.html')


# 编辑文章的前端页面渲染
@article.route('/edit/<int:articleid>')
def go_edit(articleid):
    result = Articles().find_by_id(articleid)
    return render_template("article-edit.html", result=result)


# 处理文章编辑请求
@article.route("/edit", methods=["PUT", "POST"])
def edit_article():
    headline = request.form.get('headline')
    content = request.form.get('content')
    article_type = int(request.form.get('type'))
    credit = int(request.form.get('credit'))
    drafted = int(request.form.get('drafted'))
    checked = int(request.form.get('checked'))
    articleid = int(request.form.get('articleid'))
    article_instance = Articles()
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


@article.route('/article', methods=['POST'])
def add_article():
    headline = request.form.get('headline')
    content = request.form.get('content')
    article_type = int(request.form.get('type'))
    credit = int(request.form.get('credit'))
    drafted = int(request.form.get('drafted'))
    checked = int(request.form.get('checked'))
    articleid = int(request.form.get('articleid'))
    print(f"headline:{headline},article_type:{article_type},articleid:{articleid}")
    if session.get('userid') is None:
        return 'perm-denied'
    else:
        user = Users().find_by_userid(session.get('userid'))
        print("user", user, user.role)
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


if __name__ == "__main__":
    print(Articles().find_all())
