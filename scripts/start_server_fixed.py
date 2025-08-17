#!/usr/bin/env python3
"""
WoniuNote 服务器启动脚本 (修复版)
解决模块导入路径问题并提供更好的错误处理
"""
import os
import sys
import argparse
from pathlib import Path

def setup_environment():
    """设置环境变量和Python路径"""
    # 获取项目根目录
    project_root = Path(__file__).parent.parent.absolute()
    
    # 添加项目根目录到Python路径
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # 设置环境变量
    os.environ['PYTHONPATH'] = f"{project_root}:{os.environ.get('PYTHONPATH', '')}"
    os.environ['FLASK_APP'] = 'woniunote.app'
    
    print(f"✓ 项目根目录: {project_root}")
    print(f"✓ Python路径已设置")
    
    return project_root

def check_dependencies():
    """检查必要的依赖"""
    required_modules = [
        'flask',
        'sqlalchemy', 
        'redis',
        'pymysql',
        'werkzeug'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"❌ 缺少依赖模块: {', '.join(missing_modules)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    print("✓ 所有依赖模块检查通过")
    return True

def check_configuration():
    """检查配置文件"""
    project_root = Path(__file__).parent.parent
    
    config_files = [
        'woniunote/common/database.py',
        'woniunote/common/utils.py',
        'configs/config.py'
    ]
    
    missing_configs = []
    for config_file in config_files:
        config_path = project_root / config_file
        if not config_path.exists():
            missing_configs.append(config_file)
    
    if missing_configs:
        print(f"⚠️ 缺少配置文件: {', '.join(missing_configs)}")
    else:
        print("✓ 配置文件检查通过")
    
    return len(missing_configs) == 0

def start_server(host='0.0.0.0', port=5001, debug=True, optimized=False):
    """启动Flask服务器"""
    try:
        print("\n🚀 正在启动 WoniuNote 服务器...")
        
        if optimized:
            print("📊 使用优化版本启动")
            # 导入优化版本的应用工厂
            from woniunote.app_factory import create_app
            app = create_app('development')
            
            # 启动清理管理器和监控系统
            try:
                from woniunote.common.cleanup_manager import start_cleanup_manager
                start_cleanup_manager()
                print("✓ 清理管理器已启动")
            except Exception as e:
                print(f"⚠️ 清理管理器启动失败: {e}")
            
        else:
            print("📱 使用标准版本启动")
            # 导入标准应用
            from woniunote.app import app
        
        print(f"✓ 应用创建成功")
        print(f"🌐 服务器将在 http://{host}:{port} 启动")
        
        if debug:
            print("🔧 开发模式 (Debug=True)")
        
        # 启动服务器
        app.run(host=host, port=port, debug=debug, threaded=True)
        
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        print("\n🔧 可能的解决方案:")
        print("1. 检查PYTHONPATH是否正确设置")
        print("2. 确保所有依赖已安装: pip install -r requirements.txt")
        print("3. 验证项目结构完整性")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='WoniuNote 服务器启动脚本')
    parser.add_argument('--host', default='0.0.0.0', help='服务器主机地址')
    parser.add_argument('--port', type=int, default=5001, help='服务器端口')
    parser.add_argument('--debug', action='store_true', default=True, help='启用调试模式')
    parser.add_argument('--no-debug', action='store_true', help='禁用调试模式')
    parser.add_argument('--optimized', action='store_true', help='使用优化版本')
    parser.add_argument('--check-only', action='store_true', help='仅执行检查，不启动服务器')
    
    args = parser.parse_args()
    
    # 如果指定了--no-debug，覆盖debug设置
    if args.no_debug:
        args.debug = False
    
    print("🔍 WoniuNote 服务器启动检查")
    print("=" * 50)
    
    # 设置环境
    project_root = setup_environment()
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查配置
    config_ok = check_configuration()
    if not config_ok:
        print("⚠️ 配置检查未完全通过，但将尝试启动")
    
    # 如果只是检查，不启动服务器
    if args.check_only:
        print("\n✅ 检查完成")
        return
    
    print("\n" + "=" * 50)
    
    # 启动服务器
    start_server(
        host=args.host,
        port=args.port,
        debug=args.debug,
        optimized=args.optimized
    )

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 服务器被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 启动脚本异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)