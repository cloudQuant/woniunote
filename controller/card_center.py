from flask import Flask, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from woniunote.controller.user import *
from woniunote.utils import read_config
from woniunote.common.create_database import Card, CardCategory
import os
import time
import datetime

app = Flask(__name__)
# todo_app.config['SECRET_KEY'] = 'a secret string'
# todo_app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite://')
# todo_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24)
config_result = read_config()
SQLALCHEMY_DATABASE_URI = config_result['database']["SQLALCHEMY_DATABASE_URI"]
# 使用集成方式处理SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # True: 跟踪数据库的修改，及时发送信号
app.config['SQLALCHEMY_POOL_SIZE'] = 100  # 数据库连接池的大小。默认是数据库引擎的默认值（通常是 5）
# 实例化db对象
app.config['DEBUG'] = True
db = SQLAlchemy(app)

dbsession = db.session
DBase = db.Model

card_center = Blueprint("card_center", __name__)


# cal remain days from now


def cal_leave_day(target_date):
    if not target_date:
        return 0
    now_datetime = datetime.datetime.now()
    total_delta = target_date - now_datetime
    leave_days = total_delta.days
    leave_seconds = (target_date - now_datetime).seconds
    # print(leave_days,leave_seconds,now_datetime,target_date)
    return leave_days


@card_center.route('/cards/', methods=['GET', 'POST'])
def card_index():
    if session.get('islogin') is None:
        return 404
    # if request.method == 'POST':
    #     headline = request.form.get('card')
    #     category_id = request.form.get('cardcategory')
    #     category = CardCategory.query.get_or_404(category_id)
    #     card_item = Card(headline=headline, cardcategory=category)
    #     db.session.add(card_item)
    #     db.session.commit()
    #     return redirect(f"/cards/category/{category.id}")
    return redirect(f"/cards/category/1")


@card_center.route('/cards/add_new_card', methods=['GET', 'POST'])
def add_new_card():
    if session.get('islogin') is None:
        return 404
    # print(dir(request))
    if request.method == 'POST':
        headline = request.form.get('card_headline')
        card_date = request.form.get('card_date')
        category_id = request.form.get('category')
        card_type = request.form.get('card_type')
        now_time = datetime.datetime.now()
        # print(headline,card_date,category_id)
        card_category = CardCategory.query.get_or_404(category_id)
        card_item = Card(headline=headline,
                         createtime=now_time,
                         updatetime=card_date,
                         cardcategory=card_category,
                         usedtime=0,
                         type=card_type)
        db.session.add(card_item)
        db.session.commit()
        time.sleep(0.5)
        return redirect(f"/cards/category/{category_id}")
    return redirect(f"/cards/category/1")


@card_center.route('/cards/begin_card/<int:id>', methods=['GET', 'POST'])
def begin_card(card_id):
    if session.get('islogin') is None:
        return 404
    # print("begin_card ","run")
    card = Card.query.get_or_404(card_id)
    # print("Card.query.get_or_404 ","run")
    category_id = card.cardcategory_id
    # now_datetime = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())
    card.begintime = datetime.datetime.now()
    card.endtime = None
    db.session.add(card)
    db.session.commit()
    time.sleep(0.5)
    return redirect(f"/cards/category/{category_id}")


@card_center.route('/cards/end_card/<int:id>', methods=['GET', 'POST'])
def end_card(card_id):
    if session.get('islogin') is None:
        return 404
    time.sleep(0.5)
    card = Card.query.get_or_404(card_id)
    head_line = card.headline
    print(head_line)
    if "重复" in head_line:
        category_id = card.cardcategory_id
        now_time = datetime.datetime.now()
        # end_datetime = datetime.datetime.strftime("%Y-%m-%d %H:%M:%S",now_time)
        card.endtime = now_time
        begin_datetime = card.begintime
        # t2 = time.strptime(end_datetime,"%Y-%m-%d %H:%M:%S")
        if not card.usedtime:
            card.usedtime = 0
        # print("card.usedtime",card.usedtime)
        if not begin_datetime:
            total_seconds = 0
        else:
            total_seconds = (now_time - begin_datetime).seconds
        print("total_seconds", total_seconds)
        used_time = total_seconds + card.usedtime
        card.usedtime = used_time
        card.begintime = None
        card.endtime = now_time
        done_category = CardCategory.query.get_or_404(2)
        new_head_line = head_line.replace("重复", "")
        done_card = Card(headline=new_head_line, cardcategory=done_category,
                         begintime=None,
                         endtime=now_time,
                         donetime=now_time,
                         usedtime=(now_time - begin_datetime).seconds)
        db.session.add(done_card)
        db.session.commit()
        time.sleep(0.5)
        db.session.add(card)
        db.session.commit()
        time.sleep(0.5)
    else:
        category_id = card.cardcategory_id
        now_time = datetime.datetime.now()
        # end_datetime = datetime.datetime.strftime("%Y-%m-%d %H:%M:%S",now_time)
        card.endtime = now_time
        begin_datetime = card.begintime
        # t2 = time.strptime(end_datetime,"%Y-%m-%d %H:%M:%S")
        if not card.usedtime:
            card.usedtime = 0
        # print("card.usedtime",card.usedtime)
        if not begin_datetime:
            total_seconds = 0
        else:
            total_seconds = (now_time - begin_datetime).seconds
        print("total_seconds", total_seconds)
        used_time = total_seconds + card.usedtime
        card.usedtime = used_time
        card.begintime = None

        db.session.add(card)
        db.session.commit()
        time.sleep(0.5)

    return redirect(f"/cards/category/{category_id}")


@card_center.route('/cards/category/<int:id>', methods=['GET', 'POST'])
def category(card_id):
    if session.get('islogin') is None:
        return 404
    time.sleep(0.2)
    categories = []
    while not categories:
        try:
            categories = CardCategory.query.all()
        except Exception as e:
            print(f"CardCategory.query.all() run fail, {e}")
            categories = []
        time.sleep(0.2)
    all_cards = []
    for card_category in categories:
        now_cards = card_category.cards
        all_cards.extend(now_cards)

    if card_id == 2:
        card_category = CardCategory.query.get_or_404(2)
        items = card_category.cards
        category_name = card_category.name
        # 
        month_cards = {}
        for i in items:
            itme_done_time = int(str(i.donetime)[:4] + str(i.donetime)[5:7])
            if itme_done_time not in month_cards:
                month_cards[itme_done_time] = []
            else:
                month_cards[itme_done_time].append(i)

        month_list = sorted(list(month_cards.keys()))[::-1]
        new_items = month_cards[month_list[0]]
        return get_done_category(month_list[0])

    all_undone_cards = [card for card in all_cards if not card.donetime]
    # all_undone_cards = [[x.updatetime,x] for  x in all_undone_cards]
    # all_undone_cards = sorted(all_undone_cards,key = lambda x:x[0])
    # all_undone_cards = [x[1] for x in all_undone_cards ]
    all_undone_cards = sorted(all_undone_cards, key=lambda x: getattr(x, "updatetime"))
    # print([i.updatetime for i in all_undone_cards])
    all_begin_cards = [card for card in all_cards if card.begintime]
    # print(all_undone_cards)
    type_1_cards = [i for i in all_undone_cards if i.type == 1]
    type_2_cards = [i for i in all_undone_cards if i.type == 2]
    type_3_cards = [i for i in all_undone_cards if i.type == 3]
    type_4_cards = [i for i in all_undone_cards if i.type == 4]
    # ["不重要不紧急","紧急不重要","重要不紧急","重要紧急"]
    types_cards = {"重要紧急": type_1_cards, "重要不紧急": type_2_cards,
                   "紧急不重要": type_3_cards, "不重要不紧急": type_4_cards,
                   "已开始清单": all_begin_cards}
    day_cards = []
    week_cards = []
    month_cards = []
    year_cards = []
    ten_year_cards = []
    for card in all_undone_cards:
        leave_day = cal_leave_day(card.updatetime)
        # print(card,card.headline,card.updatetime,leave_day)
        if leave_day <= 1:
            day_cards.append(card)
        if 1 < leave_day <= 7:
            week_cards.append(card)
        if 7 < leave_day <= 30:
            month_cards.append(card)
        if 30 < leave_day <= 365:
            year_cards.append(card)
        if leave_day > 365:
            ten_year_cards.append(card)
    times_cards = {"日清单": day_cards, "周清单": week_cards,
                   "月清单": month_cards, "年清单": year_cards, "十年清单": ten_year_cards}

    card_category = CardCategory.query.get_or_404(id)
    items = card_category.cards
    items = sorted(items, key=lambda x: getattr(x, "updatetime"))
    category_name = card_category.name
    if category_name in ["日清单", "周清单", "月清单", "年清单", "十年清单"]:
        # print("true,ri day")
        items = times_cards[category_name]
    if category_name in ["不重要不紧急", "紧急不重要", "重要不紧急", "重要紧急"]:
        items = types_cards[category_name]
    important_cards = type_1_cards + type_2_cards
    if card_id == 1:
        if len(type_1_cards) + len(type_2_cards) > 0:
            items = important_cards

    if category_name == "已开始清单":
        items = all_begin_cards
    # print("calling category/id",category_name,items,times_cards,types_cards,category.name)
    return render_template('card_index.html', items=items,
                           categories=categories,
                           category_now=card_category,
                           types_cards=types_cards,
                           times_cards=times_cards,
                           all_begin_cards=all_begin_cards,
                           important_cards=important_cards,
                           )


@card_center.route('/cards/category/2/<int:year_month>', methods=['GET', 'POST'])
def get_done_category(year_month):
    if session.get('islogin') is None:
        return 404
    time.sleep(0.2)
    # year,month = year_month.split("_")
    categories = []
    while not categories:
        try:
            categories = CardCategory.query.all()
        except Exception as e:
            print(f"CardCategory.query.all() run fail, {e}")
            categories = []
        time.sleep(0.2)
    all_cards = []
    for card_category in categories:
        now_cards = card_category.cards
        all_cards.extend(now_cards)
    all_undone_cards = [card for card in all_cards if not card.donetime]
    all_begin_cards = [card for card in all_cards if card.begintime]
    # print(all_undone_cards)
    type_1_cards = [i for i in all_undone_cards if i.type == 1]
    type_2_cards = [i for i in all_undone_cards if i.type == 2]
    type_3_cards = [i for i in all_undone_cards if i.type == 3]
    type_4_cards = [i for i in all_undone_cards if i.type == 4]
    # ["不重要不紧急","紧急不重要","重要不紧急","重要紧急"]
    types_cards = {"重要紧急": type_1_cards, "重要不紧急": type_2_cards,
                   "紧急不重要": type_3_cards, "不重要不紧急": type_4_cards,
                   "已开始清单": all_begin_cards}
    day_cards = []
    week_cards = []
    month_cards = []
    year_cards = []
    ten_year_cards = []
    for card in all_undone_cards:
        leave_day = cal_leave_day(card.updatetime)
        # print(card,card.headline,card.updatetime,leave_day)
        if leave_day <= 1:
            day_cards.append(card)
        if 1 < leave_day <= 7:
            week_cards.append(card)
        if 7 < leave_day <= 30:
            month_cards.append(card)
        if 30 < leave_day <= 365:
            year_cards.append(card)
        if leave_day > 365:
            ten_year_cards.append(card)
    times_cards = {"日清单": day_cards, "周清单": week_cards,
                   "月清单": month_cards, "年清单": year_cards, "十年清单": ten_year_cards}

    card_category = CardCategory.query.get_or_404(2)
    items = card_category.cards
    category_name = card_category.name
    # 
    month_cards = {}
    for i in items:
        itme_done_time = int(str(i.donetime)[:4] + str(i.donetime)[5:7])
        if itme_done_time not in month_cards:
            month_cards[itme_done_time] = []
        else:
            month_cards[itme_done_time].append(i)
    new_items = month_cards[year_month]
    new_items = new_items[::-1]
    month_list = sorted(list(month_cards.keys()))[::-1]

    if category_name in ["日清单", "周清单", "月清单", "年清单", "十年清单"]:
        # print("true,ri day")
        items = times_cards[category_name]

    if category_name in ["不重要不紧急", "紧急不重要", "重要不紧急", "重要紧急"]:
        items = types_cards[category_name]

    important_cards = type_1_cards + type_2_cards
    if id == 1:
        if len(type_1_cards) + len(type_2_cards) > 0:
            items = important_cards
    if category_name == "已开始清单":
        items = all_begin_cards
    # print("calling category/id",category_name,items,times_cards,types_cards,category.name)
    return render_template('card_done_index.html', items=new_items, year_month=year_month,
                           categories=categories,
                           category_now=card_category,
                           types_cards=types_cards,
                           times_cards=times_cards,
                           all_begin_cards=all_begin_cards,
                           important_cards=important_cards,
                           month_cards=month_cards,
                           month_list=month_list,
                           )


@card_center.route('/cards/new_category', methods=['GET', 'POST'])
def new_category():
    if session.get('islogin') is None:
        return 404
    # print("enter new_category")
    name = request.form.get('name')
    # print("enter new_category",name)
    card_category = CardCategory(name=name)
    db.session.add(category)
    db.session.commit()
    time.sleep(0.2)
    return redirect(f"/cards/category/{card_category.id}")


@card_center.route('/cards/edit_card/<int:id>', methods=['GET', 'POST'])
def edit_card(card_id):
    if session.get('islogin') is None:
        return 404

    card_0 = Card.query.get_or_404(card_id)
    # print(id,card.id,card.headline)
    time.sleep(0.2)
    categories = CardCategory.query.all()
    all_cards = []
    for card_category in categories:
        now_cards = card_category.cards
        all_cards.extend(now_cards)
    all_undone_cards = [card for card in all_cards if not card.donetime]
    type_1_cards = [i for i in all_undone_cards if i.type == 1]
    type_2_cards = [i for i in all_undone_cards if i.type == 2]
    type_3_cards = [i for i in all_undone_cards if i.type == 3]
    type_4_cards = [i for i in all_undone_cards if i.type == 4]
    # ["不重要不紧急","紧急不重要","重要不紧急","重要紧急"]
    types_cards = {"重要紧急": type_1_cards, "重要不紧急": type_2_cards,
                   "紧急不重要": type_3_cards, "不重要不紧急": type_4_cards}
    day_cards = []
    week_cards = []
    month_cards = []
    year_cards = []
    ten_year_cards = []
    for card in all_undone_cards:
        leave_day = cal_leave_day(card.updatetime)
        # print(card,card.headline,card.updatetime,leave_day)
        if leave_day <= 1:
            day_cards.append(card)
        if 1 < leave_day <= 7:
            week_cards.append(card)
        if 7 < leave_day <= 30:
            month_cards.append(card)
        if 30 < leave_day <= 365:
            year_cards.append(card)
        if leave_day > 365:
            ten_year_cards.append(card)
    times_cards = {"日清单": day_cards, "周清单": week_cards,
                   "月清单": month_cards, "年清单": year_cards, "十年清单": ten_year_cards}

    card_category = card_0.cardcategory
    items = card_category.cards
    category_name = card_category.name
    if category_name in ["日清单", "周清单", "月清单", "年清单", "十年清单"]:
        # print("true,ri day")
        items = times_cards[category_name]
    if category_name in ["不重要不紧急", "紧急不重要", "重要不紧急", "重要紧急"]:
        items = types_cards[category_name]
    important_cards = type_1_cards + type_2_cards

    if card_id == 1:
        if len(type_1_cards) + len(type_2_cards) > 0:
            items = important_cards
    # print("calling edit card",id, card_0.id, card_0.headline, category_name)
    return render_template('card_edit.html', card=card_0,
                           items=items,
                           categories=categories,
                           category_now=card_category,
                           types_cards=types_cards,
                           times_cards=times_cards,
                           important_cards=important_cards, )


@card_center.route('/cards/edit_item/<int:id>', methods=['GET', 'POST'])
def edit_item(card_id):
    if session.get('islogin') is None:
        return 404
    # print("edit_item",id)
    card = Card.query.get_or_404(card_id)
    # print("card_category_id",card.cardcategory_id)
    category_id = request.form.get('category_id')
    # print("new_card_category_id",category_id)
    headline = request.form.get('headline')
    createtime = request.form.get('createtime')
    updatetime = request.form.get('updatetime')
    donetime = request.form.get('donetime')
    begintime = request.form.get('begintime')
    endtime = request.form.get('endtime')
    usedtime = request.form.get('usedtime')
    card_type = request.form.get('card_type')
    content = request.form.get('content')
    if headline != "None":
        card.headline = headline
    if createtime != "None":
        card.createtime = createtime
    if updatetime != "None":
        card.updatetime = updatetime
    if donetime != "None":
        # print("run donetime",donetime)
        card.donetime = donetime
    else:
        card.donetime = None

    if begintime != "None":
        card.begintime = begintime
    else:
        card.begintime = None

    if endtime != "None":
        card.endtime = endtime
    else:
        card.endtime = None

    if card_type != "None":
        card.type = card_type

    if usedtime != "None":
        # print(" run usedtime")
        card.usedtime = usedtime

    if content != "None":
        card.content = content

    if category_id != "None":
        card.cardcategory_id = category_id

    db.session.add(card)
    db.session.commit()
    time.sleep(0.5)
    return redirect(f"/cards/category/{category_id}")


@card_center.route('/cards/edit_category/<int:id>', methods=['GET', 'POST'])
def edit_category(card_id):
    if session.get('islogin') is None:
        return 404
    # print("edit_category",id)
    card_category = CardCategory.query.get_or_404(card_id)
    card_category.name = request.form.get('name')
    db.session.add(card_category)
    db.session.commit()
    time.sleep(0.2)
    return redirect(f"/cards/category/1")


@card_center.route('/cards/done/<int:id>', methods=['GET', 'POST'])
def done(card_id):
    if session.get('islogin') is None:
        return 404
    card = Card.query.get_or_404(card_id)
    category_id = card.cardcategory_id
    now_time = datetime.datetime.now()
    begintime = card.begintime
    endtime = card.endtime
    usedtime = card.usedtime
    done_category = CardCategory.query.get_or_404(2)
    done_card = Card(headline=card.headline, cardcategory=done_category,
                     begintime=begintime,
                     endtime=endtime,
                     donetime=now_time,
                     usedtime=usedtime)
    db.session.add(done_card)
    db.session.delete(card)
    db.session.commit()
    time.sleep(0.2)
    return redirect(f"/cards/category/{category_id}")


@card_center.route('/cards/delete_item/<int:id>', methods=['GET', 'POST'])
def delete_item(card_id):
    if session.get('islogin') is None:
        return 404
    # print("del_item",id)
    item = Card.query.get_or_404(card_id)
    category_id = item.cardcategory_id
    if item is None:
        return redirect(f"/cards/category/1")
    db.session.delete(item)
    db.session.commit()
    time.sleep(0.2)
    return redirect(f"/cards/category/1")


@card_center.route('/cards/delete_category/<int:id>', methods=['GET', 'POST'])
def delete_category(card_id):
    if session.get('islogin') is None:
        return 404
    card_category = CardCategory.query.get_or_404(card_id)
    if card_category is None or card_id in [1, 2]:
        return redirect(f"/cards/category/1")
    db.session.delete(card_category)
    db.session.commit()
    time.sleep(0.2)
    return redirect(f"/cards/category/1")


if __name__ == "__main__":
    pass
