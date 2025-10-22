#!/usr/bin/env python3
"""
缩略图功能测试
测试缩略图的自动创建和处理功能
"""

import unittest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

class TestThumbnailFunctionality(unittest.TestCase):
    """缩略图功能测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.thumb_dir = os.path.join(self.test_dir, 'thumb')
        os.makedirs(self.thumb_dir, exist_ok=True)
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_create_thumb_png_function(self):
        """测试create_thumb_png函数"""
        try:
            from woniunote.common.utils import create_thumb_png
            
            # 测试创建缩略图
            thumbnail = create_thumb_png(width=226, height=136, text="测试")
            self.assertIsNotNone(thumbnail)
            
            # 测试保存缩略图
            test_file = os.path.join(self.thumb_dir, 'test.png')
            thumbnail.save(test_file, 'PNG')
            self.assertTrue(os.path.exists(test_file))
            
        except ImportError:
            self.skipTest("PIL库未安装，跳过缩略图创建测试")
        except Exception as e:
            self.fail(f"创建缩略图失败: {e}")
    
    def test_create_missing_thumbnail_function(self):
        """测试create_missing_thumbnail函数"""
        try:
            # 导入函数
            import sys
            sys.path.insert(0, str(Path.cwd()))
            from woniunote.app import create_missing_thumbnail
            
            # 测试创建缺失的缩略图
            result = create_missing_thumbnail(self.thumb_dir, 11, '11.png')
            self.assertTrue(result)
            
            # 验证文件是否创建
            test_file = os.path.join(self.thumb_dir, '11.png')
            self.assertTrue(os.path.exists(test_file))
            
        except ImportError:
            self.skipTest("PIL库未安装，跳过缩略图创建测试")
        except Exception as e:
            self.fail(f"创建缺失缩略图失败: {e}")
    
    def test_create_default_thumbnail_function(self):
        """测试create_default_thumbnail函数"""
        try:
            # 导入函数
            import sys
            sys.path.insert(0, str(Path.cwd()))
            from woniunote.app import create_default_thumbnail
            
            # 测试创建默认缩略图
            result = create_default_thumbnail(self.thumb_dir, 'default.png')
            self.assertTrue(result)
            
            # 验证文件是否创建
            test_file = os.path.join(self.thumb_dir, 'default.png')
            self.assertTrue(os.path.exists(test_file))
            
        except ImportError:
            self.skipTest("PIL库未安装，跳过缩略图创建测试")
        except Exception as e:
            self.fail(f"创建默认缩略图失败: {e}")
    
    def test_thumbnail_type_mapping(self):
        """测试缩略图类型映射"""
        try:
            import sys
            sys.path.insert(0, str(Path.cwd()))
            from woniunote.app import create_missing_thumbnail
            
            # 测试不同类型的缩略图创建
            test_cases = [
                (1, "技术"),
                (11, "教育"), 
                (101, "技术"),  # 子类型应该映射到主类型
                (999, "类型999")  # 未知类型
            ]
            
            for type_id, expected_category in test_cases:
                filename = f"{type_id}.png"
                result = create_missing_thumbnail(self.thumb_dir, type_id, filename)
                self.assertTrue(result, f"创建类型{type_id}的缩略图失败")
                
                # 验证文件存在
                test_file = os.path.join(self.thumb_dir, filename)
                self.assertTrue(os.path.exists(test_file), f"缩略图文件{filename}不存在")
                
        except ImportError:
            self.skipTest("PIL库未安装，跳过缩略图创建测试")
        except Exception as e:
            self.fail(f"缩略图类型映射测试失败: {e}")
    
    def test_thumbnail_file_exists_check(self):
        """测试缩略图文件存在性检查"""
        # 创建一个测试文件
        test_file = os.path.join(self.thumb_dir, 'existing.png')
        with open(test_file, 'w') as f:
            f.write('test')
        
        # 验证文件存在
        self.assertTrue(os.path.exists(test_file))
        
        # 验证不存在的文件
        non_existing = os.path.join(self.thumb_dir, 'non_existing.png')
        self.assertFalse(os.path.exists(non_existing))
    
    def test_thumbnail_directory_creation(self):
        """测试缩略图目录创建"""
        try:
            import sys
            sys.path.insert(0, str(Path.cwd()))
            from woniunote.app import create_missing_thumbnail
            
            # 删除测试目录
            if os.path.exists(self.thumb_dir):
                shutil.rmtree(self.thumb_dir)
            
            # 确认目录不存在
            self.assertFalse(os.path.exists(self.thumb_dir))
            
            # 创建缩略图（应该自动创建目录）
            result = create_missing_thumbnail(self.thumb_dir, 1, '1.png')
            self.assertTrue(result)
            
            # 验证目录和文件都被创建
            self.assertTrue(os.path.exists(self.thumb_dir))
            self.assertTrue(os.path.exists(os.path.join(self.thumb_dir, '1.png')))
            
        except ImportError:
            self.skipTest("PIL库未安装，跳过缩略图创建测试")
        except Exception as e:
            self.fail(f"缩略图目录创建测试失败: {e}")
    
    def test_actual_thumbnail_files(self):
        """测试实际的缩略图文件"""
        thumb_dir = Path("woniunote/resource/thumb")
        
        if not thumb_dir.exists():
            self.skipTest("缩略图目录不存在，跳过测试")
        
        # 检查11.png是否存在（这是报错中提到的文件）
        file_11 = thumb_dir / "11.png"
        self.assertTrue(file_11.exists(), "11.png文件应该存在")
        
        # 检查文件大小是否合理
        if file_11.exists():
            file_size = file_11.stat().st_size
            self.assertGreater(file_size, 0, "11.png文件不应该为空")
            self.assertLess(file_size, 50000, "11.png文件大小应该合理")  # 小于50KB
    
    def test_error_handling(self):
        """测试错误处理"""
        try:
            import sys
            sys.path.insert(0, str(Path.cwd()))
            from woniunote.app import create_missing_thumbnail, create_default_thumbnail
            
            # 测试无效路径
            result = create_missing_thumbnail("/invalid/path", 1, "test.png")
            self.assertFalse(result)  # 应该返回False而不是抛出异常
            
            # 测试无效参数
            result = create_default_thumbnail("/invalid/path", "test.png")
            self.assertFalse(result)  # 应该返回False而不是抛出异常
            
        except ImportError:
            self.skipTest("PIL库未安装，跳过错误处理测试")
        except Exception as e:
            # 如果抛出了其他异常，测试失败
            self.fail(f"错误处理测试失败: {e}")

class TestThumbnailIntegration(unittest.TestCase):
    """缩略图集成测试"""
    
    def test_thumbnail_route_exists(self):
        """测试缩略图路由是否存在"""
        try:
            import sys
            sys.path.insert(0, str(Path.cwd()))
            
            # 这里我们只测试函数是否可以导入，不实际启动Flask应用
            from woniunote.app import create_app
            
            # 验证create_app函数存在
            self.assertTrue(callable(create_app))
            
        except ImportError as e:
            self.skipTest(f"无法导入应用模块: {e}")
    
    def test_thumbnail_utils_integration(self):
        """测试缩略图工具集成"""
        try:
            from woniunote.common.utils import create_thumb_png
            
            # 测试工具函数可以正常调用
            thumbnail = create_thumb_png(width=100, height=100, text="测试")
            self.assertIsNotNone(thumbnail)
            
        except ImportError:
            self.skipTest("PIL库未安装或utils模块不可用")
        except Exception as e:
            self.fail(f"缩略图工具集成测试失败: {e}")

def run_thumbnail_tests():
    """运行缩略图测试"""
    # 创建测试套件
    suite = unittest.TestSuite()
    
    # 添加测试用例
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestThumbnailFunctionality))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestThumbnailIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_thumbnail_tests()
    exit(0 if success else 1)
