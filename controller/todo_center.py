from flask import Flask,Blueprint, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager,login_required,UserMixin,login_user,logout_user,current_user
from woniunote.module.favorite import Favorite
from woniunote.controller.user import *
from woniunote.module.article import Article
from woniunote.module.comment import Comment
from woniunote.common.database import db,ARTICLE_TYPES
import os 
app = Flask(__name__)
# todo_app.config['SECRET_KEY'] = 'a secret string'
# todo_app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite://')
# todo_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24)

SQLALCHEMY_DATABASE_URI = 'mysql://debian-sys-maint:8vm5a0XBDt0HVTGC@localhost:3306/woniunote?charset=utf8'
# 使用集成方式处理SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # True: 跟踪数据库的修改，及时发送信号
app.config['SQLALCHEMY_POOL_SIZE'] = 100  # 数据库连接池的大小。默认是数据库引擎的默认值（通常是 5）
# 实例化db对象
app.config['DEBUG'] = True
db = SQLAlchemy(app)


dbsession = db.session
DBase = db.Model

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    category_id = db.Column(
        db.Integer, db.ForeignKey('category.id'), default=1)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    items = db.relationship('Item', backref='category')
# from woniunote.common.todo_database import todo_db,todo_app,Item,Category

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
    if session.get('islogin') is None:
        return 404
    if request.method == 'POST':
        body = request.form.get('item')
        category_id = request.form.get('category')
        category = Category.query.get_or_404(category_id)
        item = Item(body=body, category=category)
        db.session.add(item)
        db.session.commit()
        return redirect(f"/todo/category/{category.id}")
    return redirect(f"/todo/category/1")


@tcenter.route('/todo/category/<int:id>', methods=['GET', 'POST'])
def category(id):
    if session.get('islogin') is None:
        return 404
    category = Category.query.get_or_404(id)
    categories = Category.query.all()
    items = category.items
    return render_template('todo_index.html', items=items,
                           categories=categories, category_now=category)


@tcenter.route('/todo/new_category', methods=['GET', 'POST'])
def new_category():
    if session.get('islogin') is None:
        return 404
    # print("enter new_category")
    name = request.form.get('name')
    # print("enter new_category",name)
    category = Category(name=name)
    db.session.add(category)
    db.session.commit()
    return redirect(f"/todo/category/1")


@tcenter.route('/todo/edit_item/<int:id>', methods=['GET', 'POST'])
def edit_item(id):
    if session.get('islogin') is None:
        return 404
    print("edit_item",id)
    item = Item.query.get_or_404(id)
    category = item.category
    item.body = request.form.get('body')
    db.session.add(item)
    db.session.commit()
    return redirect(f"/todo/category/{category.id}")


@tcenter.route('/todo/edit_category/<int:id>', methods=['GET', 'POST'])
def edit_category(id):
    if session.get('islogin') is None:
        return 404
    print("edit_category",id)
    category = Category.query.get_or_404(id)
    category.name = request.form.get('name')
    db.session.add(category)
    db.session.commit()
    return redirect(f"/todo/category/1")


@tcenter.route('/todo/done/<int:id>', methods=['GET', 'POST'])
def done(id):
    if session.get('islogin') is None:
        return 404
    item = Item.query.get_or_404(id)
    category = item.category
    done_category = Category.query.get_or_404(2)
    done_item = Item(body=item.body, category=done_category)
    db.session.add(done_item)
    db.session.delete(item)
    db.session.commit()
    return redirect(f"/todo/category/{category.id}")


@tcenter.route('/todo/delete_item/<int:id>', methods=['GET', 'POST'])
def delete_item(id):
    if session.get('islogin') is None:
        return 404
    # print("del_item",id)
    item = Item.query.get_or_404(id)
    category = item.category
    if item is None:
        return redirect(f"/todo/category/1")
    db.session.delete(item)
    db.session.commit()
    return redirect(f"/todo/category/1")


@tcenter.route('/todo/delete_category/<int:id>',methods=['GET', 'POST'])
def delete_category(id):
    if session.get('islogin') is None:
        return 404
    category = Category.query.get_or_404(id)
    if category is None or id in [1, 2]:
        return redirect(f"/todo/category/1")
    db.session.delete(category)
    db.session.commit()
    return redirect(f"/todo/category/1")