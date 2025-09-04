#!/usr/bin/env python3
"""
WoniuNote todo修复工具测试
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from woniunote.fix_todo import fix_controller_file, main


class TestFixTodo:
    """测试todo修复工具"""

    def test_fix_controller_file_exists(self):
        """测试fix_controller_file函数存在"""
        assert callable(fix_controller_file)

    def test_main_function_exists(self):
        """测试main函数存在"""
        assert callable(main)

    def test_fix_controller_file_basic_replacement(self):
        """测试控制器文件修复基本替换功能"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""def test_function():
    return 404
    return "normal response"
""")
            temp_file = f.name

        try:
            # 修复文件
            fix_controller_file(temp_file)

            # 验证修复结果
            with open(temp_file, 'r') as f:
                content = f.read()

            # 验证替换是否成功
            assert "return render_template('error-404.html'), 404" in content
            assert "return 404" not in content
            assert "return \"normal response\"" in content

        finally:
            # 清理临时文件
            os.unlink(temp_file)

    def test_fix_controller_file_no_changes_needed(self):
        """测试不需要修复的文件"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""def test_function():
    return "normal response"
    return render_template('page.html')
""")
            temp_file = f.name

        try:
            # 获取原始内容
            with open(temp_file, 'r') as f:
                original_content = f.read()

            # 修复文件
            fix_controller_file(temp_file)

            # 验证内容没有变化
            with open(temp_file, 'r') as f:
                new_content = f.read()

            assert original_content == new_content

        finally:
            # 清理临时文件
            os.unlink(temp_file)

    def test_fix_controller_file_multiple_occurrences(self):
        """测试文件中有多个需要修复的地方"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""def test_function1():
    return 404

def test_function2():
    return 404

def test_function3():
    return "normal"
""")
            temp_file = f.name

        try:
            # 修复文件
            fix_controller_file(temp_file)

            # 验证修复结果
            with open(temp_file, 'r') as f:
                content = f.read()

            # 验证所有404都被替换
            assert content.count("return render_template('error-404.html'), 404") == 2
            assert "return 404" not in content

        finally:
            # 清理临时文件
            os.unlink(temp_file)

    @patch('builtins.print')
    @patch('os.path.exists')
    @patch('woniunote.fix_todo.fix_controller_file')
    def test_main_function_execution(self, mock_fix, mock_exists, mock_print):
        """测试main函数执行流程"""
        mock_exists.return_value = True

        # 执行main函数
        main()

        # 验证函数调用
        mock_print.assert_called()
        mock_fix.assert_called()

        # 验证至少修复了两个文件
        assert mock_fix.call_count >= 2

    @patch('builtins.print')
    @patch('os.path.exists')
    def test_main_function_missing_files(self, mock_exists, mock_print):
        """测试main函数处理缺失文件的情况"""
        mock_exists.return_value = False

        # 执行main函数
        main()

        # 验证警告消息
        mock_print.assert_called()
        print_calls = [str(call) for call in mock_print.call_args_list]
        warning_found = any("警告" in call or "未找到文件" in call for call in print_calls)
        assert warning_found

    def test_fix_controller_file_encoding(self):
        """测试文件编码处理"""
        # 创建包含中文的临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', encoding='utf-8', delete=False) as f:
            f.write("""# -*- coding: utf-8 -*-
def test_function():
    return 404  # 测试404错误
    return "正常响应"
""")
            temp_file = f.name

        try:
            # 修复文件
            fix_controller_file(temp_file)

            # 验证修复结果和编码
            with open(temp_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 验证修复成功且中文内容保留
            assert "return render_template('error-404.html'), 404" in content
            assert "测试404错误" in content
            assert "正常响应" in content

        finally:
            # 清理临时文件
            os.unlink(temp_file)
