from flask import render_template
from woniunote.controller.user import *
from woniunote.module.articles import Articles
from woniunote.module.comments import Comments
from woniunote.module.favorites import Favorites
import traceback

ucenter = Blueprint("ucenter", __name__)


@ucenter.route('/ucenter')
def user_center():
    try:
        result = Favorites().find_my_favorite()
        html_file = "user-center.html"
        return render_template(html_file, result=result)
    except Exception as e:
        print(e)
        traceback.print_exc()


@ucenter.route('/user/favorite/<int:favoriteid>')
def user_favorite(favoriteid):
    try:
        canceled = Favorites().switch_favorite(favoriteid)
        return str(canceled)
    except Exception as e:
        print(e)
        traceback.print_exc()


@ucenter.route('/user/post')
def user_post():
    try:
        # return render_template('user-post.html',my_article_type=ARTICLE_TYPES)
        html_file = "user-post.html"
        return render_template(html_file)
    except Exception as e:
        print(e)
        traceback.print_exc()


@ucenter.route('/user/article')
def user_article():
    try:
        userid = session.get("userid")
        results = Articles().find_all()
        results = [[i.articleid, i] for i in results if i.userid == userid]
        html_file = "user-center.html"
        return render_template(html_file, result=results)
    except Exception as e:
        print(e)
        traceback.print_exc()


@ucenter.route('/user/comment')
def user_comment():
    try:
        userid = session.get("userid")
        results = Comments().find_all()
        commentid_list = [i.articleid for i in results]
        articles = Articles().find_all()
        articles = [[i.articleid, i] for i in articles if i.articleid in commentid_list]
        html_file = "user-center.html"
        return render_template(html_file, result=articles)
    except Exception as e:
        print(e)
        traceback.print_exc()

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
