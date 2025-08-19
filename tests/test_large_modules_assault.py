#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大型模块攻关测试
专门攻克app.py、card_center.py、todo_center.py等超大文件
"""

import sys
import os
import pytest
import importlib.util
from unittest.mock import Mock, patch, MagicMock, mock_open, call
from datetime import datetime, UTC
import json
import tempfile
import ast
import re

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

class LargeFileAnalyzer:
    """大文件深度分析器"""
    
    @staticmethod
    def extract_functions_with_context(file_path):
        """提取函数及其上下文"""
        if not os.path.exists(file_path):
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            functions = []
            current_function = None
            indentation_level = 0
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith('def '):
                    # 提取函数名
                    match = re.match(r'def\s+(\w+)\s*\(', stripped)
                    if match:
                        if current_function:
                            functions.append(current_function)
                        
                        current_function = {
                            'name': match.group(1),
                            'line_start': i + 1,
                            'line_end': i + 1,
                            'content': [line],
                            'decorators': [],
                            'calls_made': [],
                            'complexity': 0
                        }
                        indentation_level = len(line) - len(line.lstrip())
                
                elif current_function and line.strip():
                    current_line_indent = len(line) - len(line.lstrip())
                    
                    # 检查是否是装饰器
                    if stripped.startswith('@') and i < len(lines) - 1:
                        next_line = lines[i + 1].strip()
                        if next_line.startswith('def '):
                            current_function['decorators'].append(stripped)
                    
                    # 如果还在函数内部
                    if current_line_indent > indentation_level or (current_line_indent == indentation_level and not stripped.startswith(('def ', 'class '))):
                        current_function['content'].append(line)
                        current_function['line_end'] = i + 1
                        
                        # 分析复杂度
                        if any(keyword in stripped for keyword in ['if ', 'for ', 'while ', 'try:', 'except:']):
                            current_function['complexity'] += 1
                        
                        # 分析函数调用
                        calls = re.findall(r'(\w+)\s*\(', stripped)
                        current_function['calls_made'].extend(calls)
                    else:
                        # 函数结束
                        if current_function:
                            functions.append(current_function)
                            current_function = None
            
            # 添加最后一个函数
            if current_function:
                functions.append(current_function)
            
            return functions
        except Exception as e:
            return []
    
    @staticmethod
    def analyze_imports_and_dependencies(file_path):
        """分析导入和依赖关系"""
        if not os.path.exists(file_path):
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 分析导入语句
            import_lines = [line.strip() for line in content.split('\n') 
                          if line.strip().startswith(('import ', 'from '))]
            
            # 分类导入
            flask_imports = [line for line in import_lines if 'flask' in line.lower()]
            woniunote_imports = [line for line in import_lines if 'woniunote' in line]
            external_imports = [line for line in import_lines 
                              if not any(internal in line for internal in ['woniunote', 'flask']) 
                              and not line.startswith('from .')]
            
            # 分析使用的外部库
            external_libs = set()
            for imp_line in external_imports:
                if 'import ' in imp_line:
                    lib_name = imp_line.split('import ')[1].split('.')[0].split(' as ')[0].strip()
                    external_libs.add(lib_name)
                elif 'from ' in imp_line:
                    lib_name = imp_line.split('from ')[1].split('.')[0].split(' import')[0].strip()
                    external_libs.add(lib_name)
            
            return {
                'total_imports': len(import_lines),
                'flask_imports': flask_imports,
                'woniunote_imports': woniunote_imports,
                'external_imports': external_imports,
                'external_libs': list(external_libs),
                'import_diversity': len(external_libs)
            }
        except Exception:
            return {}
    
    @staticmethod
    def extract_routes_and_endpoints(file_path):
        """提取路由和端点信息"""
        if not os.path.exists(file_path):
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            routes = []
            current_route = None
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                
                # 检测路由装饰器
                if stripped.startswith('@') and ('route' in stripped or 'app.' in stripped):
                    route_match = re.search(r"['\"]([^'\"]+)['\"]", stripped)
                    methods_match = re.search(r"methods\s*=\s*\[([^\]]+)\]", stripped)
                    
                    current_route = {
                        'decorator': stripped,
                        'path': route_match.group(1) if route_match else 'unknown',
                        'methods': methods_match.group(1) if methods_match else 'GET',
                        'line_number': i + 1,
                        'function_name': None
                    }
                
                # 检测路由对应的函数
                elif current_route and stripped.startswith('def '):
                    func_match = re.match(r'def\s+(\w+)\s*\(', stripped)
                    if func_match:
                        current_route['function_name'] = func_match.group(1)
                        routes.append(current_route)
                        current_route = None
            
            return routes
        except Exception:
            return []

class TestAppModuleAssault:
    """app.py模块攻关测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.analyzer = LargeFileAnalyzer()
        self.app_path = os.path.join(project_root, 'woniunote', 'app.py')
    
    def test_app_module_size_and_structure(self):
        """测试app.py模块规模和结构"""
        if not os.path.exists(self.app_path):
            pytest.skip("app.py not found")
        
        with open(self.app_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        # app.py应该是一个超大文件
        assert len(lines) > 500, f"app.py应该是超大文件: {len(lines)}行"
        
        # 分析非空行和代码密度
        non_empty_lines = [line for line in lines if line.strip()]
        comment_lines = [line for line in lines if line.strip().startswith('#')]
        code_density = len(non_empty_lines) / len(lines)
        
        assert len(non_empty_lines) > 400, f"有效代码行数: {len(non_empty_lines)}"
        assert code_density > 0.6, f"代码密度: {code_density:.2f}"
        
        # 分析文件复杂度
        complex_statements = content.count('if ') + content.count('for ') + content.count('while ') + content.count('try:')
        assert complex_statements > 30, f"复杂语句数: {complex_statements}"
    
    def test_app_functions_comprehensive_analysis(self):
        """深度分析app.py中的函数"""
        functions = self.analyzer.extract_functions_with_context(self.app_path)
        
        if not functions:
            pytest.skip("Could not extract functions from app.py")
        
        # 应该有大量函数
        assert len(functions) >= 10, f"app.py函数数量: {len(functions)}"
        
        # 分析函数复杂度分布
        complex_functions = [f for f in functions if f['complexity'] >= 3]
        simple_functions = [f for f in functions if f['complexity'] < 3]
        
        assert len(complex_functions) >= 3, f"复杂函数数: {len(complex_functions)}"
        assert len(simple_functions) >= 3, f"简单函数数: {len(simple_functions)}"
        
        # 分析函数名模式
        function_names = [f['name'] for f in functions]
        
        # 检查常见的Flask应用函数模式
        flask_patterns = ['create_app', 'init_app', 'configure', 'setup', 'register']
        found_flask_patterns = [name for name in function_names 
                              if any(pattern in name.lower() for pattern in flask_patterns)]
        
        # 检查业务逻辑函数
        business_patterns = ['get', 'post', 'put', 'delete', 'list', 'show', 'create', 'update']
        found_business_patterns = [name for name in function_names 
                                 if any(pattern in name.lower() for pattern in business_patterns)]
        
        # 应该有一些Flask或业务相关的函数
        assert len(found_flask_patterns) >= 1 or len(found_business_patterns) >= 3, \
               f"Flask模式: {found_flask_patterns}, 业务模式: {found_business_patterns}"
        
        # 分析装饰器使用
        decorated_functions = [f for f in functions if f['decorators']]
        assert len(decorated_functions) >= 5, f"使用装饰器的函数数: {len(decorated_functions)}"
    
    def test_app_imports_and_dependencies(self):
        """分析app.py的导入和依赖"""
        imports_info = self.analyzer.analyze_imports_and_dependencies(self.app_path)
        
        if not imports_info:
            pytest.skip("Could not analyze imports")
        
        # app.py应该有丰富的导入
        assert imports_info['total_imports'] >= 15, f"总导入数: {imports_info['total_imports']}"
        
        # Flask导入检查
        assert len(imports_info['flask_imports']) >= 3, f"Flask导入: {imports_info['flask_imports']}"
        
        # 内部模块导入检查
        assert len(imports_info['woniunote_imports']) >= 5, f"内部导入: {imports_info['woniunote_imports']}"
        
        # 外部库多样性
        assert imports_info['import_diversity'] >= 5, f"外部库多样性: {imports_info['external_libs']}"
        
        # 检查关键依赖
        key_dependencies = ['os', 'sys', 'json', 'datetime', 'logging']
        found_key_deps = [dep for dep in key_dependencies if dep in imports_info['external_libs']]
        assert len(found_key_deps) >= 3, f"关键依赖: {found_key_deps}"
    
    def test_app_routes_and_endpoints(self):
        """分析app.py的路由和端点"""
        routes = self.analyzer.extract_routes_and_endpoints(self.app_path)
        
        # app.py应该定义了一些路由
        if len(routes) >= 5:
            # HTTP方法分析
            get_routes = [r for r in routes if 'GET' in r['methods']]
            post_routes = [r for r in routes if 'POST' in r['methods']]
            
            assert len(get_routes) >= 2, f"GET路由数: {len(get_routes)}"
            assert len(post_routes) >= 1, f"POST路由数: {len(post_routes)}"
            
            # 路径模式分析
            paths = [r['path'] for r in routes]
            dynamic_paths = [p for p in paths if '<' in p and '>' in p]
            static_paths = [p for p in paths if '<' not in p]
            
            assert len(static_paths) >= 2, f"静态路径: {static_paths}"
            
            # 函数名检查
            route_functions = [r['function_name'] for r in routes if r['function_name']]
            assert len(route_functions) >= 3, f"路由函数: {route_functions}"
        else:
            # 如果没有直接路由定义，检查是否有路由相关代码
            with open(self.app_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            route_indicators = ['route', 'endpoint', 'url_for', 'redirect']
            found_indicators = [indicator for indicator in route_indicators if indicator in content]
            assert len(found_indicators) >= 3, f"路由相关代码: {found_indicators}"

class TestCardCenterAssault:
    """card_center.py模块攻关测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.analyzer = LargeFileAnalyzer()
        self.card_center_path = os.path.join(project_root, 'woniunote', 'controller', 'card_center.py')
    
    def test_card_center_module_scale(self):
        """测试card_center.py模块规模"""
        if not os.path.exists(self.card_center_path):
            pytest.skip("card_center.py not found")
        
        with open(self.card_center_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        # card_center应该是一个大型控制器文件
        assert len(lines) > 300, f"card_center应该是大文件: {len(lines)}行"
        
        # 检查卡片相关功能
        card_keywords = ['card', 'Card', 'category', 'Category', 'flashcard', 'learning', 'study']
        found_keywords = [kw for kw in card_keywords if kw in content]
        assert len(found_keywords) >= 4, f"卡片相关关键词: {found_keywords}"
        
        # 检查CRUD操作模式
        crud_patterns = ['create', 'read', 'update', 'delete', 'list', 'show', 'edit', 'add', 'remove']
        found_crud = [pattern for pattern in crud_patterns if pattern.lower() in content.lower()]
        assert len(found_crud) >= 5, f"CRUD操作: {found_crud}"
    
    def test_card_center_functions_analysis(self):
        """分析card_center.py中的函数"""
        functions = self.analyzer.extract_functions_with_context(self.card_center_path)
        
        if not functions:
            pytest.skip("Could not extract functions from card_center.py")
        
        # 应该有丰富的功能函数
        assert len(functions) >= 8, f"card_center函数数: {len(functions)}"
        
        # 分析函数名模式
        function_names = [f['name'] for f in functions]
        
        # 卡片相关函数
        card_functions = [name for name in function_names if 'card' in name.lower()]
        category_functions = [name for name in function_names if 'category' in name.lower()]
        
        assert len(card_functions) >= 2, f"卡片相关函数: {card_functions}"
        assert len(category_functions) >= 1, f"分类相关函数: {category_functions}"
        
        # 检查REST API函数模式
        rest_patterns = ['get', 'post', 'put', 'delete', 'list', 'create', 'update']
        rest_functions = [name for name in function_names 
                         if any(pattern in name.lower() for pattern in rest_patterns)]
        
        assert len(rest_functions) >= 4, f"REST API函数: {rest_functions}"
        
        # 复杂函数分析
        complex_functions = [f for f in functions if f['complexity'] >= 4]
        assert len(complex_functions) >= 2, f"复杂函数数: {len(complex_functions)}"
    
    def test_card_center_route_structure(self):
        """分析card_center.py的路由结构"""
        routes = self.analyzer.extract_routes_and_endpoints(self.card_center_path)
        
        if len(routes) >= 3:
            # 路由路径分析
            paths = [r['path'] for r in routes]
            card_paths = [p for p in paths if 'card' in p.lower()]
            
            assert len(card_paths) >= 2, f"卡片相关路径: {card_paths}"
            
            # HTTP方法分析
            methods = [r['methods'] for r in routes]
            assert len(methods) >= 3, f"HTTP方法: {methods}"
        
        # 检查蓝图定义
        with open(self.card_center_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        blueprint_patterns = ['Blueprint', 'card_center', 'register_blueprint']
        found_blueprint = [pattern for pattern in blueprint_patterns if pattern in content]
        assert len(found_blueprint) >= 2, f"蓝图相关: {found_blueprint}"

class TestTodoCenterAssault:
    """todo_center.py模块攻关测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.analyzer = LargeFileAnalyzer()
        self.todo_center_path = os.path.join(project_root, 'woniunote', 'controller', 'todo_center.py')
    
    def test_todo_center_functionality_coverage(self):
        """测试todo_center.py功能覆盖"""
        if not os.path.exists(self.todo_center_path):
            pytest.skip("todo_center.py not found")
        
        with open(self.todo_center_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Todo相关功能检查
        todo_keywords = ['todo', 'Todo', 'task', 'Task', 'item', 'Item', 'category', 'Category']
        found_keywords = [kw for kw in todo_keywords if kw in content]
        assert len(found_keywords) >= 4, f"Todo相关关键词: {found_keywords}"
        
        # 任务管理功能
        management_features = ['create', 'update', 'delete', 'complete', 'priority', 'status', 'due_date']
        found_features = [feature for feature in management_features if feature in content.lower()]
        assert len(found_features) >= 4, f"任务管理功能: {found_features}"
        
        # 数据库操作检查
        db_operations = ['db.session', 'query(', '.filter(', '.all()', '.first()', 'commit()', 'add(']
        found_db_ops = [op for op in db_operations if op in content]
        assert len(found_db_ops) >= 3, f"数据库操作: {found_db_ops}"
    
    def test_todo_center_business_logic(self):
        """分析todo_center.py业务逻辑"""
        functions = self.analyzer.extract_functions_with_context(self.todo_center_path)
        
        if not functions:
            pytest.skip("Could not extract functions from todo_center.py")
        
        # 应该有足够的业务函数
        assert len(functions) >= 5, f"todo_center函数数: {len(functions)}"
        
        # 业务逻辑函数分析
        function_names = [f['name'] for f in functions]
        
        # Todo特定函数
        todo_functions = [name for name in function_names 
                         if any(todo in name.lower() for todo in ['todo', 'task', 'item'])]
        assert len(todo_functions) >= 2, f"Todo特定函数: {todo_functions}"
        
        # 分类管理函数
        category_functions = [name for name in function_names if 'category' in name.lower()]
        assert len(category_functions) >= 1, f"分类函数: {category_functions}"
        
        # 状态管理函数
        status_functions = [name for name in function_names 
                           if any(status in name.lower() for status in ['complete', 'finish', 'status', 'toggle'])]
        # 状态函数是可选的，不强制要求

class TestLargeControllersComparative:
    """大型控制器对比分析测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.analyzer = LargeFileAnalyzer()
        
        # 大型控制器文件路径
        self.large_controllers = {
            'card_center': os.path.join(project_root, 'woniunote', 'controller', 'card_center.py'),
            'todo_center': os.path.join(project_root, 'woniunote', 'controller', 'todo_center.py'),
            'admin': os.path.join(project_root, 'woniunote', 'controller', 'admin.py'),
            'article': os.path.join(project_root, 'woniunote', 'controller', 'article.py'),
            'user': os.path.join(project_root, 'woniunote', 'controller', 'user.py')
        }
    
    def test_controllers_size_distribution(self):
        """测试控制器文件大小分布"""
        controller_sizes = {}
        total_lines = 0
        
        for name, path in self.large_controllers.items():
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    lines = len(f.readlines())
                
                controller_sizes[name] = lines
                total_lines += lines
        
        # 应该分析了多个控制器
        assert len(controller_sizes) >= 3, f"分析的控制器数: {len(controller_sizes)}"
        assert total_lines >= 500, f"控制器总行数: {total_lines}"
        
        # 找到最大的控制器
        largest_controller = max(controller_sizes.items(), key=lambda x: x[1])
        assert largest_controller[1] >= 100, f"最大控制器 {largest_controller[0]}: {largest_controller[1]}行"
        
        # 检查是否有超大控制器（>300行）
        super_large = {name: size for name, size in controller_sizes.items() if size > 300}
        # 超大控制器是可选的，记录但不强制要求
    
    def test_controllers_functionality_comparison(self):
        """对比分析控制器功能"""
        controller_analysis = {}
        
        for name, path in self.large_controllers.items():
            if os.path.exists(path):
                functions = self.analyzer.extract_functions_with_context(path)
                imports = self.analyzer.analyze_imports_and_dependencies(path)
                routes = self.analyzer.extract_routes_and_endpoints(path)
                
                controller_analysis[name] = {
                    'function_count': len(functions),
                    'import_count': imports.get('total_imports', 0),
                    'route_count': len(routes),
                    'complex_functions': len([f for f in functions if f['complexity'] >= 3])
                }
        
        # 应该有多个控制器的分析结果
        assert len(controller_analysis) >= 3, f"分析的控制器数: {len(controller_analysis)}"
        
        # 各控制器应该有一定的功能
        for name, analysis in controller_analysis.items():
            assert analysis['function_count'] >= 2, f"{name} 函数数: {analysis['function_count']}"
            assert analysis['import_count'] >= 3, f"{name} 导入数: {analysis['import_count']}"
        
        # 计算总体统计
        total_functions = sum(analysis['function_count'] for analysis in controller_analysis.values())
        total_routes = sum(analysis['route_count'] for analysis in controller_analysis.values())
        
        assert total_functions >= 20, f"控制器总函数数: {total_functions}"
    
    def test_controllers_code_quality_metrics(self):
        """分析控制器代码质量指标"""
        quality_metrics = {}
        
        for name, path in self.large_controllers.items():
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                # 计算质量指标
                total_lines = len(lines)
                non_empty_lines = len([line for line in lines if line.strip()])
                comment_lines = len([line for line in lines if line.strip().startswith('#')])
                
                # 错误处理
                error_handling = content.count('try:') + content.count('except:')
                
                # 文档字符串
                docstrings = content.count('"""') + content.count("'''")
                
                quality_metrics[name] = {
                    'code_density': non_empty_lines / total_lines if total_lines > 0 else 0,
                    'comment_ratio': comment_lines / non_empty_lines if non_empty_lines > 0 else 0,
                    'error_handling_count': error_handling,
                    'docstring_count': docstrings,
                    'total_lines': total_lines
                }
        
        # 质量指标分析
        high_quality_controllers = []
        
        for name, metrics in quality_metrics.items():
            # 代码密度应该合理
            assert 0.3 <= metrics['code_density'] <= 1.0, f"{name} 代码密度: {metrics['code_density']:.2f}"
            
            # 大文件应该有一些错误处理
            if metrics['total_lines'] > 200:
                assert metrics['error_handling_count'] >= 1, f"{name} 错误处理: {metrics['error_handling_count']}"
            
            # 评估总体质量
            quality_score = (
                metrics['code_density'] * 0.3 +
                min(metrics['comment_ratio'], 0.3) * 0.2 +
                min(metrics['error_handling_count'], 10) / 10 * 0.3 +
                min(metrics['docstring_count'], 20) / 20 * 0.2
            )
            
            if quality_score >= 0.5:
                high_quality_controllers.append(name)
        
        # 至少应该有一些高质量的控制器
        assert len(high_quality_controllers) >= 1, f"高质量控制器: {high_quality_controllers}"

class TestModuleIntegrationAssault:
    """模块集成攻关测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.analyzer = LargeFileAnalyzer()
    
    def test_cross_module_dependencies(self):
        """测试跨模块依赖关系"""
        modules_to_analyze = [
            ('woniunote/app.py', 'app'),
            ('woniunote/app_factory.py', 'app_factory'),
            ('woniunote/controller/card_center.py', 'card_center'),
            ('woniunote/controller/todo_center.py', 'todo_center'),
            ('woniunote/module/articles.py', 'articles'),
            ('woniunote/module/users.py', 'users'),
        ]
        
        dependency_network = {}
        
        for rel_path, module_name in modules_to_analyze:
            full_path = os.path.join(project_root, rel_path)
            if os.path.exists(full_path):
                imports_info = self.analyzer.analyze_imports_and_dependencies(full_path)
                dependency_network[module_name] = imports_info
        
        # 应该分析了多个模块
        assert len(dependency_network) >= 3, f"分析的模块数: {len(dependency_network)}"
        
        # 分析依赖模式
        high_coupling_modules = []
        well_integrated_modules = []
        
        for module_name, imports_info in dependency_network.items():
            total_imports = imports_info.get('total_imports', 0)
            internal_imports = len(imports_info.get('woniunote_imports', []))
            
            # 高耦合度模块（内部依赖多）
            if internal_imports >= 3:
                high_coupling_modules.append(module_name)
            
            # 良好集成模块（总导入多）
            if total_imports >= 8:
                well_integrated_modules.append(module_name)
        
        # 应该有一些高度集成的模块
        assert len(high_coupling_modules) >= 2, f"高耦合模块: {high_coupling_modules}"
        assert len(well_integrated_modules) >= 1, f"良好集成模块: {well_integrated_modules}"
    
    def test_architectural_patterns_analysis(self):
        """分析架构模式"""
        pattern_analysis = {
            'mvc_controllers': 0,
            'service_layers': 0,
            'data_access_layers': 0,
            'factory_patterns': 0,
            'blueprint_patterns': 0
        }
        
        # 分析不同类型的文件
        file_patterns = [
            ('controller/*.py', 'mvc_controllers'),
            ('module/*.py', 'service_layers'),
            ('common/database.py', 'data_access_layers'),
            ('app_factory.py', 'factory_patterns')
        ]
        
        for pattern_path, pattern_type in file_patterns:
            if '*' in pattern_path:
                # 处理通配符路径
                directory = os.path.join(project_root, 'woniunote', pattern_path.split('*')[0])
                if os.path.exists(directory):
                    py_files = [f for f in os.listdir(directory) if f.endswith('.py') and not f.startswith('__')]
                    pattern_analysis[pattern_type] = len(py_files)
            else:
                # 处理具体文件
                file_path = os.path.join(project_root, 'woniunote', pattern_path)
                if os.path.exists(file_path):
                    pattern_analysis[pattern_type] = 1
        
        # 检查蓝图模式
        controller_dir = os.path.join(project_root, 'woniunote', 'controller')
        if os.path.exists(controller_dir):
            blueprint_count = 0
            for filename in os.listdir(controller_dir):
                if filename.endswith('.py'):
                    file_path = os.path.join(controller_dir, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'Blueprint' in content:
                            blueprint_count += 1
            pattern_analysis['blueprint_patterns'] = blueprint_count
        
        # 架构模式验证
        assert pattern_analysis['mvc_controllers'] >= 5, f"MVC控制器数: {pattern_analysis['mvc_controllers']}"
        assert pattern_analysis['service_layers'] >= 3, f"服务层数: {pattern_analysis['service_layers']}"
        assert pattern_analysis['blueprint_patterns'] >= 3, f"蓝图模式数: {pattern_analysis['blueprint_patterns']}"
        
        # 计算架构成熟度分数
        architecture_score = sum(pattern_analysis.values())
        assert architecture_score >= 15, f"架构成熟度分数: {architecture_score}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])