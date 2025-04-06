"""
路由监视器：实时监控所有路由函数的返回值，并捕获类型错误
"""

from flask import Flask, make_response, jsonify, render_template, redirect, url_for, Response, request
from functools import wraps
import inspect
import types
import logging
import traceback
import sys

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('route_debug.log', 'w', 'utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('route_monitor')

def wrap_route_functions(app):
    """包装所有路由函数，检查它们的返回值类型"""
    for endpoint, view_func in app.view_functions.items():
        logger.info(f"正在包装路由函数: {endpoint}")
        
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            try:
                logger.info(f"执行路由函数: {endpoint}")
                result = view_func(*args, **kwargs)
                logger.info(f"路由函数 {endpoint} 返回类型: {type(result)}")
                
                # 检查返回值类型
                if isinstance(result, int):
                    logger.error(f"路由函数 {endpoint} 返回了整数: {result}")
                    # 将整数转换为有效的响应
                    if result == 404:
                        return render_template('error-404.html'), 404
                    elif result == 200 or result == 0:
                        # 假设这是一个“成功”的响应，我们尝试返回页面
                        # 首先检查是否和某个类别或页面相关
                        if 'category' in endpoint or 'todo' in endpoint:
                            # Todo相关路由
                            return redirect(url_for('tcenter.category', id=1))
                        elif 'card' in endpoint:
                            # Card相关路由
                            return redirect(url_for('ccenter.card_index'))
                        else:
                            # 默认返回主页
                            return redirect(url_for('index'))
                    elif result >= 400:
                        # 错误应该返回错误页面
                        return render_template('error-404.html'), result
                    else:
                        # 其他情况，尝试重定向到主页
                        return redirect(url_for('index'))
                
                return result
            except Exception as e:
                logger.error(f"路由函数 {endpoint} 执行出错: {str(e)}")
                logger.error(traceback.format_exc())
                # 返回500错误响应
                return render_template('error-500.html'), 500
        
        # 替换原始视图函数
        app.view_functions[endpoint] = wrapped_view
    
    logger.info("所有路由函数已被包装")
    return app

# 在应用生成后调用此函数
def enable_route_monitoring(app):
    """启用路由监控"""
    # 包装路由函数
    app = wrap_route_functions(app)
    
    # 包装make_response函数，捕获TypeError
    original_make_response = app.make_response
    
    @wraps(original_make_response)
    def wrapped_make_response(rv):
        try:
            logger.info(f"处理响应: {type(rv)}")
            if isinstance(rv, int):
                logger.error(f"检测到整数响应: {rv}")
                if rv == 404:
                    return original_make_response((render_template('error-404.html'), 404))
                elif rv == 200 or rv == 0:
                    # 正常业务处理完成，应该返回成功页面
                    # 尝试猜测当前请求的目标页面
                    try:
                        from flask import request, redirect, url_for
                        path = request.path
                        if '/todo' in path:
                            return original_make_response(redirect(url_for('tcenter.category', id=1)))
                        elif '/card' in path:
                            return original_make_response(redirect(url_for('ccenter.card_index')))
                        else:
                            return original_make_response(redirect(url_for('index')))
                    except Exception as e:
                        logger.error(f"处理整数响应时出错: {str(e)}")
                        # 默认返回主页
                        return original_make_response((render_template('index.html'), 200))
                elif rv >= 400:
                    return original_make_response((render_template('error-404.html'), rv))
                else:
                    # 其他整数情况，返回主页
                    return original_make_response((render_template('index.html'), 200))
            return original_make_response(rv)
        except TypeError as e:
            if "view function did not return a valid response" in str(e):
                # 获取错误发生时的堆栈跟踪
                tb = traceback.format_exc()
                logger.error(f"TypeError 异常: {str(e)}\n{tb}")
                # 尝试恢复
                return original_make_response(jsonify({"error": "Server Error"}), 500)
            raise
        except Exception as e:
            logger.error(f"处理响应时出错: {str(e)}")
            logger.error(traceback.format_exc())
            # 尝试恢复
            return original_make_response(jsonify({"error": "Server Error"}), 500)
    
    # 替换原始函数
    app.make_response = wrapped_make_response
    
    logger.info("路由监控已启用")
    return app
