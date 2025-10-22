#!/usr/bin/env python3
"""
Windows Redis 自动安装配置脚本
用于解决 Redis客户端未配置，Redis缓存功能不可用 的问题

功能：
1. 自动下载Redis for Windows
2. 安装和配置Redis服务
3. 启动Redis服务
4. 验证Redis连接
5. 配置环境变量

作者: WoniuNote Team
版本: 1.0.0
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil
import time
import json
import winreg
from pathlib import Path
from typing import Optional, Dict, Any

class RedisInstaller:
    """Windows Redis 安装器"""
    
    def __init__(self):
        self.redis_version = "5.0.14.1"  # 稳定版本
        self.redis_download_url = f"https://github.com/tporadowski/redis/releases/download/v{self.redis_version}/Redis-x64-{self.redis_version}.zip"
        self.redis_backup_url = "https://download.redis.io/redis-stable.tar.gz"  # 备用下载地址
        
        # 安装路径
        self.install_dir = Path("C:/Program Files/Redis")
        self.redis_exe = self.install_dir / "redis-server.exe"
        self.redis_cli = self.install_dir / "redis-cli.exe"
        self.redis_conf = self.install_dir / "redis.windows.conf"
        
        # 临时目录
        self.temp_dir = Path.cwd() / "temp_redis_install"
        self.download_file = self.temp_dir / f"Redis-x64-{self.redis_version}.zip"
        
        # Redis配置
        self.redis_config = {
            'port': 6379,
            'bind': '127.0.0.1',
            'timeout': 0,
            'tcp-keepalive': 300,
            'daemonize': 'no',  # Windows不支持daemon模式
            'supervised': 'no',
            'pidfile': '',
            'loglevel': 'notice',
            'logfile': str(self.install_dir / 'redis.log'),
            'databases': 16,
            'save': ['900 1', '300 10', '60 10000'],
            'stop-writes-on-bgsave-error': 'yes',
            'rdbcompression': 'yes',
            'rdbchecksum': 'yes',
            'dbfilename': 'dump.rdb',
            'dir': str(self.install_dir),
            'maxmemory-policy': 'allkeys-lru',
            'maxmemory': '256mb'
        }
    
    def check_admin_privileges(self) -> bool:
        """检查是否有管理员权限"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def request_admin_privileges(self):
        """请求管理员权限"""
        if not self.check_admin_privileges():
            print("需要管理员权限来安装Redis服务...")
            print("请以管理员身份重新运行此脚本")
            
            # 尝试以管理员身份重新启动
            try:
                import ctypes
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, " ".join(sys.argv), None, 1
                )
            except:
                pass
            sys.exit(1)
    
    def check_redis_installed(self) -> bool:
        """检查Redis是否已安装"""
        return self.redis_exe.exists() and self.redis_cli.exists()
    
    def check_redis_running(self) -> bool:
        """检查Redis服务是否运行"""
        try:
            result = subprocess.run(
                ['sc', 'query', 'Redis'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return 'RUNNING' in result.stdout
        except:
            return False
    
    def test_redis_connection(self) -> bool:
        """测试Redis连接"""
        try:
            if not self.redis_cli.exists():
                return False
            
            result = subprocess.run(
                [str(self.redis_cli), 'ping'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return 'PONG' in result.stdout
        except:
            return False
    
    def download_redis(self) -> bool:
        """下载Redis"""
        print(f"正在下载Redis {self.redis_version}...")
        
        # 创建临时目录
        self.temp_dir.mkdir(exist_ok=True)
        
        try:
            # 下载进度回调
            def show_progress(block_num, block_size, total_size):
                downloaded = block_num * block_size
                if total_size > 0:
                    percent = min(100, (downloaded * 100) // total_size)
                    print(f"\r下载进度: {percent}% ({downloaded}/{total_size} bytes)", end='')
            
            urllib.request.urlretrieve(
                self.redis_download_url,
                str(self.download_file),
                show_progress
            )
            print("\n下载完成!")
            return True
            
        except Exception as e:
            print(f"\n下载失败: {e}")
            return False
    
    def extract_redis(self) -> bool:
        """解压Redis"""
        print("正在解压Redis...")
        
        try:
            with zipfile.ZipFile(str(self.download_file), 'r') as zip_ref:
                zip_ref.extractall(str(self.temp_dir))
            
            print("解压完成!")
            return True
            
        except Exception as e:
            print(f"解压失败: {e}")
            return False
    
    def install_redis(self) -> bool:
        """安装Redis"""
        print("正在安装Redis...")
        
        try:
            # 创建安装目录
            self.install_dir.mkdir(parents=True, exist_ok=True)
            
            # 查找解压后的Redis文件
            extracted_files = list(self.temp_dir.rglob("redis-server.exe"))
            if not extracted_files:
                print("未找到Redis可执行文件")
                return False
            
            redis_source_dir = extracted_files[0].parent
            
            # 复制Redis文件到安装目录
            for file in redis_source_dir.glob("*"):
                if file.is_file():
                    shutil.copy2(str(file), str(self.install_dir))
            
            print(f"Redis已安装到: {self.install_dir}")
            return True
            
        except Exception as e:
            print(f"安装失败: {e}")
            return False
    
    def create_redis_config(self) -> bool:
        """创建Redis配置文件"""
        print("正在创建Redis配置文件...")
        
        try:
            config_content = []
            
            # 基本配置
            config_content.append("# Redis配置文件 - 由WoniuNote自动生成")
            config_content.append(f"port {self.redis_config['port']}")
            config_content.append(f"bind {self.redis_config['bind']}")
            config_content.append(f"timeout {self.redis_config['timeout']}")
            config_content.append(f"tcp-keepalive {self.redis_config['tcp-keepalive']}")
            config_content.append(f"loglevel {self.redis_config['loglevel']}")
            config_content.append(f"logfile \"{self.redis_config['logfile']}\"")
            config_content.append(f"databases {self.redis_config['databases']}")
            
            # 持久化配置
            for save_rule in self.redis_config['save']:
                config_content.append(f"save {save_rule}")
            
            config_content.append(f"stop-writes-on-bgsave-error {self.redis_config['stop-writes-on-bgsave-error']}")
            config_content.append(f"rdbcompression {self.redis_config['rdbcompression']}")
            config_content.append(f"rdbchecksum {self.redis_config['rdbchecksum']}")
            config_content.append(f"dbfilename {self.redis_config['dbfilename']}")
            config_content.append(f"dir \"{self.redis_config['dir']}\"")
            
            # 内存管理
            config_content.append(f"maxmemory {self.redis_config['maxmemory']}")
            config_content.append(f"maxmemory-policy {self.redis_config['maxmemory-policy']}")
            
            # Windows特定配置
            config_content.append("")
            config_content.append("# Windows特定配置")
            config_content.append("# 禁用一些Linux特有功能")
            config_content.append("# daemonize no")
            config_content.append("# supervised no")
            
            # 写入配置文件
            with open(self.redis_conf, 'w', encoding='utf-8') as f:
                f.write('\n'.join(config_content))
            
            print(f"配置文件已创建: {self.redis_conf}")
            return True
            
        except Exception as e:
            print(f"创建配置文件失败: {e}")
            return False
    
    def install_redis_service(self) -> bool:
        """安装Redis Windows服务"""
        print("正在安装Redis Windows服务...")
        
        try:
            # 检查是否已存在服务
            result = subprocess.run(
                ['sc', 'query', 'Redis'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("Redis服务已存在，正在删除旧服务...")
                subprocess.run(['sc', 'stop', 'Redis'], capture_output=True)
                time.sleep(2)
                subprocess.run(['sc', 'delete', 'Redis'], capture_output=True)
                time.sleep(2)
            
            # 安装新服务
            service_cmd = [
                'sc', 'create', 'Redis',
                'binPath=', f'"{self.redis_exe}" "{self.redis_conf}"',
                'DisplayName=', 'Redis Server',
                'start=', 'auto'
            ]
            
            result = subprocess.run(service_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("Redis服务安装成功!")
                return True
            else:
                print(f"服务安装失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"安装服务失败: {e}")
            return False
    
    def start_redis_service(self) -> bool:
        """启动Redis服务"""
        print("正在启动Redis服务...")
        
        try:
            result = subprocess.run(
                ['sc', 'start', 'Redis'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("Redis服务启动成功!")
                time.sleep(3)  # 等待服务完全启动
                return True
            else:
                print(f"服务启动失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"启动服务失败: {e}")
            return False
    
    def add_to_path(self) -> bool:
        """将Redis添加到系统PATH"""
        print("正在添加Redis到系统PATH...")
        
        try:
            # 获取当前系统PATH
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                              r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                              0, winreg.KEY_ALL_ACCESS) as key:
                
                current_path, _ = winreg.QueryValueEx(key, "Path")
                redis_path = str(self.install_dir)
                
                if redis_path not in current_path:
                    new_path = f"{current_path};{redis_path}"
                    winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                    print("Redis已添加到系统PATH")
                else:
                    print("Redis已在系统PATH中")
            
            return True
            
        except Exception as e:
            print(f"添加到PATH失败: {e}")
            return False
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        print("正在清理临时文件...")
        
        try:
            if self.temp_dir.exists():
                shutil.rmtree(str(self.temp_dir))
            print("临时文件清理完成")
        except Exception as e:
            print(f"清理临时文件失败: {e}")
    
    def create_redis_scripts(self) -> bool:
        """创建Redis管理脚本"""
        print("正在创建Redis管理脚本...")
        
        try:
            # 启动脚本
            start_script = self.install_dir / "start_redis.bat"
            with open(start_script, 'w', encoding='utf-8') as f:
                f.write('@echo off\n')
                f.write('echo 启动Redis服务...\n')
                f.write('sc start Redis\n')
                f.write('echo Redis服务已启动\n')
                f.write('pause\n')
            
            # 停止脚本
            stop_script = self.install_dir / "stop_redis.bat"
            with open(stop_script, 'w', encoding='utf-8') as f:
                f.write('@echo off\n')
                f.write('echo 停止Redis服务...\n')
                f.write('sc stop Redis\n')
                f.write('echo Redis服务已停止\n')
                f.write('pause\n')
            
            # 状态检查脚本
            status_script = self.install_dir / "redis_status.bat"
            with open(status_script, 'w', encoding='utf-8') as f:
                f.write('@echo off\n')
                f.write('echo 检查Redis服务状态...\n')
                f.write('sc query Redis\n')
                f.write('echo.\n')
                f.write('echo 测试Redis连接...\n')
                f.write(f'"{self.redis_cli}" ping\n')
                f.write('pause\n')
            
            print("Redis管理脚本创建完成")
            return True
            
        except Exception as e:
            print(f"创建管理脚本失败: {e}")
            return False
    
    def validate_installation(self) -> Dict[str, Any]:
        """验证Redis安装"""
        print("\n正在验证Redis安装...")
        
        validation_result = {
            'redis_installed': False,
            'service_running': False,
            'connection_test': False,
            'config_exists': False,
            'path_added': False
        }
        
        # 检查Redis文件
        validation_result['redis_installed'] = self.check_redis_installed()
        print(f"Redis文件检查: {'✓' if validation_result['redis_installed'] else '✗'}")
        
        # 检查配置文件
        validation_result['config_exists'] = self.redis_conf.exists()
        print(f"配置文件检查: {'✓' if validation_result['config_exists'] else '✗'}")
        
        # 检查服务状态
        validation_result['service_running'] = self.check_redis_running()
        print(f"服务运行检查: {'✓' if validation_result['service_running'] else '✗'}")
        
        # 检查连接
        if validation_result['service_running']:
            time.sleep(2)  # 等待服务稳定
            validation_result['connection_test'] = self.test_redis_connection()
        print(f"连接测试: {'✓' if validation_result['connection_test'] else '✗'}")
        
        # 检查PATH
        try:
            result = subprocess.run(['redis-cli', '--version'], 
                                  capture_output=True, text=True)
            validation_result['path_added'] = result.returncode == 0
        except:
            validation_result['path_added'] = False
        print(f"PATH配置: {'✓' if validation_result['path_added'] else '✗'}")
        
        return validation_result
    
    def install(self) -> bool:
        """执行完整安装流程"""
        print("="*60)
        print("Windows Redis 自动安装程序")
        print("="*60)
        
        # 检查管理员权限
        self.request_admin_privileges()
        
        # 检查是否已安装
        if self.check_redis_installed():
            print("检测到Redis已安装")
            if self.check_redis_running():
                print("Redis服务正在运行")
                if self.test_redis_connection():
                    print("Redis连接测试成功!")
                    print("Redis环境已正确配置，无需重新安装")
                    return True
        
        try:
            # 下载Redis
            if not self.download_redis():
                return False
            
            # 解压Redis
            if not self.extract_redis():
                return False
            
            # 安装Redis
            if not self.install_redis():
                return False
            
            # 创建配置文件
            if not self.create_redis_config():
                return False
            
            # 安装Windows服务
            if not self.install_redis_service():
                return False
            
            # 启动服务
            if not self.start_redis_service():
                return False
            
            # 添加到PATH
            self.add_to_path()
            
            # 创建管理脚本
            self.create_redis_scripts()
            
            # 验证安装
            validation_result = self.validate_installation()
            
            # 清理临时文件
            self.cleanup_temp_files()
            
            # 显示结果
            print("\n" + "="*60)
            print("Redis安装完成!")
            print("="*60)
            
            if all(validation_result.values()):
                print("✓ 所有检查项都通过!")
                print(f"✓ Redis服务器地址: 127.0.0.1:6379")
                print(f"✓ 配置文件位置: {self.redis_conf}")
                print(f"✓ 安装目录: {self.install_dir}")
                print("\n管理脚本:")
                print(f"  启动服务: {self.install_dir}/start_redis.bat")
                print(f"  停止服务: {self.install_dir}/stop_redis.bat")
                print(f"  状态检查: {self.install_dir}/redis_status.bat")
                
                print("\n环境变量配置:")
                print("  REDIS_HOST=127.0.0.1")
                print("  REDIS_PORT=6379")
                print("  REDIS_DB=0")
                
                return True
            else:
                print("⚠ 部分检查项未通过，请检查安装")
                return False
                
        except Exception as e:
            print(f"安装过程中出现错误: {e}")
            self.cleanup_temp_files()
            return False

def main():
    """主函数"""
    installer = RedisInstaller()
    
    try:
        success = installer.install()
        if success:
            print("\n🎉 Redis安装成功!")
            print("现在可以在WoniuNote项目中使用Redis缓存功能了")
        else:
            print("\n❌ Redis安装失败")
            print("请检查错误信息并重试")
        
        input("\n按回车键退出...")
        
    except KeyboardInterrupt:
        print("\n\n安装被用户取消")
        installer.cleanup_temp_files()
    except Exception as e:
        print(f"\n安装过程中出现未预期的错误: {e}")
        installer.cleanup_temp_files()

if __name__ == "__main__":
    main()
