"""
用于调试WoniuNote应用中的路由函数返回值问题
此脚本将包装所有视图函数，记录其返回值类型，以便找出返回整数的函数
"""

from flask import Flask, request, render_template, session, flash, redirect, url_for
import inspect
import logging
import sys
import os
import importlib
import traceback

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='route_debug.log',
    filemode='w'
)
logger = logging.getLogger('route_debug')

def debug_routes(app):
    """分析Flask应用中的所有路由函数，查找可能返回整数的函数"""
    
    # 记录所有路由信息
    logger.info("开始分析路由函数...")
    for rule in app.url_map.iter_rules():
        endpoint = rule.endpoint
        try:
            if '.' in endpoint:
                blueprint_name, view_name = endpoint.split('.')
                logger.info(f"检查Blueprint路由: {rule.rule} -> {blueprint_name}.{view_name}")
            else:
                view_name = endpoint
                logger.info(f"检查应用路由: {rule.rule} -> {view_name}")
        except Exception as e:
            logger.error(f"分析路由 {rule.rule} 时出错: {str(e)}")
    
    # 覆写Flask的视图处理逻辑，增加返回值类型检查
    original_full_dispatch_request = app.full_dispatch_request
    
    def traced_full_dispatch_request():
        try:
            # 记录当前请求信息
            logger.info(f"当前请求: {request.method} {request.path}")
            # 调用原始的处理函数
            response = original_full_dispatch_request()
            return response
        except TypeError as e:
            if "view function did not return a valid response" in str(e):
                # 获取错误发生时的堆栈跟踪
                tb = traceback.format_exc()
                logger.error(f"TypeError 异常: {str(e)}\n{tb}")
                
                # 尝试从堆栈跟踪中识别出错的视图函数
                try:
                    frames = inspect.trace()
                    func_frame = None
                    for frame in frames:
                        func_name = frame.function
                        if func_name.startswith('view_'):
                            func_frame = frame
                            break
                        
                    if func_frame:
                        logger.error(f"出错的视图函数: {func_frame.function}")
                        logger.error(f"视图函数局部变量: {func_frame.frame.f_locals}")
                    else:
                        logger.error("无法识别出错的视图函数")
                except Exception as inner_e:
                    logger.error(f"分析出错视图函数时出错: {str(inner_e)}")
            
            # 重新抛出异常，让Flask的常规错误处理器处理
            raise
        except Exception as e:
            logger.error(f"其他异常: {str(e)}\n{traceback.format_exc()}")
            raise
    
    # 替换Flask的请求分发方法
    app.full_dispatch_request = traced_full_dispatch_request
    
    logger.info("路由函数调试器已启用")
    
    return app

def debug_run():
    """运行包含调试逻辑的WoniuNote应用"""
    try:
        # 导入原始应用
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from woniunote.app import app as original_app
        
        # 添加调试逻辑
        app = debug_routes(original_app)
        
        # 运行应用
        path = original_app.config.get('PACKAGE_PATH', '')
        ssl_context = None
        if path:
            ssl_context = (path + "/configs/cert.pem", path + "/configs/key.pem")
            
        app.run(host="127.0.0.1", debug=True, port=5000, ssl_context=ssl_context)
        
    except Exception as e:
        logger.error(f"启动调试应用时出错: {str(e)}\n{traceback.format_exc()}")
        raise

if __name__ == "__main__":
    debug_run()
