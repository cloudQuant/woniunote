from flask import render_template, redirect, abort, jsonify, current_app
from woniunote.controller.user import *
from woniunote.common.database import db
from woniunote.models.card import Card, CardCategory
from woniunote.common.simple_logger import get_simple_logger
from functools import wraps
import datetime
import time
import uuid
import traceback

card_center = Blueprint("card_center", __name__)

# 初始化日志记录器
card_logger = get_simple_logger('card_controller')

# 生成跟踪ID
def generate_card_trace_id():
    return str(uuid.uuid4())

# 获取当前跟踪ID
_card_thread_local_trace_id = {}
def get_card_trace_id():
    if 'trace_id' not in _card_thread_local_trace_id:
        _card_thread_local_trace_id['trace_id'] = generate_card_trace_id()
    return _card_thread_local_trace_id['trace_id']

# Decorator for requiring login
def login_required(f):
    """Decorator to check if user is logged in before accessing card functions"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 生成跟踪ID
        trace_id = get_card_trace_id()
        
        if session.get('main_islogin') is None:
            # 记录未授权访问尝试
            card_logger.warning("未授权访问卡片管理功能", {
                'trace_id': trace_id,
                'function': f.__name__,
                'remote_addr': request.remote_addr,
                'path': request.path,
                'method': request.method
            })
            abort(404)
        
        # 记录授权访问
        card_logger.info("访问卡片管理功能", {
            'trace_id': trace_id,
            'function': f.__name__,
            'user_id': session.get('main_userid'),
            'remote_addr': request.remote_addr,
            'path': request.path,
            'method': request.method
        })
        
        return f(*args, **kwargs)
    return decorated_function

# Decorator for database error handling
def db_error_handler(f):
    """Decorator to handle database errors consistently"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 生成跟踪ID
        trace_id = get_card_trace_id()
        
        try:
            return f(*args, **kwargs)
        except Exception as e:
            # 回滚数据库事务
            db.session.rollback()
            
            # 记录数据库错误
            card_logger.error("卡片管理数据库错误", {
                'trace_id': trace_id,
                'function': f.__name__,
                'user_id': session.get('main_userid'),
                'remote_addr': request.remote_addr,
                'path': request.path,
                'method': request.method,
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            
            # 返回用户友好的错误信息
            return jsonify({"error": "处理请求时发生错误。请稍后再试。"}), 500
    return decorated_function


def cal_leave_day(target_date):
    """Calculate the number of days that have passed since the target_date.
    
    Args:
        target_date (datetime): The reference date to calculate days from
        
    Returns:
        int: Number of days passed (non-negative). Returns 0 if target_date is None.
    """
    # 生成跟踪ID
    trace_id = get_card_trace_id()
    
    # 检查目标日期是否有效
    if not target_date:
        # 记录无效日期
        card_logger.debug("计算天数差异失败", {
            'trace_id': trace_id,
            'reason': 'target_date_is_none',
            'result': 0
        })
        return 0
    
    # 计算天数差异
    now_datetime = datetime.datetime.now()
    total_delta = now_datetime - target_date
    days_passed = total_delta.days
    
    # 确保返回非负值
    result = max(0, days_passed)
    
    # 记录计算结果
    card_logger.debug("计算天数差异成功", {
        'trace_id': trace_id,
        'target_date': str(target_date),
        'now_datetime': str(now_datetime),
        'days_passed': days_passed,
        'result': result
    })
    
    return result


@card_center.route('/cards/', methods=['GET', 'POST'])
@login_required
def card_index():
    """Main entry point for the card management functionality.
    
    Returns:
        Response: Redirects to the default category view.
    """
    # 生成跟踪ID
    trace_id = get_card_trace_id()
    
    # 记录访问信息
    card_logger.info("访问卡片管理首页", {
        'trace_id': trace_id,
        'user_id': session.get('main_userid'),
        'remote_addr': request.remote_addr
    })
    
    return redirect(f"/cards/category/1")


@card_center.route('/cards/add_new_card', methods=['GET', 'POST'])
@login_required
@db_error_handler
def add_new_card():
    """Add a new card to the system.
    
    POST parameters:
        card_headline: Title of the card
        card_date: Date for the card
        category: Category ID for the card
        card_type: Type of card
        
    Returns:
        Response: Redirects to the category page after creation
    """
    # 生成跟踪ID
    trace_id = get_card_trace_id()
    
    if request.method == 'POST':
        headline = request.form.get('card_headline')
        card_date = request.form.get('card_date')
        category_id = request.form.get('category')
        card_type = request.form.get('card_type')
        now_time = datetime.datetime.now()
        
        # 记录创建新卡片的请求
        card_logger.info("创建新卡片", {
            'trace_id': trace_id,
            'user_id': session.get('main_userid'),
            'headline': headline,
            'category_id': category_id,
            'card_type': card_type,
            'card_date': card_date
        })
        
        # 获取卡片分类
        card_category = CardCategory.query.get_or_404(category_id)
        
        # 创建新卡片
        card_item = Card(headline=headline,
                         createtime=now_time,
                         updatetime=card_date,
                         cardcategory=card_category,
                         usedtime=0,
                         type=card_type)
        db.session.add(card_item)
        db.session.commit()
        
        # 记录创建成功
        card_logger.info("卡片创建成功", {
            'trace_id': trace_id,
            'user_id': session.get('main_userid'),
            'headline': headline,
            'category_id': category_id,
            'card_id': card_item.id
        })
        
        return redirect(f"/cards/category/{category_id}")
    
    # 如果不是POST请求，重定向到默认分类
    card_logger.info("非POST请求访问添加卡片页面", {
        'trace_id': trace_id,
        'user_id': session.get('main_userid'),
        'method': request.method
    })
    
    return redirect(f"/cards/category/1")


@card_center.route('/cards/begin_card/<int:card_id>', methods=['GET', 'POST'])
@login_required
@db_error_handler
def begin_card(card_id):
    """Mark a card as started by setting its begin time.
    
    Args:
        card_id (int): ID of the card to start
        
    Returns:
        Response: Redirects to the category page after updating
    """
    # 生成跟踪ID
    trace_id = get_card_trace_id()
    
    # 记录开始卡片的请求
    card_logger.info("开始卡片任务", {
        'trace_id': trace_id,
        'user_id': session.get('main_userid'),
        'card_id': card_id,
        'remote_addr': request.remote_addr
    })
    
    # 获取卡片
    card = Card.query.get_or_404(card_id)
    category_id = card.cardcategory_id
    
    # 记录卡片信息
    card_logger.info("卡片信息", {
        'trace_id': trace_id,
        'card_id': card_id,
        'headline': card.headline,
        'category_id': category_id,
        'already_started': card.begintime is not None
    })
    
    # 设置开始时间（如果还没有设置）
    if not card.begintime:
        now_time = datetime.datetime.now()
        card.begintime = now_time
        db.session.add(card)
        db.session.commit()
        
        # 记录卡片开始成功
        card_logger.info("卡片开始成功", {
            'trace_id': trace_id,
            'card_id': card_id,
            'headline': card.headline,
            'begin_time': now_time.strftime('%Y-%m-%d %H:%M:%S')
        })
    else:
        # 记录卡片已经开始
        card_logger.info("卡片已经开始", {
            'trace_id': trace_id,
            'card_id': card_id,
            'headline': card.headline,
            'begin_time': card.begintime.strftime('%Y-%m-%d %H:%M:%S') if card.begintime else None
        })
    
    return redirect(f"/cards/category/{category_id}")


@card_center.route('/cards/end_card/<int:card_id>', methods=['GET', 'POST'])
@login_required
@db_error_handler
def end_card(card_id):
    """Mark a card as ended by setting its end time and calculating usage time.
    
    For cards with "重复" (repeat) in the title, this creates a completed version in the done category
    and keeps the original for future use.
    
    Args:
        card_id (int): ID of the card to end
        
    Returns:
        Response: Redirects to the category page after updating
    """
    # 生成跟踪ID
    trace_id = get_card_trace_id()
    
    # 记录结束卡片的请求
    card_logger.info("结束卡片任务", {
        'trace_id': trace_id,
        'user_id': session.get('main_userid'),
        'card_id': card_id,
        'remote_addr': request.remote_addr
    })
    
    # 获取卡片
    card = Card.query.get_or_404(card_id)
    head_line = card.headline
    category_id = card.cardcategory_id
    now_time = datetime.datetime.now()
    
    # 记录卡片信息
    card_logger.info("卡片结束信息", {
        'trace_id': trace_id,
        'card_id': card_id,
        'headline': head_line,
        'category_id': category_id,
        'has_begin_time': card.begintime is not None
    })
    
    # 设置结束时间
    card.endtime = now_time
    begin_datetime = card.begintime
    
    # 初始化使用时间（如果未设置）
    if not card.usedtime:
        card.usedtime = 0
    
    # 计算使用时间
    if not begin_datetime:
        total_seconds = 0
    else:
        total_seconds = (now_time - begin_datetime).seconds
    
    # 记录使用时间
    card_logger.info("卡片使用时间", {
        'trace_id': trace_id,
        'card_id': card_id,
        'headline': head_line,
        'total_seconds': total_seconds,
        'previous_used_time': card.usedtime
    })
    
    # 更新使用时间
    used_time = total_seconds + card.usedtime
    card.usedtime = used_time
    card.begintime = None
    
    # 特殊处理重复卡片
    if "重复" in head_line:
        card_logger.info("处理重复卡片", {
            'trace_id': trace_id,
            'card_id': card_id,
            'headline': head_line,
            'category_id': category_id
        })
        
        # 在完成分类中创建完成版本
        done_category = CardCategory.query.get_or_404(2) # 完成分类ID为2
        new_head_line = head_line.replace("重复", "")
        
        done_card = Card(headline=new_head_line, 
                          cardcategory=done_category,
                          begintime=None,
                          endtime=now_time,
                          donetime=now_time,
                          usedtime=(now_time - begin_datetime).seconds if begin_datetime else 0)
        
        db.session.add(done_card)
        db.session.add(card)
        db.session.commit()
        
        # 记录重复卡片处理成功
        card_logger.info("重复卡片处理成功", {
            'trace_id': trace_id,
            'original_card_id': card_id,
            'new_card_id': done_card.id,
            'headline': new_head_line,
            'used_time': done_card.usedtime
        })
    else:
        # 普通卡片结束
        db.session.add(card)
        db.session.commit()
        
        # 记录普通卡片结束成功
        card_logger.info("普通卡片结束成功", {
            'trace_id': trace_id,
            'card_id': card_id,
            'headline': head_line,
            'used_time': card.usedtime
        })
    
    return redirect(f"/cards/category/{category_id}")


@card_center.route('/cards/category/<int:card_id>', methods=['GET', 'POST'])
@login_required
@db_error_handler
def category(card_id):
    """Display card category view with filtering based on category type.
    
    This function handles the main card viewing interface, applying
    different filters based on the category type (time-based, priority-based).
    
    Args:
        card_id (int): ID of the category to display
        
    Returns:
        Response: Renders the card_index.html template with filtered cards
    """
    # 生成跟踪ID
    trace_id = get_card_trace_id()
    
    # 记录访问分类页面
    card_logger.info("访问卡片分类页面", {
        'trace_id': trace_id,
        'user_id': session.get('main_userid'),
        'category_id': card_id,
        'remote_addr': request.remote_addr
    })
    
    # 特殊处理已完成分类
    if card_id == 2:  # ID 2是'已完成'分类
        card_logger.info("访问已完成分类", {
            'trace_id': trace_id,
            'user_id': session.get('main_userid')
        })
        return _handle_done_category()
    
    # 获取所有分类
    categories = CardCategory.query.all()
    if not categories:
        card_logger.error("获取卡片分类失败", {
            'trace_id': trace_id,
            'user_id': session.get('main_userid')
        })
        return jsonify({"error": "无法加载分类"}), 500
    
    # 获取当前分类
    card_category = CardCategory.query.get_or_404(card_id)
    
    # 记录当前分类信息
    card_logger.info("当前分类信息", {
        'trace_id': trace_id,
        'category_id': card_id,
        'category_name': card_category.name,
        'category_type': card_category.type
    })
    category_name = card_category.name
    
    # Process all cards and create filtered collections
    card_collections = _prepare_card_collections(categories)
    
    # Select the appropriate items based on category
    items = _select_items_for_category(card_category, card_collections, card_id)
    
    # Ensure all dictionaries have safe default values
    times_cards = card_collections['times_cards']
    types_cards = card_collections['types_cards']
    _ensure_safe_defaults(categories, times_cards, types_cards)
    
    # Render the template with all necessary data
    return render_template('card_index.html', 
                          items=items,
                          categories=categories,
                          category_now=card_category,
                          types_cards=types_cards,
                          times_cards=times_cards,
                          all_begin_cards=card_collections['all_begin_cards'],
                          important_cards=card_collections['important_cards'])


def _handle_done_category():
    """Handle the 'Done' category view (card_id = 2).
    
    Groups completed cards by month and redirects to the view
    for the most recent month.
    
    Returns:
        Response: Redirects to the appropriate month view
    """
    # 生成跟踪ID
    trace_id = get_card_trace_id()
    
    # 记录访问已完成分类
    card_logger.info("处理已完成卡片分类", {
        'trace_id': trace_id,
        'user_id': session.get('main_userid'),
        'remote_addr': request.remote_addr
    })
    
    # 获取已完成分类
    done_category = CardCategory.query.get_or_404(2)
    done_items = done_category.cards
    
    # 记录已完成卡片数量
    card_logger.info("已完成卡片数量", {
        'trace_id': trace_id,
        'total_done_cards': len(done_items)
    })
    
    # 按月分组卡片
    month_cards = {}
    for card in done_items:
        if not card.donetime:
            continue
            
        try:
            item_done_time = int(str(card.donetime)[:4] + str(card.donetime)[5:7])
            if item_done_time not in month_cards:
                month_cards[item_done_time] = []
            month_cards[item_done_time].append(card)
        except (ValueError, TypeError, IndexError) as e:
            card_logger.warning("处理卡片完成时间错误", {
                'trace_id': trace_id,
                'card_id': card.id,
                'headline': card.headline,
                'error': str(e)
            })
    
    # 记录按月分组结果
    card_logger.info("按月分组卡片结果", {
        'trace_id': trace_id,
        'month_count': len(month_cards),
        'months': list(month_cards.keys())
    })
    
    # 如果没有卡片有完成时间，返回空页面
    if not month_cards:
        card_logger.info("未找到已完成卡片", {
            'trace_id': trace_id
        })
        return render_template('card_index.html', 
                              items=[],
                              categories=CardCategory.query.all(),
                              category_now=done_category,
                              types_cards={},
                              times_cards={},
                              all_begin_cards=[],
                              important_cards=[])
    
    # Get the most recent month
    month_list = sorted(list(month_cards.keys()), reverse=True)
    return get_done_category(month_list[0])


def _prepare_card_collections(categories):
    """Prepare various card collections for filtering.
    
    Categorizes cards by type, time periods, and started status.
    
    Args:
        categories (list): List of all CardCategory objects
        
    Returns:
        dict: Dictionary containing various card collections
    """
    # 生成跟踪ID
    trace_id = get_card_trace_id()
    
    # 收集所有卡片
    all_cards = []
    for category in categories:
        all_cards.extend(category.cards)
    
    # 记录总卡片数量
    card_logger.info("卡片总数量", {
        'trace_id': trace_id,
        'total_cards': len(all_cards)
    })
    
    # 过滤并排序未完成卡片
    all_undone_cards = [card for card in all_cards if not card.donetime]
    all_undone_cards = sorted(all_undone_cards, key=lambda x: getattr(x, "updatetime"))
    
    # 过滤已开始的卡片
    all_begin_cards = [card for card in all_cards if card.begintime]
    
    # 按优先级类型分组卡片
    type_1_cards = [card for card in all_undone_cards if card.type == 1]
    type_2_cards = [card for card in all_undone_cards if card.type == 2]
    type_3_cards = [card for card in all_undone_cards if card.type == 3]
    type_4_cards = [card for card in all_undone_cards if card.type == 4]
    
    # 记录各类型卡片数量
    card_logger.info("卡片分类统计", {
        'trace_id': trace_id,
        'undone_cards': len(all_undone_cards),
        'begin_cards': len(all_begin_cards),
        'type_1_cards': len(type_1_cards),
        'type_2_cards': len(type_2_cards),
        'type_3_cards': len(type_3_cards),
        'type_4_cards': len(type_4_cards)
    })
    
    # 创建基于优先级的分类字典
    types_cards = {
        "重要紧急": type_1_cards, 
        "重要不紧急": type_2_cards,
        "紧急不重要": type_3_cards, 
        "不重要不紧急": type_4_cards,
        "已开始清单": all_begin_cards
    }
    
    # 创建基于时间的分类
    time_categories = _categorize_cards_by_time(all_undone_cards)
    
    # 合并重要卡片
    important_cards = type_1_cards + type_2_cards
    
    # 记录卡片集合准备完成
    card_logger.info("卡片集合准备完成", {
        'trace_id': trace_id,
        'important_cards': len(important_cards),
        'time_categories': len(time_categories)
    })
    
    return {
        'all_undone_cards': all_undone_cards,
        'all_begin_cards': all_begin_cards,
        'types_cards': types_cards,
        'times_cards': time_categories,
        'important_cards': important_cards
    }


def _categorize_cards_by_time(all_undone_cards):
    """Categorize cards by time periods based on updatetime.
    
    Args:
        all_undone_cards (list): List of cards that are not completed
        
    Returns:
        dict: Dictionary mapping time category names to card lists
    """
    # 生成跟踪ID
    trace_id = get_card_trace_id()
    
    # 初始化各时间分类的卡片列表
    day_cards = []
    week_cards = []
    month_cards = []
    year_cards = []
    ten_year_cards = []
    
    # 记录开始分类
    card_logger.info("开始按时间分类卡片", {
        'trace_id': trace_id,
        'total_cards': len(all_undone_cards)
    })
    
    # 分类卡片
    for card in all_undone_cards:
        leave_day = cal_leave_day(card.updatetime)
        
        if leave_day <= 1:
            day_cards.append(card)
        elif 1 < leave_day <= 7:
            week_cards.append(card)
        elif 7 < leave_day <= 30:
            month_cards.append(card)
        elif 30 < leave_day <= 365:
            year_cards.append(card)
        else:  # leave_day > 365
            ten_year_cards.append(card)
    
    # 记录分类结果
    card_logger.info("按时间分类卡片结果", {
        'trace_id': trace_id,
        'day_cards': len(day_cards),
        'week_cards': len(week_cards),
        'month_cards': len(month_cards),
        'year_cards': len(year_cards),
        'ten_year_cards': len(ten_year_cards)
    })
    
    # 返回分类结果
    return {
        "日清单": day_cards, 
        "周清单": week_cards,
        "月清单": month_cards, 
        "年清单": year_cards, 
        "十年清单": ten_year_cards
    }


def _select_items_for_category(card_category, card_collections, card_id):
    """Select the appropriate items for the given category.
    
    Args:
        card_category (CardCategory): The current category object
        card_collections (dict): Dictionary of card collections
        card_id (int): ID of the current category
        
    Returns:
        list: The filtered list of cards to display
    """
    # 生成跟踪ID
    trace_id = get_card_trace_id()
    
    category_name = card_category.name
    
    # 记录开始选择卡片
    card_logger.info("选择分类卡片", {
        'trace_id': trace_id,
        'category_id': card_id,
        'category_name': category_name
    })
    
    # 开始使用该分类中的卡片
    items = card_category.cards
    items = sorted(items, key=lambda x: getattr(x, "updatetime"))
    
    # 记录原始卡片数量
    card_logger.info("分类原始卡片", {
        'trace_id': trace_id,
        'category_id': card_id,
        'category_name': category_name,
        'original_items_count': len(items)
    })
    
    # 根据分类名称应用特殊过滤
    time_categories = ["日清单", "周清单", "月清单", "年清单", "十年清单"]
    priority_categories = ["不重要不紧急", "紧急不重要", "重要不紧急", "重要紧急"]
    
    # 处理基于时间的分类
    if category_name in time_categories:
        items = card_collections['times_cards'].get(category_name, [])
        card_logger.info("选择时间分类卡片", {
            'trace_id': trace_id,
            'category_name': category_name,
            'items_count': len(items)
        })
        
    # 处理基于优先级的分类
    elif category_name in priority_categories:
        items = card_collections['types_cards'].get(category_name, [])
        card_logger.info("选择优先级分类卡片", {
            'trace_id': trace_id,
            'category_name': category_name,
            'items_count': len(items)
        })
        
    # 处理默认视图的特殊情况（card_id = 1）
    elif card_id == 1 and len(card_collections['important_cards']) > 0:
        items = card_collections['important_cards']
        card_logger.info("选择重要卡片", {
            'trace_id': trace_id,
            'category_id': card_id,
            'items_count': len(items)
        })
        
    # 处理已开始卡片列表
    elif category_name == "已开始清单":
        items = card_collections['all_begin_cards']
        card_logger.info("选择已开始卡片", {
            'trace_id': trace_id,
            'category_name': category_name,
            'items_count': len(items)
        })
    
    # 记录最终选择结果
    card_logger.info("卡片选择结果", {
        'trace_id': trace_id,
        'category_id': card_id,
        'category_name': category_name,
        'final_items_count': len(items)
    })
        
    return items


def _ensure_safe_defaults(categories, times_cards, types_cards):
    """Ensure all dictionaries have safe default values to prevent KeyError.
    
    Args:
        categories (list): List of all CardCategory objects
        times_cards (dict): Dictionary of time-based card collections
        types_cards (dict): Dictionary of priority-based card collections
    """
    # 生成跟踪ID
    trace_id = get_card_trace_id()
    
    # 记录开始确保安全默认值
    card_logger.info("确保卡片分类安全默认值", {
        'trace_id': trace_id,
        'categories_count': len(categories),
        'times_cards_count': len(times_cards),
        'types_cards_count': len(types_cards)
    })
    
    time_categories = ["日清单", "周清单", "月清单", "年清单", "十年清单"]
    priority_categories = ["不重要不紧急", "紧急不重要", "重要不紧急", "重要紧急", "已开始清单"]
    
    # 记录缺失的分类
    missing_time_categories = []
    missing_priority_categories = []
    
    for category in categories:
        # 确保时间分类存在
        if category.name in time_categories and category.name not in times_cards:
            times_cards[category.name] = []
            missing_time_categories.append(category.name)
            
        # 确保优先级分类存在
        if category.name in priority_categories and category.name not in types_cards:
            types_cards[category.name] = []
            missing_priority_categories.append(category.name)
    
    # 记录添加的默认值
    if missing_time_categories or missing_priority_categories:
        card_logger.info("添加缺失的分类默认值", {
            'trace_id': trace_id,
            'missing_time_categories': missing_time_categories,
            'missing_priority_categories': missing_priority_categories
        })


@card_center.route('/cards/category/2/<int:year_month>', methods=['GET', 'POST'])
@login_required
@db_error_handler
def get_done_category(year_month):
    """Display done cards filtered by year and month.
    
    This view shows completed cards for a specific year_month (format: YYYYMM).
    It provides navigation between different months of completed cards.
    
    Args:
        year_month (int): Year and month as a combined integer (YYYYMM format)
        
    Returns:
        Response: Renders the card_done_index.html template with the filtered cards
    """
    # 生成跟踪ID
    trace_id = get_card_trace_id()
    
    # 记录访问已完成卡片
    card_logger.info("查看已完成卡片", {
        'trace_id': trace_id,
        'user_id': session.get('main_userid'),
        'year_month': year_month,
        'remote_addr': request.remote_addr
    })
    
    # 获取所有分类
    categories = CardCategory.query.all()
    if not categories:
        card_logger.error("获取卡片分类失败", {
            'trace_id': trace_id,
            'user_id': session.get('main_userid')
        })
        return jsonify({"error": "无法加载分类"}), 500
    
    # 处理所有卡片并创建过滤集合
    card_collections = _prepare_card_collections(categories)
    
    # 获取已完成分类（ID 2）
    done_category = CardCategory.query.get_or_404(2)
    done_items = done_category.cards
    
    # 记录已完成卡片数量
    card_logger.info("已完成卡片数量", {
        'trace_id': trace_id,
        'total_done_cards': len(done_items)
    })
    
    # 按月分组已完成卡片
    month_cards_dict = _group_done_cards_by_month(done_items)
    
    # 记录按月分组结果
    card_logger.info("已完成卡片按月分组结果", {
        'trace_id': trace_id,
        'month_count': len(month_cards_dict),
        'months': list(month_cards_dict.keys()),
        'requested_month': year_month
    })
    
    # 处理缺失的年月
    if year_month not in month_cards_dict:
        card_logger.warning("请求的年月在已完成卡片中未找到", {
            'trace_id': trace_id,
            'year_month': year_month,
            'available_months': list(month_cards_dict.keys())
        })
        
        if not month_cards_dict:
            # 没有已完成卡片
            card_logger.info("没有找到已完成卡片", {
                'trace_id': trace_id
            })
            return render_template('card_done_index.html',
                                 items=[],
                                 year_month=year_month,
                                 categories=categories,
                                 category_now=done_category,
                                 types_cards=card_collections['types_cards'],
                                 times_cards=card_collections['times_cards'],
                                 all_begin_cards=card_collections['all_begin_cards'],
                                 important_cards=card_collections['important_cards'],
                                 month_cards={},
                                 month_list=[])
        
        # 重定向到最近的月份
        month_list = sorted(list(month_cards_dict.keys()), reverse=True)
        card_logger.info("重定向到最近的月份", {
            'trace_id': trace_id,
            'requested_month': year_month,
            'redirect_month': month_list[0]
        })
        return redirect(f"/cards/category/2/{month_list[0]}")
    
    # 获取所选月份的卡片并按降序排序（最新的先显示）
    filtered_items = month_cards_dict[year_month]
    filtered_items = sorted(filtered_items, key=lambda x: x.donetime, reverse=True)
    
    # 记录过滤结果
    card_logger.info("已完成卡片过滤结果", {
        'trace_id': trace_id,
        'year_month': year_month,
        'filtered_items_count': len(filtered_items)
    })
    
    # Get sorted list of months for navigation
    month_list = sorted(list(month_cards_dict.keys()), reverse=True)
    
    # Render the template
    return render_template('card_done_index.html',
                          items=filtered_items,
                          year_month=year_month,
                          categories=categories,
                          category_now=done_category,
                          types_cards=card_collections['types_cards'],
                          times_cards=card_collections['times_cards'],
                          all_begin_cards=card_collections['all_begin_cards'],
                          important_cards=card_collections['important_cards'],
                          month_cards=month_cards_dict,
                          month_list=month_list)


def _group_done_cards_by_month(done_items):
    """Group done cards by month based on their done time.
    
    Args:
        done_items (list): List of completed cards
        
    Returns:
        dict: Dictionary mapping year_month (YYYYMM) to lists of cards
    """
    # 生成跟踪ID
    trace_id = get_card_trace_id()
    
    # 记录开始按月分组卡片
    card_logger.info("开始按月分组已完成卡片", {
        'trace_id': trace_id,
        'total_cards': len(done_items)
    })
    
    month_cards = {}
    skipped_cards = 0
    processed_cards = 0
    error_cards = 0
    
    for card in done_items:
        if not card.donetime:
            skipped_cards += 1
            continue
            
        try:
            # Extract year and month as a combined integer (YYYYMM)
            item_done_time = int(str(card.donetime)[:4] + str(card.donetime)[5:7])
            
            if item_done_time not in month_cards:
                month_cards[item_done_time] = []
                
                # 记录新月份分组创建
                card_logger.info("创建新月份分织", {
                    'trace_id': trace_id,
                    'year_month': item_done_time
                })
                
            month_cards[item_done_time].append(card)
            processed_cards += 1
        except (ValueError, TypeError, IndexError) as e:
            error_cards += 1
            # 记录处理卡片完成时间错误
            card_logger.warning("处理卡片完成时间错误", {
                'trace_id': trace_id,
                'card_id': card.id,
                'headline': card.headline if hasattr(card, 'headline') else 'Unknown',
                'donetime': str(card.donetime) if card.donetime else None,
                'error': str(e)
            })
    
    # 记录分组结果
    card_logger.info("完成按月分组卡片", {
        'trace_id': trace_id,
        'total_cards': len(done_items),
        'processed_cards': processed_cards,
        'skipped_cards': skipped_cards,
        'error_cards': error_cards,
        'month_count': len(month_cards),
        'months': list(month_cards.keys()) if month_cards else []
    })
    
    return month_cards


@card_center.route('/cards/new_category', methods=['GET', 'POST'])
@login_required
@db_error_handler
def new_category():
    """Create a new card category.
    
    POST parameters:
        name: Name of the new category
        
    Returns:
        Response: Redirects to the new category page after creation
    """
    # 生成跟踪ID
    trace_id = get_card_trace_id()
    
    # 记录创建新分类请求
    card_logger.info("创建新卡片分类请求", {
        'trace_id': trace_id,
        'user_id': session.get('main_userid'),
        'remote_addr': request.remote_addr,
        'method': request.method
    })
    
    name = request.form.get('name')
    
    # 记录分类名称
    card_logger.info("新分类名称", {
        'trace_id': trace_id,
        'name': name
    })
    
    if not name or name.strip() == "":
        # 记录空分类名称错误
        card_logger.warning("尝试创建空名称分类", {
            'trace_id': trace_id,
            'user_id': session.get('main_userid'),
            'remote_addr': request.remote_addr
        })
        return jsonify({"error": "分类名称不能为空"}), 400
    
    # 记录创建新分类
    card_logger.info("创建新分类", {
        'trace_id': trace_id,
        'name': name,
        'user_id': session.get('main_userid')
    })
    
    # 创建新分类
    card_category = CardCategory(name=name)
    db.session.add(card_category)
    db.session.commit()
    
    # 记录创建成功
    card_logger.info("新分类创建成功", {
        'trace_id': trace_id,
        'name': name,
        'category_id': card_category.id,
        'user_id': session.get('main_userid')
    })
    
    return redirect(f"/cards/category/{card_category.id}")


@card_center.route('/cards/edit_card/<int:card_id>', methods=['GET', 'POST'])
@login_required
@db_error_handler
def edit_card(card_id):
    """Edit a card.
    
    Args:
        card_id (int): ID of the card to edit
        
    Returns:
        Response: Renders the card_edit.html template with the card and related data
    """
    # 生成跟踪ID
    trace_id = get_card_trace_id()
    
    # 记录编辑卡片请求
    card_logger.info("编辑卡片请求", {
        'trace_id': trace_id,
        'user_id': session.get('main_userid'),
        'card_id': card_id,
        'remote_addr': request.remote_addr,
        'method': request.method
    })

    # 获取卡片
    card_0 = Card.query.get_or_404(card_id)
    
    # 记录卡片信息
    card_logger.info("当前卡片信息", {
        'trace_id': trace_id,
        'card_id': card_id,
        'headline': card_0.headline,
        'type': card_0.type,
        'category_id': card_0.cardcategory_id
    })
    
    # 获取所有分类
    categories = CardCategory.query.all()
    
    # 记录分类信息
    card_logger.info("获取所有分类", {
        'trace_id': trace_id,
        'categories_count': len(categories)
    })
    
    # 收集所有卡片
    all_cards = []
    for card_category in categories:
        now_cards = card_category.cards
        all_cards.extend(now_cards)
    
    # 筛选未完成卡片
    all_undone_cards = [card for card in all_cards if not card.donetime]
    
    # 按类型分类卡片
    type_1_cards = [i for i in all_undone_cards if i.type == 1]
    type_2_cards = [i for i in all_undone_cards if i.type == 2]
    type_3_cards = [i for i in all_undone_cards if i.type == 3]
    type_4_cards = [i for i in all_undone_cards if i.type == 4]
    
    # 记录卡片类型统计
    card_logger.info("卡片类型统计", {
        'trace_id': trace_id,
        'type_1_count': len(type_1_cards),  # 重要紧急
        'type_2_count': len(type_2_cards),  # 重要不紧急
        'type_3_count': len(type_3_cards),  # 紧急不重要
        'type_4_count': len(type_4_cards)   # 不重要不紧急
    })
    
    # ["不重要不紧急","紧急不重要","重要不紧急","重要紧急"]
    types_cards = {"重要紧急": type_1_cards, "重要不紧急": type_2_cards,
                   "紧急不重要": type_3_cards, "不重要不紧急": type_4_cards}
    # 按时间分类卡片
    day_cards = []
    week_cards = []
    month_cards = []
    year_cards = []
    ten_year_cards = []
    
    # 记录开始按时间分类
    card_logger.info("开始按时间分类卡片", {
        'trace_id': trace_id,
        'total_undone_cards': len(all_undone_cards)
    })
    
    for card in all_undone_cards:
        leave_day = cal_leave_day(card.updatetime)
        
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
    
    # 记录时间分类统计
    card_logger.info("卡片时间分类统计", {
        'trace_id': trace_id,
        'day_count': len(day_cards),      # 日清单
        'week_count': len(week_cards),    # 周清单
        'month_count': len(month_cards),  # 月清单
        'year_count': len(year_cards),    # 年清单
        'ten_year_count': len(ten_year_cards)  # 十年清单
    })
    
    times_cards = {"日清单": day_cards, "周清单": week_cards,
                   "月清单": month_cards, "年清单": year_cards, "十年清单": ten_year_cards}

    # 获取卡片分类和项目
    card_category = card_0.cardcategory
    items = card_category.cards
    category_name = card_category.name
    
    # 记录当前分类信息
    card_logger.info("当前卡片分类信息", {
        'trace_id': trace_id,
        'category_id': card_category.id,
        'category_name': category_name,
        'items_count': len(items)
    })
    
    # 根据分类类型选择卡片
    if category_name in ["日清单", "周清单", "月清单", "年清单", "十年清单"]:
        items = times_cards[category_name]
        card_logger.info("按时间分类选择卡片", {
            'trace_id': trace_id,
            'category_name': category_name,
            'selected_items_count': len(items)
        })
    
    if category_name in ["不重要不紧急", "紧急不重要", "重要不紧急", "重要紧急"]:
        items = types_cards[category_name]
        card_logger.info("按类型分类选择卡片", {
            'trace_id': trace_id,
            'category_name': category_name,
            'selected_items_count': len(items)
        })
    
    # 重要卡片处理
    important_cards = type_1_cards + type_2_cards
    
    if card_id == 1:
        if len(type_1_cards) + len(type_2_cards) > 0:
            items = important_cards
            card_logger.info("选择重要卡片", {
                'trace_id': trace_id,
                'important_cards_count': len(important_cards)
            })
    
    # 记录渲染编辑页面
    card_logger.info("渲染卡片编辑页面", {
        'trace_id': trace_id,
        'card_id': card_id,
        'headline': card_0.headline,
        'items_count': len(items)
    })
    
    html_file = 'card_edit.html'
    return render_template(html_file, card=card_0,
                           items=items,
                           categories=categories,
                           category_now=card_category,
                           types_cards=types_cards,
                           times_cards=times_cards,
                           important_cards=important_cards, )


@card_center.route('/cards/edit_item/<int:card_id>', methods=['GET', 'POST'])
@login_required
@db_error_handler
def edit_item(card_id):
    """Edit an existing card's properties.
    
    Updates card attributes from form data, skipping any fields with value "None".
    
    Args:
        card_id (int): ID of the card to be edited
        
    POST parameters:
        category_id: ID of the category to assign the card to
        headline: Card title
        createtime: Creation timestamp
        updatetime: Update timestamp
        donetime: Completion timestamp
        begintime: Start timestamp
        endtime: End timestamp
        usedtime: Time used on the card in seconds
        card_type: Type of card
        content: Card content/description
        
    Returns:
        Response: Redirects to the category page after updating
    """
    # 生成跟踪ID
    trace_id = get_card_trace_id()
    
    # 记录保存卡片编辑请求
    card_logger.info("保存卡片编辑请求", {
        'trace_id': trace_id,
        'user_id': session.get('main_userid'),
        'card_id': card_id,
        'remote_addr': request.remote_addr,
        'method': request.method
    })
    
    # 获取卡片
    card = Card.query.get_or_404(card_id)
    
    # 记录当前卡片信息
    card_logger.info("当前卡片信息", {
        'trace_id': trace_id,
        'card_id': card_id,
        'headline': card.headline,
        'type': card.type,
        'category_id': card.cardcategory_id,
        'has_donetime': card.donetime is not None,
        'has_begintime': card.begintime is not None,
        'has_endtime': card.endtime is not None
    })
    
    # 获取表单数据
    form_data = {
        'category_id': request.form.get('category_id'),
        'headline': request.form.get('headline'),
        'createtime': request.form.get('createtime'),
        'updatetime': request.form.get('updatetime'),
        'donetime': request.form.get('donetime'),
        'begintime': request.form.get('begintime'),
        'endtime': request.form.get('endtime'),
        'usedtime': request.form.get('usedtime'),
        'card_type': request.form.get('card_type'),
        'content': request.form.get('content')
    }
    
    # 记录表单数据
    card_logger.info("提交的表单数据", {
        'trace_id': trace_id,
        'card_id': card_id,
        'form_data': {
            'headline': form_data['headline'] if form_data['headline'] != "None" else None,
            'category_id': form_data['category_id'] if form_data['category_id'] != "None" else None,
            'card_type': form_data['card_type'] if form_data['card_type'] != "None" else None,
            'has_content': form_data['content'] != "None" and form_data['content'] is not None,
            'content_length': len(form_data['content']) if form_data['content'] != "None" and form_data['content'] is not None else 0
        }
    })
    
    # 更新卡片字段，当表单值不是"None"时
    changes = {}
    
    if form_data['headline'] != "None":
        changes['headline'] = {'old': card.headline, 'new': form_data['headline']}
        card.headline = form_data['headline']
        
    if form_data['createtime'] != "None":
        try:
            changes['createtime'] = {'old': str(card.createtime), 'new': form_data['createtime']}
            card.createtime = form_data['createtime']
        except (ValueError, TypeError) as e:
            card_logger.warning("创建时间格式无效", {
                'trace_id': trace_id,
                'card_id': card_id,
                'value': form_data['createtime'],
                'error': str(e)
            })
            
    if form_data['updatetime'] != "None":
        try:
            changes['updatetime'] = {'old': str(card.updatetime), 'new': form_data['updatetime']}
            card.updatetime = form_data['updatetime']
        except (ValueError, TypeError) as e:
            card_logger.warning("更新时间格式无效", {
                'trace_id': trace_id,
                'card_id': card_id,
                'value': form_data['updatetime'],
                'error': str(e)
            })
    
    # 处理可能为None的时间戳字段
    if form_data['donetime'] != "None":
        try:
            changes['donetime'] = {'old': str(card.donetime) if card.donetime else None, 'new': form_data['donetime']}
            card.donetime = form_data['donetime']
        except (ValueError, TypeError) as e:
            card_logger.warning("完成时间格式无效", {
                'trace_id': trace_id,
                'card_id': card_id,
                'value': form_data['donetime'],
                'error': str(e)
            })
    else:
        if card.donetime is not None:
            changes['donetime'] = {'old': str(card.donetime), 'new': None}
        card.donetime = None

    if form_data['begintime'] != "None":
        try:
            changes['begintime'] = {'old': str(card.begintime) if card.begintime else None, 'new': form_data['begintime']}
            card.begintime = form_data['begintime']
        except (ValueError, TypeError) as e:
            card_logger.warning("开始时间格式无效", {
                'trace_id': trace_id,
                'card_id': card_id,
                'value': form_data['begintime'],
                'error': str(e)
            })
    else:
        if card.begintime is not None:
            changes['begintime'] = {'old': str(card.begintime), 'new': None}
        card.begintime = None

    if form_data['endtime'] != "None":
        try:
            changes['endtime'] = {'old': str(card.endtime) if card.endtime else None, 'new': form_data['endtime']}
            card.endtime = form_data['endtime']
        except (ValueError, TypeError) as e:
            card_logger.warning("结束时间格式无效", {
                'trace_id': trace_id,
                'card_id': card_id,
                'value': form_data['endtime'],
                'error': str(e)
            })
    else:
        if card.endtime is not None:
            changes['endtime'] = {'old': str(card.endtime), 'new': None}
        card.endtime = None

    # 处理其他字段
    if form_data['card_type'] != "None":
        changes['type'] = {'old': card.type, 'new': form_data['card_type']}
        card.type = form_data['card_type']

    if form_data['usedtime'] != "None":
        try:
            changes['usedtime'] = {'old': card.usedtime, 'new': int(form_data['usedtime'])}
            card.usedtime = int(form_data['usedtime'])
        except (ValueError, TypeError) as e:
            card_logger.warning("使用时间值无效", {
                'trace_id': trace_id,
                'card_id': card_id,
                'value': form_data['usedtime'],
                'error': str(e)
            })

    if form_data['content'] != "None":
        # 不记录内容的实际值，只记录长度变化
        old_content_length = len(card.content) if card.content else 0
        new_content_length = len(form_data['content']) if form_data['content'] else 0
        changes['content'] = {'old_length': old_content_length, 'new_length': new_content_length}
        card.content = form_data['content']

    if form_data['category_id'] != "None":
        try:
            category_id = int(form_data['category_id'])
            # 验证分类是否存在
            CardCategory.query.get_or_404(category_id)
            changes['category_id'] = {'old': card.cardcategory_id, 'new': category_id}
            card.cardcategory_id = category_id
        except (ValueError, TypeError) as e:
            card_logger.warning("分类编号无效", {
                'trace_id': trace_id,
                'card_id': card_id,
                'value': form_data['category_id'],
                'error': str(e)
            })
            category_id = card.cardcategory_id
    else:
        category_id = card.cardcategory_id

    # 记录变更摘要
    card_logger.info("卡片变更摘要", {
        'trace_id': trace_id,
        'card_id': card_id,
        'changes': changes,
        'fields_changed': len(changes)
    })

    # 保存变更
    db.session.add(card)
    db.session.commit()
    
    # 记录更新成功
    card_logger.info("卡片更新成功", {
        'trace_id': trace_id,
        'card_id': card_id,
        'category_id': category_id,
        'user_id': session.get('main_userid')
    })
    
    return redirect(f"/cards/category/{category_id}")


@card_center.route('/cards/edit_category/<int:card_id>', methods=['GET', 'POST'])
@login_required
@db_error_handler
def edit_category(card_id):
    """Edit a card category name.
    
    Args:
        card_id (int): ID of the category to edit
        
    POST parameters:
        name: New name for the category
        
    Returns:
        Response: Redirects to the default category page after update
    """
    # 生成跟踪ID
    trace_id = get_card_trace_id()
    
    # 记录编辑分类请求
    card_logger.info("编辑卡片分类请求", {
        'trace_id': trace_id,
        'user_id': session.get('main_userid'),
        'category_id': card_id,
        'remote_addr': request.remote_addr,
        'method': request.method
    })
    
    # 获取分类
    card_category = CardCategory.query.get_or_404(card_id)
    
    # 记录当前分类信息
    card_logger.info("当前分类信息", {
        'trace_id': trace_id,
        'category_id': card_id,
        'current_name': card_category.name
    })
    
    name = request.form.get('name')
    
    # 记录新分类名称
    card_logger.info("新分类名称", {
        'trace_id': trace_id,
        'category_id': card_id,
        'new_name': name
    })
    
    if not name or name.strip() == "":
        # 记录空分类名称错误
        card_logger.warning("尝试更新为空名称分类", {
            'trace_id': trace_id,
            'user_id': session.get('main_userid'),
            'category_id': card_id,
            'current_name': card_category.name,
            'remote_addr': request.remote_addr
        })
        return jsonify({"error": "分类名称不能为空"}), 400
    
    # 记录分类更新
    card_logger.info("更新分类名称", {
        'trace_id': trace_id,
        'category_id': card_id,
        'old_name': card_category.name,
        'new_name': name,
        'user_id': session.get('main_userid')
    })
    
    # 更新分类名称
    card_category.name = name
    db.session.add(card_category)
    db.session.commit()
    
    # 记录更新成功
    card_logger.info("分类更新成功", {
        'trace_id': trace_id,
        'category_id': card_id,
        'name': name,
        'user_id': session.get('main_userid')
    })
    
    return redirect(f"/cards/category/1")


@card_center.route('/cards/done/<int:card_id>', methods=['GET', 'POST'])
@login_required
@db_error_handler
def done(card_id):
    """Mark a card as done by moving it to the 'Done' category (ID 2).
    
    This creates a new card in the 'Done' category with the same properties
    and deletes the original card.
    
    Args:
        card_id (int): ID of the card to mark as done
        
    Returns:
        Response: Redirects to the original category page after completion
    """
    # 生成跟踪ID
    trace_id = get_card_trace_id()
    
    # 记录完成卡片请求
    card_logger.info("标记卡片为已完成请求", {
        'trace_id': trace_id,
        'user_id': session.get('main_userid'),
        'card_id': card_id,
        'remote_addr': request.remote_addr,
        'method': request.method
    })
    
    # 获取原始卡片
    card = Card.query.get_or_404(card_id)
    category_id = card.cardcategory_id
    
    # 记录原始卡片信息
    card_logger.info("原始卡片信息", {
        'trace_id': trace_id,
        'card_id': card_id,
        'headline': card.headline,
        'category_id': category_id,
        'type': card.type,
        'has_begintime': card.begintime is not None,
        'has_endtime': card.endtime is not None,
        'usedtime': card.usedtime,
        'content_length': len(card.content) if card.content else 0
    })
    
    # 创建完成时间戳
    now_time = datetime.datetime.now()
    
    # 记录完成时间
    card_logger.info("卡片完成时间", {
        'trace_id': trace_id,
        'card_id': card_id,
        'donetime': str(now_time)
    })
    
    # 获取'已完成'分类（ID 2）
    done_category = CardCategory.query.get_or_404(2)
    
    # 记录目标分类信息
    card_logger.info("目标分类信息", {
        'trace_id': trace_id,
        'category_id': done_category.id,
        'category_name': done_category.name
    })
    
    # 在'已完成'分类中创建新卡片
    done_card = Card(headline=card.headline, 
                     cardcategory=done_category,
                     begintime=card.begintime,
                     endtime=card.endtime,
                     donetime=now_time,
                     usedtime=card.usedtime,
                     content=card.content,
                     type=card.type)
    
    # 记录移动卡片操作
    card_logger.info("移动卡片到已完成分类", {
        'trace_id': trace_id,
        'card_id': card_id,
        'headline': card.headline,
        'from_category_id': category_id,
        'to_category_id': done_category.id
    })
    
    # 在单个事务中添加新卡片并删除原始卡片
    db.session.add(done_card)
    db.session.delete(card)
    
    # 记录数据库操作
    card_logger.info("数据库操作准备", {
        'trace_id': trace_id,
        'operations': ['add_done_card', 'delete_original_card']
    })
    
    db.session.commit()
    
    # 记录操作成功
    card_logger.info("卡片完成操作成功", {
        'trace_id': trace_id,
        'card_id': card_id,
        'done_card_id': done_card.id,
        'user_id': session.get('main_userid'),
        'donetime': str(now_time)
    })
    
    return redirect(f"/cards/category/{category_id}")


@card_center.route('/cards/delete_item/<int:card_id>', methods=['GET', 'POST'])
@login_required
@db_error_handler
def delete_item(card_id):
    """Delete a card item permanently.
    
    Args:
        card_id (int): ID of the card to delete
        
    Returns:
        Response: Redirects to the default category page after deletion
    """
    # 生成跟踪ID
    trace_id = get_card_trace_id()
    
    # 记录删除卡片请求
    card_logger.info("删除卡片请求", {
        'trace_id': trace_id,
        'user_id': session.get('main_userid'),
        'card_id': card_id,
        'remote_addr': request.remote_addr,
        'method': request.method
    })
    
    # 获取卡片或404如果未找到
    item = Card.query.get_or_404(card_id)
    category_id = item.cardcategory_id
    
    # 记录卡片信息
    card_logger.info("将要删除的卡片信息", {
        'trace_id': trace_id,
        'card_id': card_id,
        'headline': item.headline,
        'category_id': category_id,
        'type': item.type,
        'has_donetime': item.donetime is not None,
        'has_begintime': item.begintime is not None,
        'has_endtime': item.endtime is not None,
        'content_length': len(item.content) if item.content else 0
    })
    
    # 注意：这个检查在get_or_404之后是多余的，但保留以确保安全
    if item is None:
        card_logger.warning("尝试删除不存在的卡片", {
            'trace_id': trace_id,
            'card_id': card_id,
            'user_id': session.get('main_userid')
        })
        return redirect(f"/cards/category/1")
    
    # 记录删除操作
    card_logger.info("删除卡片操作", {
        'trace_id': trace_id,
        'card_id': card_id,
        'headline': item.headline,
        'category_id': category_id,
        'user_id': session.get('main_userid')
    })
    
    # 删除卡片
    db.session.delete(item)
    db.session.commit()
    
    # 记录删除成功
    card_logger.info("卡片删除成功", {
        'trace_id': trace_id,
        'card_id': card_id,
        'user_id': session.get('main_userid'),
        'redirect_category_id': category_id
    })
    
    return redirect(f"/cards/category/{category_id}")


@card_center.route('/cards/delete_category/<int:card_id>', methods=['GET', 'POST'])
@login_required
@db_error_handler
def delete_category(card_id):
    """Delete a card category if it's not a protected category (ID 1 or 2).
    
    Args:
        card_id (int): ID of the category to delete
        
    Returns:
        Response: Redirects to the default category page after deletion
    """
    # 生成跟踪ID
    trace_id = get_card_trace_id()
    
    # 记录删除分类请求
    card_logger.info("删除卡片分类请求", {
        'trace_id': trace_id,
        'user_id': session.get('main_userid'),
        'category_id': card_id,
        'remote_addr': request.remote_addr,
        'method': request.method
    })
    
    # 检查是否为受保护的分类
    if card_id in [1, 2]:
        # 记录尝试删除受保护的分类
        card_logger.warning("尝试删除受保护的分类", {
            'trace_id': trace_id,
            'user_id': session.get('main_userid'),
            'category_id': card_id,
            'remote_addr': request.remote_addr
        })
        return redirect(f"/cards/category/1")
    
    # 获取分类
    card_category = CardCategory.query.get_or_404(card_id)
    
    # 记录分类信息
    card_logger.info("将要删除的分类信息", {
        'trace_id': trace_id,
        'category_id': card_id,
        'category_name': card_category.name,
        'cards_count': len(card_category.cards) if hasattr(card_category, 'cards') else 0
    })
    
    # 再次检查分类是否存在（由于get_or_404，这里应该不会执行）
    if card_category is None:
        # 记录分类不存在
        card_logger.warning("分类不存在", {
            'trace_id': trace_id,
            'category_id': card_id
        })
        return redirect(f"/cards/category/1")
    
    # 记录删除分类操作
    card_logger.info("删除分类", {
        'trace_id': trace_id,
        'category_id': card_id,
        'category_name': card_category.name,
        'user_id': session.get('main_userid')
    })
        
    # 删除分类
    db.session.delete(card_category)
    db.session.commit()
    
    # 记录删除成功
    card_logger.info("分类删除成功", {
        'trace_id': trace_id,
        'category_id': card_id,
        'user_id': session.get('main_userid')
    })
    
    # 删除后始终重定向到默认分类
    return redirect(f"/cards/category/1")


if __name__ == "__main__":
    pass
