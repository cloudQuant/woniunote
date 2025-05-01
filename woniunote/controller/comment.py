from flask import Blueprint, request, session, jsonify
import uuid
import datetime

from woniunote.module.articles import Articles
from woniunote.module.comments import Comments
from woniunote.module.credits import Credits
from woniunote.module.users import Users
from woniunote.common.simple_logger import SimpleLogger

comment = Blueprint('comment', __name__)

# 初始化评论模块日志记录器
comment_logger = SimpleLogger('comment')

# 生成评论模块跟踪ID的函数
def get_comment_trace_id():
    """生成评论模块的跟踪ID
    
    Returns:
        str: 格式为 'comment_yyyyMMdd_uuid' 的跟踪ID
    """
    now = datetime.datetime.now()
    date_str = now.strftime('%Y%m%d')
    return f"comment_{date_str}_{str(uuid.uuid4())[:8]}"


@comment.before_request
def before_comment():
    """评论模块的请求前置处理，检查用户是否已登录
    
    Returns:
        str: 如果用户未登录，返回'not-login'，否则继续处理请求
    """
    # 生成跟踪ID
    trace_id = get_comment_trace_id()
    
    # 记录请求信息
    comment_logger.info("评论模块请求", {
        'trace_id': trace_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'user_id': session.get('userid')
    })
    
    try:
        # 检查用户是否已登录
        if session.get('islogin') is None or session.get('islogin') != 'true':
            # 记录未登录访问
            comment_logger.warning("未登录用户尝试访问评论功能", {
                'trace_id': trace_id,
                'remote_addr': request.remote_addr,
                'method': request.method,
                'path': request.path
            })
            return 'not-login'
    except Exception as e:
        # 记录异常
        comment_logger.error("评论前置检查异常", {
            'trace_id': trace_id,
            'remote_addr': request.remote_addr,
            'error': str(e),
            'error_type': type(e).__name__
        })


@comment.route('/comment', methods=['POST'])
def add():
    """添加评论的处理函数
    
    处理用户对文章的评论添加请求，包括内容验证、频率限制检查、积分更新等
    
    Returns:
        str: 评论添加结果状态码
    """
    # 生成跟踪ID
    trace_id = get_comment_trace_id()
    
    try:
        # 获取评论参数
        articleid = request.form.get('articleid')
        content = request.form.get('content').strip() if request.form.get('content') else ''
        ipaddr = request.remote_addr
        userid = session.get('userid')
        
        # 记录评论请求
        comment_logger.info("添加评论请求", {
            'trace_id': trace_id,
            'user_id': userid,
            'article_id': articleid,
            'ip_addr': ipaddr,
            'content_length': len(content)
        })

        # 对评论内容进行简单检验
        if len(content) < 5 or len(content) > 1000:
            # 记录内容验证失败
            comment_logger.warning("评论内容验证失败", {
                'trace_id': trace_id,
                'user_id': userid,
                'article_id': articleid,
                'content_length': len(content),
                'reason': 'length_invalid',
                'min_length': 5,
                'max_length': 1000
            })
            return 'content-invalid'

        # 创建评论实例
        comment_instance = Comments()
        
        # 检查频率限制
        if not comment_instance.check_limit_per_5():
            try:
                # 插入评论
                comment_instance.insert_comment(articleid, content, ipaddr)
                
                # 记录评论添加成功
                comment_logger.info("评论添加成功", {
                    'trace_id': trace_id,
                    'user_id': userid,
                    'article_id': articleid,
                    'content_length': len(content)
                })
                
                # 评论成功后，更新积分明细和剩余积分，及文章回复数量
                Credits().insert_detail(credit_type='添加评论', target=articleid, credit=2)
                Users().update_credit(2)
                Articles().update_replycount(articleid)
                
                # 记录积分更新
                comment_logger.info("评论积分更新", {
                    'trace_id': trace_id,
                    'user_id': userid,
                    'article_id': articleid,
                    'credit_type': '添加评论',
                    'credit_value': 2
                })
                
                return 'add-pass'
            except Exception as e:
                # 记录评论添加异常
                comment_logger.error("评论添加异常", {
                    'trace_id': trace_id,
                    'user_id': userid,
                    'article_id': articleid,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                return 'add-fail'
        else:
            # 记录频率限制
            comment_logger.warning("评论频率超限", {
                'trace_id': trace_id,
                'user_id': userid,
                'article_id': articleid,
                'limit_rule': '5_minutes'
            })
            return 'add-limit'
    except Exception as e:
        # 记录全局异常
        comment_logger.error("评论添加全局异常", {
            'trace_id': trace_id,
            'error': str(e),
            'error_type': type(e).__name__,
            'request_path': request.path,
            'request_method': request.method
        })


@comment.route('/reply', methods=['POST'])
def reply():
    """回复评论的处理函数
    
    处理用户对已有评论的回复请求，包括内容验证、频率限制检查、积分更新等
    
    Returns:
        str: 回复添加结果状态码
    """
    # 生成跟踪ID
    trace_id = get_comment_trace_id()
    
    try:
        # 获取回复参数
        articleid = request.form.get('articleid')
        commentid = request.form.get('commentid')
        content = request.form.get('content').strip() if request.form.get('content') else ''
        ipaddr = request.remote_addr
        userid = session.get('userid')
        
        # 记录回复请求
        comment_logger.info("回复评论请求", {
            'trace_id': trace_id,
            'user_id': userid,
            'article_id': articleid,
            'comment_id': commentid,
            'ip_addr': ipaddr,
            'content_length': len(content)
        })

        # 如果评论的字数低于5个或多于1000个，均视为不合法
        if len(content) < 5 or len(content) > 1000:
            # 记录内容验证失败
            comment_logger.warning("回复内容验证失败", {
                'trace_id': trace_id,
                'user_id': userid,
                'article_id': articleid,
                'comment_id': commentid,
                'content_length': len(content),
                'reason': 'length_invalid',
                'min_length': 5,
                'max_length': 1000
            })
            return 'content-invalid'

        # 创建评论实例
        comment_instance = Comments()
        
        # 没有超出限制才能发表评论
        if not comment_instance.check_limit_per_5():
            try:
                # 插入回复
                comment_instance.insert_reply(articleid=articleid, commentid=commentid,
                                              content=content, ipaddr=ipaddr)
                
                # 记录回复添加成功
                comment_logger.info("回复添加成功", {
                    'trace_id': trace_id,
                    'user_id': userid,
                    'article_id': articleid,
                    'comment_id': commentid,
                    'content_length': len(content)
                })
                
                # 评论成功后，同步更新credit表明细、users表积分和article表回复数
                Credits().insert_detail(credit_type='回复评论', target=articleid, credit=2)
                Users().update_credit(2)
                Articles().update_replycount(articleid)
                
                # 记录积分更新
                comment_logger.info("回复积分更新", {
                    'trace_id': trace_id,
                    'user_id': userid,
                    'article_id': articleid,
                    'comment_id': commentid,
                    'credit_type': '回复评论',
                    'credit_value': 2
                })
                
                return 'reply-pass'
            except Exception as e:
                # 记录回复添加异常
                comment_logger.error("回复添加异常", {
                    'trace_id': trace_id,
                    'user_id': userid,
                    'article_id': articleid,
                    'comment_id': commentid,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                return 'reply-fail'
        else:
            # 记录频率限制
            comment_logger.warning("回复频率超限", {
                'trace_id': trace_id,
                'user_id': userid,
                'article_id': articleid,
                'comment_id': commentid,
                'limit_rule': '5_minutes'
            })
            return 'reply-limit'
    except Exception as e:
        # 记录全局异常
        comment_logger.error("回复添加全局异常", {
            'trace_id': trace_id,
            'error': str(e),
            'error_type': type(e).__name__,
            'request_path': request.path,
            'request_method': request.method
        })


# 为了使用Ajax分页，特创建此接口作为演示
# 由于分页栏已经完成渲染，此接口仅根据前端的页码请求后台对应数据
@comment.route('/comment/<int:articleid>-<int:page>')
def comment_page(articleid, page):
    """获取文章评论的分页数据
    
    根据文章ID和页码返回对应的评论数据，用于Ajax分页加载
    
    Args:
        articleid (int): 文章ID
        page (int): 页码，从1开始
        
    Returns:
        Response: JSON格式的评论数据
    """
    # 生成跟踪ID
    trace_id = get_comment_trace_id()
    
    # 记录评论分页请求
    comment_logger.info("评论分页请求", {
        'trace_id': trace_id,
        'article_id': articleid,
        'page': page,
        'user_id': session.get('userid'),
        'remote_addr': request.remote_addr
    })
    
    try:
        # 计算开始位置
        start = (page - 1) * 10
        page_size = 10
        
        # 记录分页参数
        comment_logger.info("评论分页参数", {
            'trace_id': trace_id,
            'article_id': articleid,
            'page': page,
            'start': start,
            'page_size': page_size
        })
        
        # 获取评论数据
        comment_instance = Comments()
        comment_data = comment_instance.get_comment_user_list(articleid, start, page_size)
        
        # 记录评论数据获取结果
        comment_logger.info("评论数据获取成功", {
            'trace_id': trace_id,
            'article_id': articleid,
            'page': page,
            'result_count': len(comment_data) if comment_data else 0
        })
        
        return jsonify(comment_data)
    except Exception as e:
        # 记录异常
        comment_logger.error("评论分页获取异常", {
            'trace_id': trace_id,
            'article_id': articleid,
            'page': page,
            'error': str(e),
            'error_type': type(e).__name__
        })
        # 返回空数组避免前端错误
        return jsonify([])
