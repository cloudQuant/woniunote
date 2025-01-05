from flask import Blueprint, request, session, jsonify

from woniunote.module.articles import Articles
from woniunote.module.comments import Comments
from woniunote.module.credits import Credits
from woniunote.module.users import Users
import traceback

comment = Blueprint('comment', __name__)


@comment.before_request
def before_comment():
    try:
        if session.get('islogin') is None or session.get('islogin') != 'true':
            # return '你还没有登录，不能发表评论'
            return 'not-login'
    except Exception as e:
        print(e)
        traceback.print_exc()


@comment.route('/comment', methods=['POST'])
def add():
    try:
        articleid = request.form.get('articleid')
        content = request.form.get('content').strip()
        ipaddr = request.remote_addr

        # 对评论内容进行简单检验
        if len(content) < 5 or len(content) > 1000:
            return 'content-invalid'

        comment_instance = Comments()
        if not comment_instance.check_limit_per_5():
            try:
                comment_instance.insert_comment(articleid, content, ipaddr)
                # 评论成功后，更新积分明细和剩余积分，及文章回复数量
                Credits().insert_detail(credit_type='添加评论', target=articleid, credit=2)
                Users().update_credit(2)
                Articles().update_replycount(articleid)
                return 'add-pass'
            except Exception as e:
                print("add comment error: ", e)
                return 'add-fail'
        else:
            return 'add-limit'
    except Exception as e:
        print(e)
        traceback.print_exc()


@comment.route('/reply', methods=['POST'])
def reply():
    try:
        articleid = request.form.get('articleid')
        commentid = request.form.get('commentid')
        content = request.form.get('content').strip()
        ipaddr = request.remote_addr

        # 如果评论的字数低于5个或多于1000个，均视为不合法
        if len(content) < 5 or len(content) > 1000:
            return 'content-invalid'

        comment_instance = Comments()
        # 没有超出限制才能发表评论
        if not comment_instance.check_limit_per_5():
            try:
                comment_instance.insert_reply(articleid=articleid, commentid=commentid,
                                              content=content, ipaddr=ipaddr)
                # 评论成功后，同步更新credit表明细、users表积分和article表回复数
                Credits().insert_detail(credit_type='回复评论', target=articleid, credit=2)
                Users().update_credit(2)
                Articles().update_replycount(articleid)
                return 'reply-pass'
            except Exception as e:
                print("reply comment error: ", e)
                return 'reply-fail'
        else:
            return 'reply-limit'
    except Exception as e:
        print(e)
        traceback.print_exc()


# 为了使用Ajax分页，特创建此接口作为演示
# 由于分页栏已经完成渲染，此接口仅根据前端的页码请求后台对应数据
@comment.route('/comment/<int:articleid>-<int:page>')
def comment_page(articleid, page):
    try:
        start = (page - 1) * 10
        comment_instance = Comments()
        return jsonify(comment_instance.get_comment_user_list(articleid, start, 10))
    except Exception as e:
        print(e)
        traceback.print_exc()
