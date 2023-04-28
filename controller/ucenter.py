from flask import Blueprint, render_template
from flask_login import LoginManager,login_required,UserMixin,login_user,logout_user,current_user
from woniunote.module.favorite import Favorite
from woniunote.controller.user import *
from woniunote.module.article import Article
from woniunote.module.comment import Comment
from woniunote.common.database import db,ARTICLE_TYPES


ucenter = Blueprint("ucenter", __name__)

@ucenter.route('/ucenter')
def user_center():
    result = Favorite().find_my_favorite()
    return render_template('user-center.html', result=result)

@ucenter.route('/user/favorite/<int:favoriteid>')
def user_favorite(favoriteid):
    canceled = Favorite().switch_favorite(favoriteid)
    return str(canceled)

@ucenter.route('/user/post')
def user_post():
    #return render_template('user-post.html',my_article_type=ARTICLE_TYPES)
    return render_template('user-post.html')

@ucenter.route('/user/article')
def user_article():
    # print(" get article")
    # return render_template("article-user.html")
    # name=request.cookies.get('username')
    userid = session.get("userid")
    results = Article().find_all()
    results = [[i.articleid,i] for i in results if i.userid == userid]
    return render_template('user-center.html', result=results)

@ucenter.route('/user/comment')
def user_comment():
    # print(" get article")
    # return render_template("article-user.html")
    # name=request.cookies.get('username')
    
    userid = session.get("userid")
    results = Comment().find_all()
    commentid_list = [i.articleid for i in results]
    articles = Article().find_all()
    articles = [[i.articleid,i] for i in articles if i.articleid in commentid_list]
    # print(results)
    return render_template('user-center.html', result=articles)

# @ucenter.route('/todo', methods=['GET', 'POST'])
# def todo():
#     return render_template("todo_index.html")

# @ucenter.route('/todo/', methods=['GET', 'POST'])
# def todo_index():
#     if request.method == 'POST':
#         body = request.form.get('item')
#         category_id = request.form.get('category')
#         category = Category.query.get_or_404(category_id)
#         item = Item(body=body, category=category)
#         todo_db.session.add(item)
#         todo_db.session.commit()
#         return redirect(url_for('category', id=category_id))
#     return redirect(f"/todo/category/1")


# @ucenter.route('/todo/category/<int:id>')
# def category(id):
#     category = Category.query.get_or_404(id)
#     print(1,category)
#     categories = Category.query.all()
#     print(2,categories)
#     items = category.items
#     print(3,items)
#     return render_template('todo_index.html', items=items,
#                            categories=categories, category_now=category)


# @ucenter.route('/todo/new-category', methods=['GET', 'POST'])
# def new_category():
#     name = request.form.get('name')
#     category = Category(name=name)
#     todo_db.session.add(category)
#     todo_db.session.commit()
#     return redirect(f"/todo/category/{category.id}")


# @ucenter.route('/todo/edit-item/<int:id>', methods=['GET', 'POST'])
# def edit_item(id):
#     item = Item.query.get_or_404(id)
#     category = item.category
#     item.body = request.form.get('body')
#     todo_db.session.add(item)
#     todo_db.session.commit()
#     return redirect(f"/todo/category/{category.id}")


# @ucenter.route('/todo/edit-category/<int:id>', methods=['GET', 'POST'])
# def edit_category(id):
#     category = Category.query.get_or_404(id)
#     category.name = request.form.get('name')
#     todo_db.session.add(category)
#     todo_db.session.commit()
#     return redirect(f"/todo/category/{category.id}")


# @ucenter.route('/todo/done/<int:id>', methods=['GET', 'POST'])
# def done(id):
#     item = Item.query.get_or_404(id)
#     category = item.category
#     done_category = Category.query.get_or_404(2)
#     done_item = Item(body=item.body, category=done_category)
#     todo_db.session.add(done_item)
#     todo_db.session.delete(item)
#     todo_db.session.commit()
#     return redirect(f"/todo/category/{category.id}")


# @ucenter.route('/todo/delete-item/<int:id>')
# def del_item(id):
#     item = Item.query.get_or_404(id)
#     category = item.category
#     if item is None:
#         return redirect(url_for('category', id=1))
#     todo_db.session.delete(item)
#     todo_db.session.commit()
#     return redirect(f"/todo/category/{category.id}")


# @ucenter.route('/todo/delete-category/<int:id>')
# def del_category(id):
#     category = Category.query.get_or_404(id)
#     if category is None or id in [1, 2]:
#         return redirect(url_for('category', id=1))
#     todo_db.session.delete(category)
#     todo_db.session.commit()
#     return redirect(f"/todo/category/1")