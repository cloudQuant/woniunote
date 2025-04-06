from flask import render_template, redirect, abort
from woniunote.controller.user import *
from woniunote.common.database import db

# 从模型文件导入数据库模型
from woniunote.models.todo import Item, Category




tcenter = Blueprint("tcenter", __name__)


# @tcenter.route('/todo')
# def todo_center():
#     # return "I am todo"
#     category = Category.query.get_or_404(1)
#     categories = Category.query.all()
#     items = category.items
#     return render_template('todo_index.html', items=items,
#                            categories=categories, category_now=category)


@tcenter.route('/todo/', methods=['GET', 'POST'])
def todo_index():
    print("enter todo_index")
    if session.get('main_islogin') is None:
        print("cannot find main_islogin")
        abort(404)
    if request.method == 'POST':
        body = request.form.get('item')
        category_id = request.form.get('category')
        category_card = Category.query.get_or_404(category_id)
        item = Item(body=body, category=category_card)
        db.session.add(item)
        db.session.commit()
        return redirect(f"/todo/category/{category_card.id}")
    return redirect(f"/todo/category/1")


@tcenter.route('/todo/category/<int:category_id>', methods=['GET', 'POST'])
def category(category_id):
    if session.get('main_islogin') is None:
        abort(404)
    category_card = Category.query.get_or_404(category_id)
    categories = Category.query.all()
    items = category_card.items
    html_file = "todo_index.html"
    return render_template(html_file, items=items,
                           categories=categories, category_now=category_card)


@tcenter.route('/todo/new_category', methods=['GET', 'POST'])
def new_category():
    if session.get('main_islogin') is None:
        abort(404)
    # print("enter new_category")
    name = request.form.get('name')
    # print("enter new_category",name)
    category_card = Category(name=name)
    db.session.add(category_card)
    db.session.commit()
    return redirect(f"/todo/category/{category_card.id}")


@tcenter.route('/todo/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    if session.get('main_islogin') is None:
        abort(404)
    print("edit_item", item_id)
    item = Item.query.get_or_404(item_id)
    category_ = item.category
    item.body = request.form.get('body')
    db.session.add(item)
    db.session.commit()
    return redirect(f"/todo/category/{category_.id}")


@tcenter.route('/todo/edit_category/<int:category_id>', methods=['GET', 'POST'])
def edit_category(category_id):
    if session.get('main_islogin') is None:
        abort(404)
    print("edit_category", category_id)
    category_card = Category.query.get_or_404(category_id)
    category_card.name = request.form.get('name')
    db.session.add(category_card)
    db.session.commit()
    return redirect(f"/todo/category/{category_card.id}")


@tcenter.route('/todo/done/<int:item_id>', methods=['GET', 'POST'])
def done(item_id):
    if session.get('main_islogin') is None:
        abort(404)
    item = Item.query.get_or_404(item_id)
    category_card = item.category
    done_category = Category.query.get_or_404(2)
    done_item = Item(body=item.body, category=done_category)
    db.session.add(done_item)
    db.session.delete(item)
    db.session.commit()
    return redirect(f"/todo/category/{category_card.id}")


@tcenter.route('/todo/delete_item/<int:item_id>', methods=['GET', 'POST'])
def delete_item(item_id):
    if session.get('main_islogin') is None:
        abort(404)
    # print("del_item",item_id)
    item = Item.query.get_or_404(item_id)
    category_card = item.category
    if item is None:
        return redirect(f"/todo/category/1")
    db.session.delete(item)
    db.session.commit()
    return redirect(f"/todo/category/{category_card.id}")


@tcenter.route('/todo/delete_category/<int:category_id>', methods=['GET', 'POST'])
def delete_category(category_id):
    if session.get('main_islogin') is None:
        abort(404)
    category_card = Category.query.get_or_404(category_id)
    if category_card is None or category_id in [1, 2]:
        return redirect(f"/todo/category/1")
    db.session.delete(category_card)
    db.session.commit()
    return redirect(f"/todo/category/{category_card.id}")
