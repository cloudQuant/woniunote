# WoniuNote 优化版快速启动指南

## 🚀 快速开始

### 1. 启动优化后的应用

```bash
# 启动开发服务器（包含所有优化功能）
python scripts/start_server.py --optimized

# 或直接运行优化版本
cd woniunote
python -c "
from app_factory import create_app
from common.cleanup_manager import start_cleanup_manager
from common.memory_monitor import get_memory_detector

app = create_app('development')
start_cleanup_manager()
print('🎉 WoniuNote 优化版启动成功！')
print('📊 访问 http://localhost:5001 查看应用')
print('🔍 访问 http://localhost:5001/admin/monitor 查看监控面板')
app.run(host='0.0.0.0', port=5001, debug=True)
"
```

### 2. 验证优化功能

```bash
# 运行优化验证测试
python scripts/verify_optimizations.py

# 检查内存监控
curl http://localhost:5001/api/memory/report

# 检查缓存状态
curl http://localhost:5001/api/cache/stats

# 查看资源使用情况
curl http://localhost:5001/api/resources/stats
```

## 📊 监控面板访问

### 内置监控端点
```bash
# 内存使用报告
GET /api/memory/report
{
  "current_memory_mb": 245.8,
  "memory_growth_rate": "2.3%",
  "tracked_resources": {...}
}

# 性能统计
GET /api/performance/stats
{
  "avg_response_time_ms": 85,
  "cache_hit_rate": "94.2%",
  "database_query_time_ms": 23
}

# 清理状态
GET /api/cleanup/status
{
  "running": true,
  "total_tasks": 5,
  "tasks": {...}
}
```

## 🛠️ 新功能使用示例

### 1. 使用增强的数据访问层

```python
# 新的开发模式
from woniunote.common.base_model import BaseModel
from woniunote.common.session_manager import database_transaction

class MyFeatureModel(BaseModel):
    def __init__(self):
        super().__init__("my_feature")
    
    @database_transaction('create_item')
    def create_item(self, data):
        # 自动事务管理，异常自动回滚
        return self.create(MyEntity, data)
    
    def find_items_with_cache(self, user_id):
        # 自动缓存管理
        return self.find_by_field(MyEntity, 'user_id', user_id)

# 使用示例
model = MyFeatureModel()
item = model.create_item({
    'name': 'Test Item',
    'description': 'This is a test'
})
```

### 2. 安全防护使用

```python
from woniunote.common.csrf_protection import csrf_protect
from woniunote.common.input_validator import validate_input

@csrf_protect  # 自动CSRF防护
@validate_input({
    'username': 'required|string|min:3|max:50',
    'email': 'required|email',
    'password': 'required|string|min:6'
})
def register_user():
    # 输入已自动验证和清理
    username = request.json['username']  # 安全的
    email = request.json['email']        # 已验证格式
    password = request.json['password']  # 已验证强度
    
    # 使用增强的密码处理
    from woniunote.common.password_utils import hash_password
    hashed = hash_password(password)
    
    # 创建用户...
```

### 3. 缓存策略使用

```python
from woniunote.common.cache_utils import cache_result, cache_invalidate

@cache_result(expiry=3600, cache_key="popular_articles")
def get_popular_articles():
    # 结果自动缓存1小时
    return Article.find_popular(limit=10)

@cache_result(expiry=1800, cache_key="user_profile_{user_id}")
def get_user_profile(user_id):
    # 用户相关缓存30分钟
    return User.find_with_stats(user_id)

# 缓存失效
def update_user_profile(user_id, data):
    user = User.update(user_id, data)
    cache_invalidate(f"user_profile_{user_id}")
    return user
```

### 4. 资源管理使用

```python
from woniunote.common.resource_manager import get_managed_file, get_managed_db_connection

# 安全的文件操作
with get_managed_file('data.txt', 'r') as f:
    content = f.read()
    # 文件句柄自动管理和清理

# 安全的数据库操作
with get_managed_db_connection(db_config) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    # 连接自动管理和清理
```

## 🔧 开发工具使用

### 1. 性能分析

```python
from woniunote.common.memory_monitor import memory_profile
from woniunote.common.resource_manager import resource_monitor

@memory_profile
@resource_monitor('heavy_computation')
def expensive_operation(data):
    # 自动分析内存使用和资源消耗
    result = process_large_dataset(data)
    return result

# 查看分析结果在日志中
```

### 2. 调试和故障排除

```python
# 强制内存清理
from woniunote.common.memory_monitor import trigger_memory_cleanup
trigger_memory_cleanup()

# 获取详细内存报告
from woniunote.common.memory_monitor import get_memory_report
report = get_memory_report()
print(f"当前内存使用: {report['current_memory']['process_memory_mb']} MB")

# 强制执行所有清理任务
from woniunote.common.cleanup_manager import force_cleanup
force_cleanup()
```

### 3. 自定义清理任务

```python
from woniunote.common.cleanup_manager import register_cleanup_task

def my_custom_cleanup():
    """自定义清理逻辑"""
    # 清理临时文件
    import os
    import glob
    temp_files = glob.glob('/tmp/my_app_*.tmp')
    for file in temp_files:
        os.remove(file)
    
    print(f"清理了 {len(temp_files)} 个临时文件")

# 注册每小时执行的清理任务
register_cleanup_task(
    name="temp_file_cleanup",
    func=my_custom_cleanup,
    interval_seconds=3600,
    description="清理临时文件"
)
```

## 🧪 测试优化功能

### 1. 性能测试

```bash
# 运行性能测试套件
python -m pytest tests/test_performance.py -v

# 使用Locust进行负载测试
locust -f tests/locust_performance.py --host=http://localhost:5001

# 内存泄露检测测试
python tests/test_memory_leaks.py
```

### 2. 安全测试

```bash
# CSRF保护测试
python -m pytest tests/test_csrf_protection.py -v

# 输入验证测试  
python -m pytest tests/test_input_validation.py -v

# SQL注入防护测试
python -m pytest tests/test_sql_injection.py -v
```

### 3. 缓存测试

```bash
# 缓存功能测试
python -m pytest tests/test_cache_utils.py -v

# 缓存性能测试
python tests/benchmark_cache.py
```

## 📈 监控和维护

### 1. 日常监控检查

```bash
# 每日健康检查脚本
python scripts/daily_health_check.py

# 查看内存使用趋势
curl http://localhost:5001/api/memory/history?hours=24

# 检查清理任务状态
curl http://localhost:5001/api/cleanup/status
```

### 2. 性能调优

```python
# 调整缓存配置
from woniunote.common.cache_utils import configure_cache
configure_cache({
    'default_expiry': 1800,  # 30分钟
    'max_size': 1000,       # 最大缓存项数
    'cleanup_interval': 300  # 5分钟清理间隔
})

# 调整内存监控阈值
from woniunote.common.memory_monitor import get_memory_detector
detector = get_memory_detector()
detector.memory_warning_threshold_mb = 400  # 400MB警告
detector.memory_critical_threshold_mb = 800  # 800MB临界
```

### 3. 故障排除

```python
# 诊断内存问题
from woniunote.common.memory_monitor import get_memory_detector
detector = get_memory_detector()

# 获取内存历史
history = detector.get_memory_history(hours=2)
for snapshot in history[-5:]:  # 最近5个快照
    print(f"{snapshot['timestamp']}: {snapshot['process_memory_mb']} MB")

# 诊断资源泄露
from woniunote.common.resource_manager import get_resource_stats
stats = get_resource_stats()
print("资源使用统计:", stats)

# 检查长期运行的会话
from woniunote.common.session_manager import get_global_session_manager
if get_global_session_manager():
    session_stats = get_global_session_manager().get_session_stats()
    print("会话统计:", session_stats)
```

## 🎯 最佳实践

### 1. 新功能开发流程

1. **使用模板创建新模块**
```bash
python scripts/create_new_module.py --name my_feature
```

2. **遵循安全编码规范**
   - 总是使用 `@csrf_protect` 装饰器
   - 使用 `@validate_input` 验证输入
   - 使用 `BaseModel` 进行数据访问

3. **添加缓存策略**
   - 为查询密集的操作添加缓存
   - 设置合理的过期时间
   - 实现缓存失效逻辑

4. **编写测试**
   - 单元测试覆盖核心逻辑
   - 集成测试验证功能流程
   - 性能测试确保不回归

### 2. 生产部署检查

```bash
# 部署前检查清单
python scripts/pre_deploy_check.py

# 包含以下检查项：
# ✓ 数据库索引是否就绪
# ✓ 缓存配置是否正确
# ✓ 安全设置是否启用
# ✓ 监控系统是否运行
# ✓ 清理任务是否注册
# ✓ 日志配置是否正确
```

## 📞 获取帮助

### 文档资源
- **完整API文档**: `/docs/api_reference.md`
- **架构说明**: `/docs/architecture_guide.md`
- **安全指南**: `/docs/security_guide.md`
- **性能优化**: `/docs/performance_guide.md`

### 调试工具
- **管理面板**: `http://localhost:5001/admin`
- **监控仪表板**: `http://localhost:5001/admin/monitor`
- **性能分析**: `http://localhost:5001/admin/performance`
- **安全日志**: `http://localhost:5001/admin/security`

---

🎉 **恭喜！您现在可以充分利用 WoniuNote 的所有优化功能了！**

这些优化让您的应用具备了企业级的性能、安全性和可维护性。继续使用这些最佳实践，您的项目将持续保持高质量和高性能！