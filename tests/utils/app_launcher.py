"""
简化的应用启动脚本，专用于测试环境
这个脚本直接启动Flask应用，无需任何额外的功能
"""

import os
import sys
import shutil
import time
import traceback
import argparse
import signal
import logging
import atexit
from flask import request, session
import hashlib
from woniunote.module.users import Users

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger("app_launcher")

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
logger.info(f"项目根目录: {project_root}")
sys.path.insert(0, project_root)

# 全局变量，用于保存配置备份路径
backup_files = []

# 确保测试配置文件存在
def setup_config():
    """设置测试配置文件"""
    global backup_files
    success = True
    config_paths = []
    
    # 设置用户密码配置
    # 应用期望的配置文件位置
    user_config_path = os.path.join(project_root, "woniunote", "configs", "user_password_config.yaml")
    
    # 创建备份（如果原文件存在）
    if os.path.exists(user_config_path):
        backup_path = user_config_path + ".bak"
        shutil.copy(user_config_path, backup_path)
        backup_files.append((user_config_path, backup_path))
        logger.info(f"已备份原用户配置文件到: {backup_path}")
    
    # 使用示例文件或测试文件创建配置
    example_config = os.path.join(project_root, "woniunote", "configs", "user_password_config_example.yaml")
    test_config = os.path.join(project_root, "tests", "configs", "user_password_config.yaml")
    
    # 使用现有的测试配置文件，如果不存在则使用示例文件
    source_config = test_config if os.path.exists(test_config) else example_config
    
    if os.path.exists(source_config):
        shutil.copy(source_config, user_config_path)
        logger.info(f"已复制用户配置文件从 {source_config} 到 {user_config_path}")
        config_paths.append(user_config_path)
    else:
        logger.error(f"错误: 找不到任何可用的用户配置文件")
        success = False
    
    # 设置文章类型配置
    article_config_path = os.path.join(project_root, "woniunote", "configs", "article_type_config.yaml")
    
    # 创建备份（如果原文件存在）
    if os.path.exists(article_config_path):
        backup_path = article_config_path + ".bak"
        shutil.copy(article_config_path, backup_path)
        backup_files.append((article_config_path, backup_path))
        logger.info(f"已备份原文章类型配置文件到: {backup_path}")
    
    # 使用测试文件或原始文件
    test_article_config = os.path.join(project_root, "tests", "configs", "article_type_config.yaml")
    
    if os.path.exists(test_article_config):
        shutil.copy(test_article_config, article_config_path)
        logger.info(f"已复制文章类型配置文件从 {test_article_config} 到 {article_config_path}")
        config_paths.append(article_config_path)
    else:
        logger.warning(f"警告: 找不到测试文章类型配置文件，使用原始配置")
        # 保持原有配置不变

    return success, config_paths

# 设置环境变量
os.environ["FLASK_APP"] = "woniunote.app"
os.environ["FLASK_ENV"] = "testing"

# 解析命令行参数
def parse_args():
    parser = argparse.ArgumentParser(description='启动测试用的Flask应用')
    parser.add_argument('--port', type=int, default=5001, help='Flask服务器端口')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Flask服务器主机')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--test-mode', action='store_true', help='启用测试模式（禁用HTTPS重定向）')
    return parser.parse_args()

# 恢复配置文件
def restore_config():
    """恢复原始配置文件"""
    global backup_files
    try:
        for target_path, backup_path in backup_files:
            if os.path.exists(backup_path):
                logger.info(f"正在恢复配置文件: {target_path}")
                shutil.copy(backup_path, target_path)
                os.remove(backup_path)
                logger.info(f"已恢复原始配置文件: {target_path}")
        
        # 清空备份列表
        backup_files = []
    except Exception as e:
        logger.error(f"恢复配置文件时出错: {e}")
        traceback.print_exc()

# 信号处理函数
def signal_handler(sig, frame):
    """处理信号，确保正常退出"""
    logger.info(f"收到信号 {sig}，准备退出...")
    restore_config()
    sys.exit(0)

def main():
    """主函数 - 启动Flask应用"""
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 注册退出处理
    atexit.register(restore_config)
    
    # 解析参数
    args = parse_args()
    
    # 先设置配置文件
    success, config_paths = setup_config()
    if not success:
        logger.error("无法设置测试配置文件，退出程序")
        sys.exit(1)
    
    port = args.port
    host = args.host
    debug = args.debug
    test_mode = args.test_mode
    
    try:
        logger.info(f"使用配置文件: {config_paths}")
        
        # 尝试直接导入 app 而不是 create_app
        try:
            from woniunote.app import app as flask_app
            logger.info("成功导入Flask应用")
        except ImportError:
            # 如果直接导入app失败，尝试导入create_app函数
            logger.info("尝试使用create_app函数初始化应用...")
            from woniunote.app import create_app
            flask_app = create_app('testing')
        
        # 添加健康检查端点
        if not any(rule.rule == '/health' for rule in flask_app.url_map.iter_rules()):
            @flask_app.route('/health')
            def health_check():
                return {'status': 'ok', 'timestamp': time.time()}, 200
        else:
            logger.info("健康检查端点 '/health' 已存在，跳过添加")
            
            # 添加一个测试端点，确保应用可以响应
            @flask_app.route('/test-health')
            def test_health_check():
                return {'status': 'ok', 'timestamp': time.time(), 'test': True}, 200
        
        # 禁用HTTP到HTTPS的重定向，确保测试环境可以使用HTTP
        if test_mode:
            logger.info("正在禁用测试环境中的HTTP到HTTPS重定向...")
            
            # 找到并替换before_request处理器
            for func in flask_app.before_request_funcs.get(None, []):
                # 检查函数是否是重定向处理器
                if func.__name__ == 'before':
                    # 保存原始函数以便参考
                    original_before = func
                    
                    # 创建一个新函数，跳过HTTPS重定向部分
                    @flask_app.before_request
                    def modified_before():
                        url = request.path
                        pass_list = ['/user', '/login', '/logout', '/vcode']
                        
                        if url in pass_list or url.endswith('.js') or url.endswith('.jpg'):
                            return
                            
                        # 检查session是否存在，其余逻辑保持不变
                        session_id = request.cookies.get('session_id')
                        if session_id and session.get(f'islogin_{session_id}') == 'true':
                            return
                            
                        if session.get('islogin') is None:
                            username = request.cookies.get('username')
                            password = request.cookies.get('password')
                            
                            if username is not None and password is not None:
                                user_ = Users()
                                result = user_.find_by_username(username)
                                
                                if len(result) == 1 and hashlib.md5(password.encode()).hexdigest() == result[0].password:
                                    # 设置session
                                    session['islogin'] = 'true'
                                    session['userid'] = result[0].userid
                                    session['username'] = username
                                    session['nickname'] = result[0].nickname
                                    session['role'] = result[0].role
                                    # 确保session被保存
                                    session.modified = True
                                return
                    
                    # 移除原始函数并注册新函数
                    flask_app.before_request_funcs[None].remove(func)
                    # 新函数已通过装饰器注册，不需要再次添加
                    
                    logger.info("已成功禁用HTTP到HTTPS重定向")
                    break
        
        logger.info(f"启动Flask服务器在 {host}:{port}...")
        logger.info("注意: 始终使用HTTP协议启动，不支持HTTPS")
        
        # 使用非阻塞方式启动服务器，以便可以响应信号
        # 注意: 不传入ssl_context参数，确保使用HTTP
        flask_app.run(
            host=host, 
            port=port, 
            debug=debug, 
            threaded=True, 
            use_reloader=False,  # 禁用重载器，避免创建子进程
            ssl_context=None  # 显式设置为None，确保使用HTTP
        )
    except Exception as e:
        logger.error(f"启动Flask应用时出错: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
