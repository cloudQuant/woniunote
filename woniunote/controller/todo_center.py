from flask import render_template, redirect, abort, request, session
import uuid
from datetime import datetime, UTC

from woniunote.controller.user import Blueprint
from woniunote.common.database import db
from woniunote.common.simple_logger import SimpleLogger

# 从模型文件导入数据库模型
from woniunote.models.todo import Item, Category

tcenter = Blueprint("tcenter", __name__)

# 初始化待办事项模块日志记录器
todo_logger = SimpleLogger('todo')

# 生成待办事项模块跟踪ID的函数
def get_todo_trace_id():
    """生成待办事项模块的跟踪ID
    
    Returns:
        str: 格式为 'todo_yyyyMMdd_uuid' 的跟踪ID
    """
    now = datetime.now(UTC)
    date_str = now.strftime('%Y%m%d')
    return f"todo_{date_str}_{str(uuid.uuid4())[:8]}"


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
    """待办事项首页处理函数
    
    处理待办事项首页的访问和新增待办事项的请求
    
    Returns:
        Response: 重定向到待办事项分类页面
    """
    # 生成跟踪ID
    trace_id = get_todo_trace_id()
    
    # 记录待办事项首页访问请求
    todo_logger.info("待办事项首页访问", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'user_id': session.get('userid') if session.get('islogin') == 'true' else None
    })
    
    # 检查用户登录状态
    if session.get('main_islogin') is None:
        # 记录未登录访问尝试
        todo_logger.warning("未登录访问待办事项首页", {
            'trace_id': trace_id,
            'remote_addr': request.remote_addr,
            'method': request.method,
            'path': request.path
        })
        abort(404)
    
    # 处理POST请求，添加新的待办事项
    if request.method == 'POST':
        try:
            # 获取表单数据
            body = request.form.get('item')
            category_id = request.form.get('category')
            
            # 记录添加待办事项请求
            todo_logger.info("添加待办事项请求", {
                'trace_id': trace_id,
                'remote_addr': request.remote_addr,
                'body': body,
                'category_id': category_id,
                'user_id': session.get('userid') if session.get('islogin') == 'true' else None
            })
            
            # 获取分类并创建新的待办事项
            category_card = Category.query.get_or_404(category_id)
            item = Item(body=body, category=category_card)
            
            # 保存到数据库
            db.session.add(item)
            db.session.commit()
            
            # 记录添加待办事项成功
            todo_logger.info("添加待办事项成功", {
                'trace_id': trace_id,
                'item_id': item.id,
                'body': body,
                'category_id': category_id
            })
            
            # 重定向到分类页面
            return redirect(f"/todo/category/{category_card.id}")
        except Exception as e:
            # 记录异常
            todo_logger.error("添加待办事项异常", {
                'trace_id': trace_id,
                'error': str(e),
                'error_type': type(e).__name__
            })
            # 回滚事务
            db.session.rollback()
            # 重定向到默认分类
            return redirect(f"/todo/category/1")
    
    # GET请求，重定向到默认分类
    todo_logger.info("重定向到默认待办事项分类", {
        'trace_id': trace_id,
        'default_category_id': 1
    })
    return redirect(f"/todo/category/1")


@tcenter.route('/todo/category/<int:category_id>', methods=['GET', 'POST'])
def category(category_id):
    """待办事项分类页面处理函数
    
    显示指定分类的待办事项列表
    
    Args:
        category_id (int): 分类 ID
        
    Returns:
        Response: 渲染后的待办事项分类页面
    """
    # 生成跟踪ID
    trace_id = get_todo_trace_id()
    
    # 记录待办事项分类页面访问请求
    todo_logger.info("待办事项分类页面访问", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'category_id': category_id,
        'user_id': session.get('userid') if session.get('islogin') == 'true' else None
    })
    
    # 检查用户登录状态
    if session.get('main_islogin') is None:
        # 记录未登录访问尝试
        todo_logger.warning("未登录访问待办事项分类页面", {
            'trace_id': trace_id,
            'remote_addr': request.remote_addr,
            'category_id': category_id,
            'path': request.path
        })
        abort(404)
    
    try:
        # 获取当前分类
        category_card = Category.query.get_or_404(category_id)
        
        # 记录分类获取成功
        todo_logger.info("待办事项分类获取成功", {
            'trace_id': trace_id,
            'category_id': category_id,
            'category_name': category_card.name
        })
        
        # 获取所有分类和当前分类的待办事项
        categories = Category.query.all()
        items = category_card.items
        
        # 记录待办事项列表获取成功
        todo_logger.info("待办事项列表获取成功", {
            'trace_id': trace_id,
            'category_id': category_id,
            'items_count': len(items) if items else 0,
            'categories_count': len(categories) if categories else 0
        })
        
        # 渲染模板
        html_file = "todo_index.html"
        content = render_template(html_file, items=items,
                               categories=categories, category_now=category_card)
        
        # 记录渲染成功
        todo_logger.info("待办事项分类页面渲染成功", {
            'trace_id': trace_id,
            'category_id': category_id,
            'template': html_file,
            'content_length': len(content) if content else 0
        })
        
        return content
    except Exception as e:
        # 记录异常
        todo_logger.error("待办事项分类页面访问异常", {
            'trace_id': trace_id,
            'category_id': category_id,
            'error': str(e),
            'error_type': type(e).__name__
        })
        # 重定向到默认分类
        return redirect(f"/todo/category/1")


@tcenter.route('/todo/new_category', methods=['GET', 'POST'])
def new_category():
    """新建待办事项分类处理函数
    
    创建新的待办事项分类
    
    Returns:
        Response: 重定向到新创建的分类页面
    """
    # 生成跟踪ID
    trace_id = get_todo_trace_id()
    
    # 记录新建分类请求
    todo_logger.info("新建待办事项分类请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'user_id': session.get('userid') if session.get('islogin') == 'true' else None
    })
    
    # 检查用户登录状态
    if session.get('main_islogin') is None:
        # 记录未登录访问尝试
        todo_logger.warning("未登录尝试新建待办事项分类", {
            'trace_id': trace_id,
            'remote_addr': request.remote_addr,
            'path': request.path
        })
        abort(404)
    
    try:
        # 获取分类名称
        name = request.form.get('name')
        
        # 记录分类名称
        todo_logger.info("新建待办事项分类信息", {
            'trace_id': trace_id,
            'category_name': name
        })
        
        # 创建新分类
        category_card = Category(name=name)
        db.session.add(category_card)
        db.session.commit()
        
        # 记录新建分类成功
        todo_logger.info("新建待办事项分类成功", {
            'trace_id': trace_id,
            'category_id': category_card.id,
            'category_name': name
        })
        
        # 重定向到新分类页面
        return redirect(f"/todo/category/{category_card.id}")
    except Exception as e:
        # 记录异常
        todo_logger.error("新建待办事项分类异常", {
            'trace_id': trace_id,
            'error': str(e),
            'error_type': type(e).__name__
        })
        # 回滚事务
        db.session.rollback()
        # 重定向到默认分类
        return redirect(f"/todo/category/1")


@tcenter.route('/todo/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    """编辑待办事项处理函数
    
    编辑现有的待办事项
    
    Args:
        item_id (int): 待办事项 ID
        
    Returns:
        Response: 重定向到待办事项所属分类页面
    """
    # 生成跟踪ID
    trace_id = get_todo_trace_id()
    
    # 记录编辑待办事项请求
    todo_logger.info("编辑待办事项请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'item_id': item_id,
        'user_id': session.get('userid') if session.get('islogin') == 'true' else None
    })
    
    # 检查用户登录状态
    if session.get('main_islogin') is None:
        # 记录未登录访问尝试
        todo_logger.warning("未登录尝试编辑待办事项", {
            'trace_id': trace_id,
            'remote_addr': request.remote_addr,
            'item_id': item_id,
            'path': request.path
        })
        abort(404)
    
    try:
        # 获取待办事项
        item = Item.query.get_or_404(item_id)
        category_ = item.category
        
        # 记录待办事项获取成功
        todo_logger.info("待办事项获取成功", {
            'trace_id': trace_id,
            'item_id': item_id,
            'category_id': category_.id,
            'original_body': item.body
        })
        
        # 获取新的内容并更新
        new_body = request.form.get('body')
        item.body = new_body
        
        # 保存到数据库
        db.session.add(item)
        db.session.commit()
        
        # 记录编辑待办事项成功
        todo_logger.info("编辑待办事项成功", {
            'trace_id': trace_id,
            'item_id': item_id,
            'category_id': category_.id,
            'new_body': new_body
        })
        
        # 重定向到分类页面
        return redirect(f"/todo/category/{category_.id}")
    except Exception as e:
        # 记录异常
        todo_logger.error("编辑待办事项异常", {
            'trace_id': trace_id,
            'item_id': item_id,
            'error': str(e),
            'error_type': type(e).__name__
        })
        # 回滚事务
        db.session.rollback()
        # 重定向到默认分类
        return redirect(f"/todo/category/1")


@tcenter.route('/todo/edit_category/<int:category_id>', methods=['GET', 'POST'])
def edit_category(category_id):
    """编辑待办事项分类处理函数
    
    编辑现有的待办事项分类
    
    Args:
        category_id (int): 分类 ID
        
    Returns:
        Response: 重定向到待办事项分类页面
    """
    # 生成跟踪ID
    trace_id = get_todo_trace_id()
    
    # 记录编辑分类请求
    todo_logger.info("编辑待办事项分类请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'category_id': category_id,
        'user_id': session.get('userid') if session.get('islogin') == 'true' else None
    })
    
    # 检查用户登录状态
    if session.get('main_islogin') is None:
        # 记录未登录访问尝试
        todo_logger.warning("未登录尝试编辑待办事项分类", {
            'trace_id': trace_id,
            'remote_addr': request.remote_addr,
            'category_id': category_id,
            'path': request.path
        })
        abort(404)
    
    try:
        # 获取分类
        category_card = Category.query.get_or_404(category_id)
        
        # 记录分类获取成功
        todo_logger.info("待办事项分类获取成功", {
            'trace_id': trace_id,
            'category_id': category_id,
            'original_name': category_card.name
        })
        
        # 获取新的分类名称并更新
        new_name = request.form.get('name')
        category_card.name = new_name
        
        # 保存到数据库
        db.session.add(category_card)
        db.session.commit()
        
        # 记录编辑分类成功
        todo_logger.info("编辑待办事项分类成功", {
            'trace_id': trace_id,
            'category_id': category_id,
            'new_name': new_name
        })
        
        # 重定向到分类页面
        return redirect(f"/todo/category/{category_card.id}")
    except Exception as e:
        # 记录异常
        todo_logger.error("编辑待办事项分类异常", {
            'trace_id': trace_id,
            'category_id': category_id,
            'error': str(e),
            'error_type': type(e).__name__
        })
        # 回滚事务
        db.session.rollback()
        # 重定向到默认分类
        return redirect(f"/todo/category/1")


@tcenter.route('/todo/done/<int:item_id>', methods=['GET', 'POST'])
def done(item_id):
    """标记待办事项为已完成处理函数
    
    将待办事项移动到已完成分类
    
    Args:
        item_id (int): 待办事项 ID
        
    Returns:
        Response: 重定向到原待办事项所属分类页面
    """
    # 生成跟踪ID
    trace_id = get_todo_trace_id()
    
    # 记录标记待办事项为已完成请求
    todo_logger.info("标记待办事项为已完成请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'item_id': item_id,
        'user_id': session.get('userid') if session.get('islogin') == 'true' else None
    })
    
    # 检查用户登录状态
    if session.get('main_islogin') is None:
        # 记录未登录访问尝试
        todo_logger.warning("未登录尝试标记待办事项为已完成", {
            'trace_id': trace_id,
            'remote_addr': request.remote_addr,
            'item_id': item_id,
            'path': request.path
        })
        abort(404)
    
    try:
        # 获取待办事项和其分类
        item = Item.query.get_or_404(item_id)
        category_card = item.category
        
        # 记录待办事项获取成功
        todo_logger.info("待办事项获取成功", {
            'trace_id': trace_id,
            'item_id': item_id,
            'body': item.body,
            'category_id': category_card.id,
            'category_name': category_card.name
        })
        
        # 获取已完成分类
        done_category = Category.query.get_or_404(2)
        
        # 记录已完成分类获取成功
        todo_logger.info("已完成分类获取成功", {
            'trace_id': trace_id,
            'done_category_id': done_category.id,
            'done_category_name': done_category.name
        })
        
        # 创建新的已完成事项
        done_item = Item(body=item.body, category=done_category)
        
        # 保存到数据库
        db.session.add(done_item)
        db.session.delete(item)
        db.session.commit()
        
        # 记录标记待办事项为已完成成功
        todo_logger.info("标记待办事项为已完成成功", {
            'trace_id': trace_id,
            'original_item_id': item_id,
            'new_item_id': done_item.id,
            'body': done_item.body,
            'original_category_id': category_card.id,
            'done_category_id': done_category.id
        })
        
        # 重定向到原分类页面
        return redirect(f"/todo/category/{category_card.id}")
    except Exception as e:
        # 记录异常
        todo_logger.error("标记待办事项为已完成异常", {
            'trace_id': trace_id,
            'item_id': item_id,
            'error': str(e),
            'error_type': type(e).__name__
        })
        # 回滚事务
        db.session.rollback()
        # 重定向到默认分类
        return redirect(f"/todo/category/1")


@tcenter.route('/todo/delete_item/<int:item_id>', methods=['GET', 'POST'])
def delete_item(item_id):
    """删除待办事项处理函数
    
    删除指定的待办事项
    
    Args:
        item_id (int): 待办事项 ID
        
    Returns:
        Response: 重定向到待办事项所属分类页面
    """
    # 生成跟踪ID
    trace_id = get_todo_trace_id()
    
    # 记录删除待办事项请求
    todo_logger.info("删除待办事项请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'item_id': item_id,
        'user_id': session.get('userid') if session.get('islogin') == 'true' else None
    })
    
    # 检查用户登录状态
    if session.get('main_islogin') is None:
        # 记录未登录访问尝试
        todo_logger.warning("未登录尝试删除待办事项", {
            'trace_id': trace_id,
            'remote_addr': request.remote_addr,
            'item_id': item_id,
            'path': request.path
        })
        abort(404)
    
    try:
        # 获取待办事项
        item = Item.query.get_or_404(item_id)
        
        # 如果待办事项不存在，重定向到默认分类
        if item is None:
            # 记录待办事项不存在
            todo_logger.warning("待办事项不存在", {
                'trace_id': trace_id,
                'item_id': item_id
            })
            return redirect(f"/todo/category/1")
        
        # 获取待办事项所属分类
        category_card = item.category
        
        # 记录待办事项获取成功
        todo_logger.info("待办事项获取成功", {
            'trace_id': trace_id,
            'item_id': item_id,
            'body': item.body,
            'category_id': category_card.id,
            'category_name': category_card.name
        })
        
        # 删除待办事项
        db.session.delete(item)
        db.session.commit()
        
        # 记录删除待办事项成功
        todo_logger.info("删除待办事项成功", {
            'trace_id': trace_id,
            'item_id': item_id,
            'category_id': category_card.id
        })
        
        # 重定向到分类页面
        return redirect(f"/todo/category/{category_card.id}")
    except Exception as e:
        # 记录异常
        todo_logger.error("删除待办事项异常", {
            'trace_id': trace_id,
            'item_id': item_id,
            'error': str(e),
            'error_type': type(e).__name__
        })
        # 回滚事务
        db.session.rollback()
        # 重定向到默认分类
        return redirect(f"/todo/category/1")


@tcenter.route('/todo/delete_category/<int:category_id>', methods=['GET', 'POST'])
def delete_category(category_id):
    """删除待办事项分类处理函数
    
    删除指定的待办事项分类，除了默认分类和已完成分类
    
    Args:
        category_id (int): 分类 ID
        
    Returns:
        Response: 重定向到默认分类页面
    """
    # 生成跟踪ID
    trace_id = get_todo_trace_id()
    
    # 记录删除分类请求
    todo_logger.info("删除待办事项分类请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'category_id': category_id,
        'user_id': session.get('userid') if session.get('islogin') == 'true' else None
    })
    
    # 检查用户登录状态
    if session.get('main_islogin') is None:
        # 记录未登录访问尝试
        todo_logger.warning("未登录尝试删除待办事项分类", {
            'trace_id': trace_id,
            'remote_addr': request.remote_addr,
            'category_id': category_id,
            'path': request.path
        })
        abort(404)
    
    try:
        # 获取分类
        category_card = Category.query.get_or_404(category_id)
        
        # 如果分类不存在或者是默认分类或已完成分类，不允许删除
        if category_card is None or category_id in [1, 2]:
            # 记录分类不存在或不允许删除
            todo_logger.warning("分类不存在或不允许删除", {
                'trace_id': trace_id,
                'category_id': category_id,
                'protected_categories': [1, 2]
            })
            return redirect(f"/todo/category/1")
        
        # 记录分类获取成功
        todo_logger.info("待办事项分类获取成功", {
            'trace_id': trace_id,
            'category_id': category_id,
            'category_name': category_card.name,
            'items_count': len(category_card.items) if category_card.items else 0
        })
        
        # 删除分类
        db.session.delete(category_card)
        db.session.commit()
        
        # 记录删除分类成功
        todo_logger.info("删除待办事项分类成功", {
            'trace_id': trace_id,
            'category_id': category_id
        })
        
        # 重定向到默认分类页面
        return redirect(f"/todo/category/1")
    except Exception as e:
        # 记录异常
        todo_logger.error("删除待办事项分类异常", {
            'trace_id': trace_id,
            'category_id': category_id,
            'error': str(e),
            'error_type': type(e).__name__
        })
        # 回滚事务
        db.session.rollback()
        # 重定向到默认分类
        return redirect(f"/todo/category/1")
