from flask import Blueprint, render_template, session, redirect, url_for
from woniunote.module.articles import Articles
from woniunote.module.comments import Comments
from woniunote.module.favorites import Favorites
from woniunote.module.users import Users
from woniunote.module.credits import Credits
import traceback
import time

ucenter = Blueprint("ucenter", __name__)


@ucenter.route('/ucenter')
def user_center():
    print("begin to user_center")
    try:
        if session.get('main_islogin') != 'true':
            print("User not logged in, redirecting to index")
            return redirect(url_for('index.home'))
            
        userid = session.get('main_userid')
        if not userid:
            print("No user ID found in session")
            return redirect(url_for('index.home'))
            
        print(f"Loading favorites for user {userid}")
        favorites = Favorites().find_by_userid(userid)
        if favorites:
            # 获取收藏文章的详细信息
            print("Favorites loaded:", favorites)
            articles = Articles.find_by_ids([f.articleid for f in favorites])
            result = []
            for fav in favorites:
                for art in articles:
                    if fav.articleid == art.articleid:
                        result.append((fav, art))
                        break
        else:
            result = []
        
        print(f"Found {len(result)} favorites with articles")
        return render_template("user-center.html", result=result)
    except Exception as e:
        print("Error in user_center:", e)
        traceback.print_exc()
        return redirect(url_for('index.home'))


@ucenter.route('/user/article')
def user_article():
    try:
        if session.get('main_islogin') != 'true':
            print("User not logged in, redirecting to index")
            return redirect(url_for('index.home'))
            
        userid = session.get("main_userid")
        if not userid:
            print("No user ID found in session")
            return redirect(url_for('index.home'))
            
        print(f"Loading articles for user {userid}")
        articles = Articles.find_by_userid(userid)
        result = [(None, article) for article in articles] if articles else []
        print(f"Found {len(result)} articles")
        
        return render_template("user-center.html", result=result)
    except Exception as e:
        print("Error in user_article:", e)
        traceback.print_exc()
        return redirect(url_for('index.home'))


@ucenter.route('/user/comment')
def user_comment():
    try:
        if session.get('main_islogin') != 'true':
            print("User not logged in, redirecting to index")
            return redirect(url_for('index.home'))
            
        userid = session.get("main_userid")
        if not userid:
            print("No user ID found in session")
            return redirect(url_for('index.home'))
            
        print(f"Loading comments for user {userid}")
        comments = Comments().find_by_userid(userid)
        if comments:
            # 获取评论对应的文章信息
            article_ids = list(set(c.articleid for c in comments))
            articles = Articles.find_by_ids(article_ids)
            result = [(comment, article) for comment, article in zip(comments, articles)]
        else:
            result = []
            
        print(f"Found {len(result)} comments")
        return render_template("user-center.html", result=result)
    except Exception as e:
        print("Error in user_comment:", e)
        traceback.print_exc()
        return redirect(url_for('index.home'))


@ucenter.route('/user/info')
def user_info():
    try:
        if session.get('main_islogin') != 'true':
            print("User not logged in, redirecting to index")
            return redirect(url_for('index.home'))
            
        userid = session.get("main_userid")
        if not userid:
            print("No user ID found in session")
            return redirect(url_for('index.home'))
            
        print(f"Loading user info for user {userid}")
        user = Users().find_by_userid(userid)
        if not user:
            print("User not found")
            return redirect(url_for('index.home'))
            
        return render_template("user-info.html", user=user)
    except Exception as e:
        print("Error in user_info:", e)
        traceback.print_exc()
        return redirect(url_for('index.home'))


@ucenter.route('/user/credit')
def user_credit():
    try:
        if session.get('main_islogin') != 'true':
            print("User not logged in, redirecting to index")
            return redirect(url_for('index.home'))
            
        userid = session.get("main_userid")
        if not userid:
            print("No user ID found in session")
            return redirect(url_for('index.home'))
            
        print(f"Loading credits for user {userid}")
        credits = Credits().find_by_userid(userid)
        return render_template("user-credit.html", credits=credits)
    except Exception as e:
        print("Error in user_credit:", e)
        traceback.print_exc()
        return redirect(url_for('index.home'))


@ucenter.route('/user/draft')
def user_draft():
    try:
        if session.get('main_islogin') != 'true':
            print("User not logged in, redirecting to index")
            return redirect(url_for('index.home'))
            
        userid = session.get("main_userid")
        if not userid:
            print("No user ID found in session")
            return redirect(url_for('index.home'))
            
        # 检查用户角色
        if session.get('main_role') != 'editor':
            print("User is not an editor")
            return redirect(url_for('index.home'))
            
        print(f"Loading drafts for user {userid}")
        drafts = Articles.find_drafts_by_userid(userid)
        result = [(None, draft) for draft in drafts] if drafts else []
        print(f"Found {len(result)} drafts")
        
        return render_template("user-center.html", result=result)
    except Exception as e:
        print("Error in user_draft:", e)
        traceback.print_exc()
        return redirect(url_for('index.home'))


@ucenter.route('/user/post')
def user_post():
    try:
        if session.get('main_islogin') != 'true':
            print("User not logged in, redirecting to index")
            return redirect(url_for('index.home'))
            
        userid = session.get("main_userid")
        if not userid:
            print("No user ID found in session")
            return redirect(url_for('index.home'))
            
        return render_template("user-post.html")
    except Exception as e:
        print("Error in user_post:", e)
        traceback.print_exc()
        return redirect(url_for('index.home'))
