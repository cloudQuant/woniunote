# ✍️ 测试编写指南

## 📋 概述

本指南介绍如何编写高质量的测试用例，包括测试结构、最佳实践、常用模式等。

## 🎯 测试编写原则

### 1. FIRST 原则
- **Fast**: 测试应该运行快速
- **Independent**: 测试间相互独立
- **Repeatable**: 测试结果可重现
- **Self-Validating**: 测试结果明确
- **Timely**: 测试应及时编写

### 2. 测试金字塔
```
End-to-End Tests    (少量)
    ↕️
Integration Tests  (中等)
    ↕️
Unit Tests        (大量)
```

## 🏗️ 测试结构

### 基本测试文件结构

```python
# tests/unit/test_example.py
import pytest
from unittest.mock import Mock, patch
from woniunote.controllers.example import ExampleController


class TestExampleController:
    """测试示例控制器"""

    def test_success_case(self, app, client):
        """测试成功场景"""
        # Given
        with app.app_context():
            # 准备测试数据

        # When
        response = client.get('/example/endpoint')

        # Then
        assert response.status_code == 200
        assert b'expected content' in response.data

    def test_error_case(self, app, client):
        """测试错误场景"""
        # Given
        # 准备错误条件

        # When
        response = client.get('/example/invalid')

        # Then
        assert response.status_code == 404

    def test_edge_case(self, app, client):
        """测试边界情况"""
        # Given
        # 准备边界条件

        # When
        # 执行测试

        # Then
        # 验证结果
```

## 🛠️ 常用测试模式

### 1. 单元测试模式

```python
class TestUserService:
    """测试用户服务"""

    @patch('woniunote.services.user_service.User')
    @patch('woniunote.services.user_service.db')
    def test_create_user_success(self, mock_db, mock_user_class):
        """测试用户创建成功"""
        # Given
        service = UserService()
        mock_user = Mock()
        mock_user_class.return_value = mock_user

        # When
        result = service.create_user('testuser', 'test@example.com')

        # Then
        assert result == mock_user
        mock_db.session.add.assert_called_once_with(mock_user)
        mock_db.session.commit.assert_called_once()
```

### 2. 控制器测试模式

```python
class TestUserController:
    """测试用户控制器"""

    def test_login_success(self, app, client):
        """测试登录成功"""
        # Given
        with app.test_request_context():
            from flask import session
            session['ecode'] = '123456'

        # When
        response = client.post('/login',
                             data={'username': 'testuser', 'password': '123456'})

        # Then
        assert response.status_code == 302  # 重定向
        assert '/loginfo' in response.headers['Location']

    def test_login_invalid_credentials(self, app, client):
        """测试登录失败 - 无效凭据"""
        # When
        response = client.post('/login',
                             data={'username': 'invalid', 'password': 'wrong'})

        # Then
        assert response.status_code == 200
        assert b'login failed' in response.data
```

### 3. 模型测试模式

```python
class TestUserModel:
    """测试用户模型"""

    def test_user_creation(self, db_session):
        """测试用户创建"""
        # Given
        user = User(username='testuser', email='test@example.com')

        # When
        db_session.add(user)
        db_session.commit()

        # Then
        assert user.id is not None
        assert user.username == 'testuser'
        assert user.created_at is not None

    def test_user_validation(self, db_session):
        """测试用户验证"""
        # Given
        user = User(username='', email='invalid-email')

        # When & Then
        with pytest.raises(ValueError):
            db_session.add(user)
            db_session.commit()
```

### 4. 集成测试模式

```python
class TestUserRegistrationFlow:
    """测试用户注册完整流程"""

    def test_complete_registration_flow(self, app, client):
        """测试完整注册流程"""
        # 1. 获取验证码
        response = client.post('/user/getcode', data={'email': 'test@example.com'})
        assert response.status_code == 200

        # 2. 注册用户 (模拟验证码)
        with app.test_request_context():
            from flask import session
            session['ecode'] = '123456'

        response = client.post('/user/user',
                             data={
                                 'username': 'testuser',
                                 'password': '123456',
                                 'email': 'test@example.com',
                                 'ecode': '123456'
                             })
        assert response.status_code == 302

        # 3. 验证用户已创建
        with app.app_context():
            from woniunote.models.user import User
            user = User.query.filter_by(username='testuser').first()
            assert user is not None
            assert user.email == 'test@example.com'
```

## 🧰 测试工具和技巧

### 夹具 (Fixtures)

```python
# conftest.py
@pytest.fixture
def app():
    """应用实例夹具"""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """测试客户端夹具"""
    return app.test_client()

@pytest.fixture
def db_session(app):
    """数据库会话夹具"""
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        session = db.create_scoped_session(
            options={"bind": connection, "binds": {}}
        )
        db.session = session
        yield session
        transaction.rollback()
        connection.close()
        session.remove()
```

### Mock 和 Patch

```python
class TestWithMocks:
    """使用 Mock 的测试示例"""

    @patch('woniunote.services.email_service.send_email')
    @patch('woniunote.common.database.db')
    def test_send_notification(self, mock_db, mock_send_email):
        """测试发送通知"""
        # Given
        service = NotificationService()
        mock_send_email.return_value = True

        # When
        result = service.send_notification('user@example.com', 'Test message')

        # Then
        assert result is True
        mock_send_email.assert_called_once_with(
            'user@example.com',
            'Test message',
            subject='Notification'
        )
```

### 参数化测试

```python
class TestParameterized:
    """参数化测试示例"""

    @pytest.mark.parametrize("input_value,expected", [
        (1, 2),
        (2, 4),
        (3, 6),
        (0, 0),
    ])
    def test_double_value(self, input_value, expected):
        """测试值翻倍"""
        assert double_value(input_value) == expected

    @pytest.mark.parametrize("username,password,should_succeed", [
        ('validuser', 'validpass', True),
        ('invaliduser', 'wrongpass', False),
        ('', 'password', False),
        ('username', '', False),
    ])
    def test_user_login(self, app, client, username, password, should_succeed):
        """测试用户登录各种场景"""
        response = client.post('/login',
                             data={'username': username, 'password': password})

        if should_succeed:
            assert response.status_code == 302
        else:
            assert response.status_code == 200
```

## 📊 覆盖率测试

### 语句覆盖率

```python
def test_complete_if_coverage():
    """测试完整 if 分支覆盖"""
    service = ExampleService()

    # 测试 if 分支
    result = service.process_value(10)
    assert result == 'positive'

    # 测试 else 分支
    result = service.process_value(-5)
    assert result == 'negative'

    # 测试边界条件
    result = service.process_value(0)
    assert result == 'zero'
```

### 异常覆盖率

```python
def test_exception_coverage():
    """测试异常处理覆盖"""
    service = RiskyService()

    # 测试正常情况
    result = service.divide(10, 2)
    assert result == 5

    # 测试异常情况
    with pytest.raises(ZeroDivisionError):
        service.divide(10, 0)

    # 测试自定义异常
    with pytest.raises(CustomValidationError):
        service.validate_input(None)
```

## 🔒 安全测试

### SQL 注入测试

```python
class TestSQLInjection:
    """SQL 注入安全测试"""

    def test_sql_injection_prevention(self, app, client):
        """测试 SQL 注入防护"""
        # Given
        malicious_input = "'; DROP TABLE users; --"

        # When
        response = client.post('/search',
                             data={'query': malicious_input})

        # Then
        assert response.status_code == 200
        # 验证数据未被删除
        with app.app_context():
            from woniunote.models.user import User
            users_count = User.query.count()
            assert users_count > 0
```

### XSS 防护测试

```python
class TestXSSProtection:
    """XSS 防护测试"""

    def test_xss_prevention(self, client):
        """测试 XSS 攻击防护"""
        # Given
        xss_payload = '<script>alert("XSS")</script>'

        # When
        response = client.post('/comment',
                             data={'content': xss_payload})

        # Then
        assert response.status_code == 200
        # 验证脚本被转义或过滤
        assert '<script>' not in response.get_data(as_text=True)
        assert '&lt;script&gt;' in response.get_data(as_text=True)
```

## ⚡ 性能测试

### 响应时间测试

```python
class TestPerformance:
    """性能测试"""

    def test_response_time(self, client):
        """测试响应时间"""
        import time

        start_time = time.time()
        response = client.get('/api/data')
        end_time = time.time()

        response_time = end_time - start_time

        assert response.status_code == 200
        assert response_time < 0.5  # 500ms 以内
```

### 负载测试

```python
class TestLoad:
    """负载测试"""

    def test_concurrent_requests(self, client):
        """测试并发请求"""
        import threading
        import queue

        results = queue.Queue()
        errors = []

        def make_request():
            try:
                response = client.get('/api/data')
                results.put(response.status_code)
            except Exception as e:
                errors.append(str(e))

        # 创建 10 个并发请求
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # 等待所有请求完成
        for thread in threads:
            thread.join()

        # 验证结果
        success_count = 0
        while not results.empty():
            status = results.get()
            if status == 200:
                success_count += 1

        assert success_count == 10
        assert len(errors) == 0
```

## 📋 测试命名规范

### 类命名
```python
class TestUserController:        # ✅ 正确
class TestUserCtrl:             # ❌ 缩写
class test_user_controller:     # ❌ 小写开头
```

### 方法命名
```python
def test_user_login_success():           # ✅ 描述性
def test_login():                        # ❌ 太泛化
def testUserLoginSuccess():              # ❌ 驼峰命名
def test_user_login_success_scenario():  # ❌ 太长
```

### 测试文件命名
```python
test_user_controller_comprehensive.py    # ✅ 清晰描述
test_uc.py                              # ❌ 缩写
user_test.py                            # ❌ 位置错误
testusercontroller.py                   # ❌ 无分隔符
```

## 🎯 最佳实践

### 1. 测试组织
- 按功能模块组织测试类
- 使用描述性的测试方法名
- 每个测试方法只测试一个场景

### 2. 测试数据
- 使用工厂方法创建测试数据
- 清理测试数据避免干扰
- 使用有意义的测试数据值

### 3. Mock 策略
- 只 Mock 外部依赖
- 验证 Mock 调用是否正确
- 使用 patch 装饰器保持代码清洁

### 4. 断言技巧
- 使用具体的断言消息
- 验证重要的副作用
- 检查错误情况的正确处理

### 5. 测试维护
- 及时更新失败的测试
- 重构重复的测试代码
- 保持测试与代码同步

## 📚 示例测试文件

查看项目中的实际测试文件：
- `tests/unit/test_user_controller_comprehensive.py`
- `tests/unit/test_models_comprehensive.py`
- `tests/integration/test_user_workflow_integration.py`

## 🔧 调试技巧

### 打印调试
```python
def test_debug_example(self, client):
    """调试示例"""
    response = client.get('/api/data')
    print(f"Status: {response.status_code}")
    print(f"Data: {response.get_data(as_text=True)}")
    assert response.status_code == 200
```

### 断点调试
```python
def test_breakpoint_example(self, client):
    """断点调试示例"""
    # 在测试中设置断点
    import pdb; pdb.set_trace()

    response = client.get('/api/data')
    assert response.status_code == 200
```

## 📊 测试质量指标

### 覆盖率目标
- **语句覆盖率**: ≥ 95%
- **分支覆盖率**: ≥ 90%
- **函数覆盖率**: ≥ 100%

### 性能指标
- **单个测试执行时间**: < 1秒
- **完整测试套件**: < 5分钟
- **内存使用**: < 500MB

### 可维护性指标
- **测试代码行数**: < 生产代码行数的 2倍
- **测试失败率**: < 5%
- **测试重构频率**: 随生产代码重构

## 📚 相关文档

- [测试环境设置指南](test-environment-setup.md)
- [测试执行指南](test-execution-guide.md)
- [CI/CD 集成指南](ci-cd-integration.md)
- [问题排查指南](troubleshooting.md)

---

*开始编写测试前，建议先阅读现有测试文件的代码风格和模式。*
