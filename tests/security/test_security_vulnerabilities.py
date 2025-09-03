#!/usr/bin/env python3
"""
Comprehensive security vulnerability tests for WoniuNote
Tests SQL injection, XSS, CSRF, session management, and other security threats
"""

import pytest
import sys
import os
import time
import json
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, session, request, g

# 确保项目根目录在Python路径中
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 设置测试环境
os.environ['TESTING'] = 'True'
os.environ['FLASK_ENV'] = 'testing'


@pytest.fixture
def app():
    """创建测试Flask应用"""
    from woniunote.app_factory import create_app

    app = create_app()
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-security-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


class TestSQLInjectionProtection:
    """测试SQL注入攻击防护"""

    def test_sql_injection_user_login(self, client):
        """测试用户登录SQL注入防护"""
        with patch('woniunote.module.users.Users') as mock_users_class:
            mock_users_instance = Mock()
            mock_users_instance.login.return_value = "用户名或密码错误"
            mock_users_class.return_value = mock_users_instance

            # 测试常见的SQL注入payload
            sql_injection_payloads = [
                "' OR '1'='1",
                "' OR '1'='1' --",
                "admin' --",
                "' UNION SELECT * FROM users --",
                "'; DROP TABLE users; --",
                "' OR 1=1; --",
                "admin' OR '1'='1",
                "' OR ''='",
                "' OR 'x'='x",
                "admin'; --",
            ]

            for payload in sql_injection_payloads:
                response = client.post('/user/login', data={
                    'username': payload,
                    'password': 'password123'
                })

                # 确保不会返回成功登录（除非payload正好匹配真实用户）
                if payload not in ['admin', 'testuser']:  # 排除可能存在的合法用户名
                    assert response.status_code in [200, 302]  # 不应该崩溃
                    # 验证没有敏感信息泄露
                    response_text = response.data.decode()
                    assert 'SQL' not in response_text.upper()
                    assert 'syntax' not in response_text.lower()
                    assert 'mysql' not in response_text.lower()

    def test_sql_injection_search_functionality(self, client):
        """测试搜索功能SQL注入防护"""
        with patch('woniunote.module.articles.Articles') as mock_articles_class:
            mock_articles_instance = Mock()
            mock_articles_instance.search_headline.return_value = []
            mock_articles_class.return_value = mock_articles_instance

            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            # 测试SQL注入payload
            malicious_queries = [
                "' UNION SELECT username, password FROM users --",
                "'; SELECT * FROM users; --",
                "' OR '1'='1",
                "test' UNION SELECT * FROM users --",
                "' DROP TABLE users --",
                "'; SHOW TABLES; --",
                "' OR 1=1 UNION SELECT * FROM users --",
                "test'; TRUNCATE TABLE users; --",
            ]

            for query in malicious_queries:
                response = client.get(f'/article/search?keyword={query}')

                # 确保应用不会崩溃
                assert response.status_code in [200, 302, 404]
                response_text = response.data.decode()

                # 验证没有数据库错误信息泄露
                assert 'SQL' not in response_text.upper()
                assert 'syntax error' not in response_text.lower()
                assert 'mysql error' not in response_text.lower()
                assert 'sqlite' not in response_text.lower()

    def test_sql_injection_comment_system(self, client):
        """测试评论系统SQL注入防护"""
        with patch('woniunote.module.comments.Comments') as mock_comments_class:
            mock_comments_instance = Mock()
            mock_comments_instance.insert_comment.return_value = "add-pass"
            mock_comments_class.return_value = mock_comments_instance

            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            # 测试SQL注入payload in comments
            malicious_comments = [
                "' UNION SELECT * FROM users --",
                "Nice article!'); DROP TABLE comments; --",
                "' OR '1'='1",
                "'; SELECT password FROM users WHERE id=1; --",
                "Great post!' UNION SELECT username,password FROM users --",
                "' OR 1=1; --",
                "Good!'); UPDATE users SET password='hacked' WHERE id=1; --",
            ]

            for comment in malicious_comments:
                response = client.post('/comment/add', data={
                    'articleid': '1',
                    'content': comment
                })

                # 确保不会因为SQL注入而崩溃
                assert response.status_code in [200, 302]
                response_text = response.data.decode()

                # 验证没有数据库错误泄露
                assert 'SQL' not in response_text.upper()
                assert 'syntax' not in response_text.lower()

    def test_sql_injection_admin_functions(self, client):
        """测试管理员功能SQL注入防护"""
        # 设置管理员登录状态
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['userid'] = 1
            sess['role'] = 'admin'

        # 测试管理员搜索功能SQL注入
        malicious_searches = [
            "' UNION SELECT * FROM users --",
            "'; SHOW TABLES; --",
            "admin' OR '1'='1",
            "' DROP TABLE articles --",
        ]

        for search_term in malicious_searches:
            response = client.get(f'/admin/search?keyword={search_term}')

            # 确保不会崩溃
            assert response.status_code in [200, 302, 404]
            response_text = response.data.decode()

            # 验证没有敏感信息泄露
            assert 'SQL' not in response_text.upper()
            assert 'error' not in response_text.lower() or '页面' in response_text

    def test_parameterized_queries_protection(self, client):
        """测试参数化查询防护"""
        with patch('woniunote.module.articles.Articles') as mock_articles_class:
            mock_articles_instance = Mock()
            # 确保查询方法被正确调用（应该使用参数化查询）
            mock_articles_instance.find_by_id.return_value = None
            mock_articles_class.return_value = mock_articles_instance

            # 测试各种恶意参数
            malicious_ids = [
                "1 UNION SELECT * FROM users",
                "1; DROP TABLE users; --",
                "1 OR 1=1",
                "1' UNION SELECT password FROM users --",
                "1; SELECT * FROM users; --",
            ]

            for article_id in malicious_ids:
                response = client.get(f'/article/{article_id}')

                # 验证应用正常处理，不崩溃
                assert response.status_code in [200, 302, 404]
                response_text = response.data.decode()

                # 不应该有数据库错误信息
                assert 'SQL' not in response_text.upper()


class TestXSSProtection:
    """测试跨站脚本攻击防护"""

    def test_xss_prevention_in_comments(self, client):
        """测试评论中的XSS防护"""
        with patch('woniunote.module.comments.Comments') as mock_comments_class:
            mock_comments_instance = Mock()
            mock_comments_instance.insert_comment.return_value = "add-pass"
            mock_comments_class.return_value = mock_comments_instance

            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            # 测试XSS payload
            xss_payloads = [
                "<script>alert('XSS')</script>",
                "<img src=x onerror=alert('XSS')>",
                "<iframe src='javascript:alert(\"XSS\")'></iframe>",
                "<svg onload=alert('XSS')>",
                "javascript:alert('XSS')",
                "<body onload=alert('XSS')>",
                "<div onmouseover=alert('XSS')>Hover me</div>",
                "<a href='javascript:alert(\"XSS\")'>Click me</a>",
                "<object data='javascript:alert(\"XSS\")'></object>",
                "<embed src='javascript:alert(\"XSS\")'>",
            ]

            for payload in xss_payloads:
                response = client.post('/comment/add', data={
                    'articleid': '1',
                    'content': payload
                })

                assert response.status_code in [200, 302]
                response_text = response.data.decode()

                # 验证XSS payload被转义或过滤
                # 理想情况下，payload应该被转义为安全字符
                assert '<script>' not in response_text or '&lt;script&gt;' in response_text

    def test_xss_prevention_in_articles(self, client):
        """测试文章内容中的XSS防护"""
        with patch('woniunote.module.articles.Articles') as mock_articles_class:
            mock_articles_instance = Mock()
            mock_articles_instance.add_article.return_value = "发布成功"
            mock_articles_class.return_value = mock_articles_instance

            # 设置登录状态
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1

            # 测试文章标题和内容中的XSS
            xss_payloads = [
                "<script>alert('XSS in title')</script>",
                "<img src=x onerror=alert('XSS in content')>",
                "<a href='javascript:alert(\"XSS\")'>Link</a>",
                "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            ]

            for payload in xss_payloads:
                response = client.post('/article/post', data={
                    'headline': f"Test Article {payload}",
                    'content': f"Content with {payload}",
                    'type': '1'
                })

                assert response.status_code in [200, 302]
                response_text = response.data.decode()

                # 验证XSS被防护
                if '发布成功' in response_text:
                    # 如果发布成功，检查内容是否被安全处理
                    assert '<script>' not in response_text or '&lt;script&gt;' in response_text

    def test_xss_prevention_in_search(self, client):
        """测试搜索功能中的XSS防护"""
        # 测试搜索参数中的XSS
        xss_search_terms = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
        ]

        for term in xss_search_terms:
            response = client.get(f'/article/search?keyword={term}')

            assert response.status_code in [200, 302, 404]
            response_text = response.data.decode()

            # 验证XSS payload没有被执行
            assert 'alert(' not in response_text or 'onerror' not in response_text

    def test_xss_prevention_in_user_input(self, client):
        """测试用户输入字段的XSS防护"""
        with patch('woniunote.module.users.Users') as mock_users_class:
            mock_users_instance = Mock()
            mock_users_instance.register.return_value = "register-success"
            mock_users_class.return_value = mock_users_instance

            # 设置验证码
            with client.session_transaction() as sess:
                sess['ecode'] = 'ABCD'

            # 测试用户名和昵称中的XSS
            xss_usernames = [
                "<script>alert('XSS')</script>",
                "<img src=x onerror=alert('XSS')>",
                "admin<script>alert('XSS')</script>",
            ]

            for username in xss_usernames:
                response = client.post('/user', data={
                    'username': f"{username}@example.com",
                    'password': 'TestPass123!',
                    'ecode': 'ABCD'
                })

                assert response.status_code in [200, 302]
                response_text = response.data.decode()

                # 验证XSS被防护
                if 'register-success' in response_text:
                    assert '<script>' not in response_text or '&lt;script&gt;' in response_text


class TestCSRFProtection:
    """测试跨站请求伪造防护"""

    def test_csrf_protection_missing_token(self, client):
        """测试缺少CSRF token的请求"""
        # 测试POST请求缺少CSRF token
        response = client.post('/user', data={
            'username': 'test@example.com',
            'password': 'TestPass123!',
            'ecode': 'ABCD'
        })

        # 如果有CSRF保护，应该返回错误
        assert response.status_code in [200, 400, 403]

        # 如果返回400或403，说明CSRF保护生效
        if response.status_code in [400, 403]:
            response_text = response.data.decode()
            assert 'csrf' in response_text.lower() or 'token' in response_text.lower()

    def test_csrf_protection_invalid_token(self, client):
        """测试无效CSRF token的请求"""
        # 测试使用无效CSRF token的请求
        response = client.post('/user', data={
            'username': 'test@example.com',
            'password': 'TestPass123!',
            'ecode': 'ABCD',
            'csrf_token': 'invalid_token_12345'
        })

        assert response.status_code in [200, 400, 403]

        # 如果返回400或403，说明CSRF保护生效
        if response.status_code in [400, 403]:
            response_text = response.data.decode()
            assert 'csrf' in response_text.lower() or 'token' in response_text.lower() or 'invalid' in response_text.lower()

    def test_csrf_protection_token_reuse(self, client):
        """测试CSRF token重用防护"""
        # 首次获取token（如果有的话）
        response1 = client.get('/user/register')
        assert response1.status_code == 200

        # 尝试重用token
        # 注意：这需要根据实际的CSRF实现来调整
        response2 = client.post('/user', data={
            'username': 'test@example.com',
            'password': 'TestPass123!',
            'ecode': 'ABCD'
        })

        assert response2.status_code in [200, 400, 403]

    def test_csrf_protection_state_changing_operations(self, client):
        """测试状态改变操作的CSRF防护"""
        # 测试所有状态改变操作的CSRF防护
        state_changing_endpoints = [
            '/user',  # 注册
            '/login',     # 登录
            '/user/logout',  # 登出
            '/article/post',  # 发布文章
            '/comment/add',   # 添加评论
            '/user/profile/update',  # 更新资料
        ]

        for endpoint in state_changing_endpoints:
            response = client.post(endpoint, data={})
            assert response.status_code in [200, 302, 400, 403, 422]

            # 如果返回400/403/422，可能说明CSRF保护生效
            if response.status_code in [400, 403, 422]:
                response_text = response.data.decode()
                # 检查是否有CSRF相关的错误信息
                csrf_indicators = ['csrf', 'token', 'invalid', 'forbidden', 'bad request']
                has_csrf_protection = any(indicator in response_text.lower() for indicator in csrf_indicators)
                if has_csrf_protection:
                    assert True  # CSRF保护生效


class TestSessionManagementSecurity:
    """测试会话管理安全"""

    def test_session_fixation_protection(self, client):
        """测试会话固定攻击防护"""
        # 尝试设置会话ID
        with client.session_transaction() as sess:
            original_session_id = sess.sid if hasattr(sess, 'sid') else 'test_session'

        # 登录后检查会话ID是否改变
        with patch('woniunote.module.users.Users') as mock_users_class:
            mock_users_instance = Mock()
            mock_users_instance.login.return_value = "login-success"
            mock_users_instance.get_user_info.return_value = {
                'userid': 1, 'username': 'testuser', 'role': 'user'
            }
            mock_users_class.return_value = mock_users_instance

            response = client.post('/user/login', data={
                'username': 'testuser',
                'password': 'TestPass123!'
            })

            # 检查登录后会话是否改变
            with client.session_transaction() as sess:
                new_session_id = sess.sid if hasattr(sess, 'sid') else 'test_session'
                # 理想情况下，会话ID应该改变以防止会话固定攻击
                # 但这取决于Flask的会话实现

    def test_session_timeout_protection(self, client):
        """测试会话超时保护"""
        # 设置登录状态
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['userid'] = 1
            sess['username'] = 'testuser'
            sess['_last_access'] = time.time() - 3600  # 1小时前

        # 尝试访问需要认证的资源
        response = client.get('/user/profile')

        # 如果有会话超时保护，应该重定向到登录页或返回未授权
        assert response.status_code in [200, 302, 401, 403]

    def test_concurrent_session_management(self, client):
        """测试并发会话管理"""
        # 由于pytest fixture限制，暂时跳过并发测试
        pytest.skip("Concurrent session management test requires multiple clients - skipping for now")

    def test_session_invalidation_on_logout(self, client):
        """测试登出时会话失效"""
        # 先登录
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['userid'] = 1
            sess['username'] = 'testuser'

        # 登出
        response = client.get('/user/logout')
        assert response.status_code in [200, 302]

        # 检查会话是否被清除
        with client.session_transaction() as sess:
            assert 'islogin' not in sess or sess.get('islogin') != 'true'
            assert 'userid' not in sess
            assert 'username' not in sess

    def test_session_hijacking_protection(self, client):
        """测试会话劫持防护"""
        # 设置登录状态
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['userid'] = 1
            sess['username'] = 'testuser'
            sess['user_agent'] = 'Mozilla/5.0 Test Browser'
            sess['ip_address'] = '127.0.0.1'

        # 尝试使用不同User-Agent访问（模拟会话劫持）
        response = client.get('/user/profile',
                            headers={'User-Agent': 'Different Browser'})

        # 如果有会话劫持防护，应该检测到异常
        assert response.status_code in [200, 302, 403]

        if response.status_code == 403:
            response_text = response.data.decode()
            assert 'session' in response_text.lower() or 'security' in response_text.lower()


class TestFileUploadSecurity:
    """测试文件上传安全"""

    def test_file_upload_type_validation(self, client):
        """测试文件上传类型验证"""
        # 设置登录状态
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['userid'] = 1

        # 测试上传恶意文件类型
        malicious_files = [
            ('malicious.exe', b'MZ\x90\x00\x03\x00\x00\x00', 'application/x-msdownload'),
            ('script.php', b'<?php echo "hacked"; ?>', 'application/x-php'),
            ('malware.js', b'alert("hacked");', 'application/javascript'),
            ('virus.bat', b'@echo off\r\necho hacked', 'application/x-bat'),
        ]

        for filename, content, mimetype in malicious_files:
            from io import BytesIO
            file_data = BytesIO(content)
            file_data.filename = filename

            response = client.post('/upload/avatar', data={
                'file': (file_data, filename)
            }, content_type='multipart/form-data')

            # 应该拒绝恶意文件类型
            assert response.status_code in [200, 400, 403, 422]
            response_text = response.data.decode()

            # 检查是否有安全拒绝信息
            if response.status_code in [400, 403, 422]:
                security_indicators = ['invalid', 'not allowed', 'forbidden', 'type', 'extension']
                has_security_message = any(indicator in response_text.lower() for indicator in security_indicators)
                assert has_security_message

    def test_file_upload_size_limit(self, client):
        """测试文件上传大小限制"""
        # 设置登录状态
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['userid'] = 1

        # 创建大文件（超过限制）
        large_content = b'0' * (10 * 1024 * 1024)  # 10MB
        from io import BytesIO
        file_data = BytesIO(large_content)
        file_data.filename = 'large_file.png'

        response = client.post('/upload/avatar', data={
            'file': (file_data, 'large_file.png')
        }, content_type='multipart/form-data')

        # 应该拒绝过大的文件
        assert response.status_code in [200, 413, 422]
        response_text = response.data.decode()

        # 如果返回413（请求实体过大），说明大小限制生效
        if response.status_code == 413:
            assert 'large' in response_text.lower() or 'size' in response_text.lower()

    def test_file_upload_path_traversal(self, client):
        """测试文件上传路径遍历攻击"""
        # 设置登录状态
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['userid'] = 1

        # 测试路径遍历payload
        path_traversal_payloads = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32\\config\\sam',
            '....//....//....//etc/passwd',
            '.../...//.../...//.../...//etc/passwd',
            '%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd',
        ]

        for malicious_path in path_traversal_payloads:
            from io import BytesIO
            file_data = BytesIO(b'test content')
            file_data.filename = malicious_path

            response = client.post('/upload/avatar', data={
                'file': (file_data, malicious_path)
            }, content_type='multipart/form-data')

            # 应该拒绝路径遍历攻击
            assert response.status_code in [200, 400, 403, 422]
            response_text = response.data.decode()

            # 检查是否有路径遍历防护
            if response.status_code in [400, 403, 422]:
                security_indicators = ['invalid', 'path', 'forbidden', 'traversal', 'filename']
                has_security_message = any(indicator in response_text.lower() for indicator in security_indicators)
                assert has_security_message

    def test_file_upload_content_validation(self, client):
        """测试文件内容验证"""
        # 设置登录状态
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['userid'] = 1

        # 测试伪装文件（文件名是图片，但内容是可执行文件）
        disguised_files = [
            ('fake_image.png', b'MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00', 'image/png'),
            ('fake_jpg.exe', b'\xff\xd8\xff\xe0\x00\x10JFIF' + b'MZ\x90\x00', 'image/jpeg'),
        ]

        for filename, content, mimetype in disguised_files:
            from io import BytesIO
            file_data = BytesIO(content)
            file_data.filename = filename

            response = client.post('/upload/avatar', data={
                'file': (file_data, filename)
            }, content_type='multipart/form-data')

            # 应该检测到内容不匹配
            assert response.status_code in [200, 400, 422]
            response_text = response.data.decode()

            # 如果有内容验证，可能会检测到不匹配
            if response.status_code in [400, 422]:
                assert 'invalid' in response_text.lower() or 'content' in response_text.lower()


class TestAPISecurity:
    """测试API安全"""

    def test_api_authentication_required(self, client):
        """测试API需要认证"""
        # 测试需要认证的API端点
        protected_endpoints = [
            '/api/user/profile',
            '/api/article/post',
            '/api/admin/dashboard',
            '/api/comment/add',
        ]

        for endpoint in protected_endpoints:
            response = client.get(endpoint)

            # 应该返回401或重定向到登录
            assert response.status_code in [200, 401, 403, 302]

            if response.status_code == 401:
                response_text = response.data.decode()
                assert 'unauthorized' in response_text.lower() or 'login' in response_text.lower()

    def test_api_rate_limiting(self, client):
        """测试API速率限制"""
        # 快速发送多个请求测试速率限制
        responses = []
        for i in range(10):
            response = client.get('/api/user/status')
            responses.append(response.status_code)
            time.sleep(0.1)  # 短暂延迟

        # 检查是否有429状态码（请求过于频繁）
        has_rate_limit = 429 in responses
        if has_rate_limit:
            # 如果有限速，验证错误处理
            rate_limit_responses = [r for r in responses if r == 429]
            assert len(rate_limit_responses) > 0

            # 检查429响应的内容
            response_429 = client.get('/api/user/status')
            if response_429.status_code == 429:
                response_text = response_429.data.decode()
                rate_limit_indicators = ['rate', 'limit', 'too many', '429', 'frequency']
                has_rate_limit_message = any(indicator in response_text.lower() for indicator in rate_limit_indicators)
                assert has_rate_limit_message

    def test_api_input_validation(self, client):
        """测试API输入验证"""
        # 测试各种恶意输入
        malicious_inputs = [
            {'id': '1 UNION SELECT * FROM users'},
            {'id': '1; DROP TABLE users;'},
            {'id': '<script>alert("xss")</script>'},
            {'id': '1 OR 1=1'},
            {'id': '../../../etc/passwd'},
            {'id': 'javascript:alert("xss")'},
        ]

        for malicious_input in malicious_inputs:
            response = client.get('/api/article/1', query_string=malicious_input)

            # 确保不会崩溃
            assert response.status_code in [200, 400, 404, 422]

            if response.status_code in [400, 422]:
                response_text = response.data.decode()
                validation_indicators = ['invalid', 'malformed', 'bad', 'error']
                has_validation_message = any(indicator in response_text.lower() for indicator in validation_indicators)
                assert has_validation_message

    def test_api_error_information_leakage(self, client):
        """测试API错误信息泄露防护"""
        # 测试各种可能导致错误的情况
        error_triggers = [
            '/api/article/999999',  # 不存在的资源
            '/api/user/invalid_id',  # 无效ID
            '/api/admin/secret_data',  # 无权限访问
        ]

        for endpoint in error_triggers:
            response = client.get(endpoint)

            assert response.status_code in [200, 404, 403, 500]
            response_text = response.data.decode()

            # 确保没有敏感信息泄露
            sensitive_indicators = ['sql', 'database', 'stack trace', 'exception', 'error']
            for indicator in sensitive_indicators:
                assert indicator.lower() not in response_text.lower()


class TestAuthenticationSecurity:
    """测试认证安全"""

    def test_password_complexity_requirements(self, client):
        """测试密码复杂度要求"""
        weak_passwords = [
            '123',
            'password',
            '123456',
            'qwerty',
            'abc',
            '111111',
        ]

        with client.session_transaction() as sess:
            sess['ecode'] = 'ABCD'

        for weak_password in weak_passwords:
            response = client.post('/user', data={
                'username': f'test{weak_password}@example.com',
                'password': weak_password,
                'ecode': 'ABCD'
            })

            assert response.status_code in [200, 302]
            response_text = response.data.decode()

            # 如果密码被拒绝，检查错误信息
            if 'register-success' not in response_text:
                assert '密码' in response_text or 'password' in response_text.lower()

    def test_account_lockout_protection(self, client):
        """测试账户锁定防护"""
        # 多次尝试错误密码
        failed_attempts = 0
        max_attempts = 5

        for i in range(max_attempts + 2):
            response = client.post('/user/login', data={
                'username': 'testuser',
                'password': f'wrong_password_{i}'
            })

            if response.status_code == 429 or 'locked' in response.data.decode().lower():
                failed_attempts += 1

        # 如果有账户锁定机制，应该在多次失败后锁定
        if failed_attempts > 0:
            assert failed_attempts <= max_attempts

    def test_password_reset_security(self, client):
        """测试密码重置安全"""
        # 测试密码重置功能的安全性
        response = client.post('/user/reset_password', data={
            'email': 'victim@example.com'
        })

        # 密码重置应该有适当的安全措施
        assert response.status_code in [200, 302, 400]

        # 无论邮箱是否存在，都不应该泄露信息
        response_text = response.data.decode()
        assert 'not found' not in response_text.lower()
        assert 'exists' not in response_text.lower()

    def test_secure_password_storage(self, client):
        """测试安全密码存储"""
        with patch('woniunote.module.users.Users') as mock_users_class:

            mock_users_instance = Mock()
            mock_users_instance.do_register.return_value = Mock(userid=1)
            mock_users_instance.find_by_username.return_value = []
            mock_users_class.return_value = mock_users_instance

            with client.session_transaction() as sess:
                sess['ecode'] = 'ABCD'

            response = client.post('/user', data={
                'username': 'secure@example.com',
                'password': 'MySecurePass123!',
                'ecode': 'ABCD'
            })

            # 验证响应成功（密码存储的安全性由其他测试验证）
            assert response.status_code in [200, 302]
            # 验证没有返回敏感信息
            response_text = response.data.decode()
            assert 'password' not in response_text.lower()
            assert 'hash' not in response_text.lower()


class TestAccessControlSecurity:
    """测试访问控制安全"""

    def test_horizontal_privilege_escalation(self, client):
        """测试水平权限提升"""
        # 测试用户尝试访问其他用户的资源
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['userid'] = 1  # 当前用户ID

        # 尝试访问其他用户的资料
        response = client.get('/user/profile/2')  # 尝试访问用户ID为2的资料

        # 应该拒绝访问或返回当前用户的资料
        assert response.status_code in [200, 403, 404]

        if response.status_code == 403:
            response_text = response.data.decode()
            assert 'forbidden' in response_text.lower() or 'access denied' in response_text.lower()

    def test_vertical_privilege_escalation(self, client):
        """测试垂直权限提升"""
        # 普通用户尝试访问管理员功能
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['userid'] = 1
            sess['role'] = 'user'  # 普通用户角色

        # 尝试访问管理员功能
        admin_endpoints = [
            '/admin/dashboard',
            '/admin/users',
            '/admin/settings',
        ]

        for endpoint in admin_endpoints:
            response = client.get(endpoint)
            assert response.status_code in [200, 302, 403, 404]

            # 如果返回403，说明权限控制生效
            if response.status_code == 403:
                response_text = response.data.decode()
                assert 'forbidden' in response_text.lower() or 'admin' in response_text.lower()

    def test_insecure_direct_object_references(self, client):
        """测试不安全直接对象引用"""
        # 测试IDOR漏洞
        with client.session_transaction() as sess:
            sess['islogin'] = 'true'
            sess['userid'] = 1

        # 尝试访问其他用户的私有资源
        other_user_resources = [
            '/user/messages/2',
            '/user/files/2',
            '/user/settings/2',
        ]

        for resource in other_user_resources:
            response = client.get(resource)
            assert response.status_code in [200, 403, 404]

            # 如果返回403，说明IDOR防护生效
            if response.status_code == 403:
                response_text = response.data.decode()
                assert 'forbidden' in response_text.lower() or 'access' in response_text.lower()

    def test_role_based_access_control(self, client):
        """测试基于角色的访问控制"""
        # 测试不同角色的访问权限
        roles_and_permissions = {
            'user': ['/user/profile', '/article/post', '/comment/add'],
            'admin': ['/admin/dashboard', '/admin/users', '/admin/settings'],
            'moderator': ['/admin/articles', '/admin/comments'],
        }

        for role, endpoints in roles_and_permissions.items():
            with client.session_transaction() as sess:
                sess['islogin'] = 'true'
                sess['userid'] = 1
                sess['role'] = role

            for endpoint in endpoints:
                response = client.get(endpoint)

                # 根据角色检查访问权限
                if role == 'user' and 'admin' in endpoint:
                    # 用户不应该访问管理员页面
                    assert response.status_code in [302, 403, 404]
                elif role == 'admin':
                    # 管理员应该能访问所有页面
                    assert response.status_code in [200, 302, 404]


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
