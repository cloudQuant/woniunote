# WoniuNote 第二阶段迁移指南

## 📋 概述

本文档提供了从旧的、分散的 `common` 模块迁移到第二阶段统一模块的详细指南。第二阶段整合了以下5个功能模块：

1. **统一缓存策略** (`unified_cache.py`)
2. **统一日志系统** (`unified_logging.py`) 
3. **统一配置管理** (`unified_config.py`)
4. **统一验证器** (`unified_validator.py`)
5. **统一工具函数** (`unified_utils.py`)

## 🚀 迁移步骤

### 1. 统一缓存策略

#### 旧代码
```python
from woniunote.common.advanced_cache import AdvancedCacheManager
from woniunote.common.cache_utils import MemoryCache
from woniunote.common.unified_cache_strategy import UnifiedCacheStrategy
from woniunote.common.static_cache_optimizer import StaticCacheOptimizer

# 初始化缓存
cache_manager = AdvancedCacheManager()
memory_cache = MemoryCache()
```

#### 新代码
```python
from woniunote.common.unified_cache import (
    UnifiedCacheManager, 
    CacheConfig, 
    CacheStrategy,
    cached,
    cache_invalidate
)

# 初始化统一缓存管理器
config = CacheConfig(
    ttl=300,
    max_size=1000,
    strategy=CacheStrategy.WRITE_THROUGH
)
cache_manager = UnifiedCacheManager(config)

# 使用装饰器
@cached(ttl=600, cache_manager=cache_manager)
def get_user_data(user_id):
    # 函数逻辑
    pass

@cache_invalidate(pattern="user:*", cache_manager=cache_manager)
def update_user_data(user_id):
    # 更新逻辑
    pass
```

#### 主要变化
- 所有缓存功能整合到一个 `UnifiedCacheManager` 类中
- 支持多层缓存（内存 + Redis）
- 提供统一的装饰器接口
- 支持多种缓存策略

### 2. 统一日志系统

#### 旧代码
```python
from woniunote.common.simple_logger import get_simple_logger
from woniunote.common.enhanced_logger import EnhancedLogger
from woniunote.common.log_level_manager import LogLevelManager

logger = get_simple_logger('my_module')
enhanced_logger = EnhancedLogger()
level_manager = LogLevelManager()
```

#### 新代码
```python
from woniunote.common.unified_logging import (
    UnifiedLogManager,
    LogConfig,
    LogLevel,
    LogFormat,
    log_function_call,
    log_performance
)

# 初始化统一日志管理器
config = LogConfig(
    level=LogLevel.INFO,
    format=LogFormat.STRUCTURED,
    enable_console=True,
    enable_file=True
)
log_manager = UnifiedLogManager(config)

# 获取logger
logger = log_manager.get_logger('my_module')

# 使用装饰器
@log_function_call(level="INFO", include_args=True)
def process_data(data):
    # 函数逻辑
    pass

@log_performance(threshold=1.0)
def heavy_operation():
    # 耗时操作
    pass
```

#### 主要变化
- 统一的日志配置和管理
- 支持多种日志格式（简单、详细、JSON、结构化）
- 提供函数调用和性能监控装饰器
- 统一的日志级别管理

### 3. 统一配置管理

#### 旧代码
```python
from woniunote.common.config_manager import ConfigManager
from woniunote.common.secure_config import SecureConfig
from woniunote.common.environment_validator import EnvironmentValidator

config_manager = ConfigManager()
secure_config = SecureConfig()
env_validator = EnvironmentValidator()
```

#### 新代码
```python
from woniunote.common.unified_config import (
    UnifiedConfigManager,
    ConfigSource,
    get_config,
    set_config
)

# 初始化统一配置管理器
config_manager = UnifiedConfigManager("configs")

# 从文件加载配置
config_manager.load_from_file("config.yaml", "database")

# 从环境变量加载配置
config_manager.load_from_environment("WONIU_")

# 获取配置值
db_host = get_config("host", "database", "localhost")
debug_mode = get_config("debug", "app", False)

# 设置配置值
set_config("max_connections", 100, "database")
```

#### 主要变化
- 统一的配置加载和管理
- 支持多种配置文件格式（JSON、YAML、INI、Python）
- 环境变量验证和加载
- 配置变更监听器

### 4. 统一验证器

#### 旧代码
```python
from woniunote.common.input_validator import InputValidator
from woniunote.common.enhanced_input_validator import EnhancedInputValidator
from woniunote.common.file_upload_validator import FileUploadValidator
from woniunote.common.permission_validator import PermissionValidator

input_validator = InputValidator()
file_validator = FileUploadValidator()
permission_validator = PermissionValidator()
```

#### 新代码
```python
from woniunote.common.unified_validator import (
    UnifiedValidator,
    ValidationResult,
    FileValidationRule,
    FileType,
    validate_input,
    validate_file,
    check_permission
)

# 初始化统一验证器
validator = UnifiedValidator()

# 验证输入数据
user_data = {"username": "john", "email": "john@example.com"}
result = validate_input(user_data)
if result.is_valid:
    # 处理有效数据
    pass

# 验证文件
file_rules = FileValidationRule(
    allowed_types=["image/jpeg", "image/png"],
    max_size=5*1024*1024,
    allowed_extensions=[".jpg", ".png"]
)
file_result = validate_file("user_photo.jpg", FileType.IMAGE, file_rules)

# 检查权限
has_access = check_permission("user", "article:read")
```

#### 主要变化
- 统一的验证接口
- 支持多种验证类型（输入、文件、权限）
- 可配置的验证规则
- 统一的验证结果格式

### 5. 统一工具函数

#### 旧代码
```python
from woniunote.common.timer import Timer
from woniunote.common.trace_id_manager import TraceIdManager
from woniunote.common.cleanup_manager import CleanupManager

timer = Timer()
trace_manager = TraceIdManager()
cleanup_manager = CleanupManager()
```

#### 新代码
```python
from woniunote.common.unified_utils import (
    UnifiedUtilsManager,
    timer,
    trace_id,
    cleanup_task,
    generate_uuid,
    generate_hash
)

# 初始化统一工具管理器
utils_manager = UnifiedUtilsManager()

# 使用装饰器
@timer(name="data_processing")
def process_large_dataset(data):
    # 数据处理逻辑
    pass

@trace_id(prefix="api_call")
def api_request():
    # API请求逻辑
    pass

@cleanup_task(name="temp_files", priority="high")
def cleanup_temp_files():
    # 清理临时文件
    pass

# 使用工具函数
request_id = generate_uuid("req")
file_hash = generate_hash("file_content", "sha256", 16)
```

#### 主要变化
- 统一的工具管理接口
- 提供多种装饰器（计时、追踪、清理）
- 常用工具函数整合
- 支持任务依赖和优先级

## 🔧 配置更新

### 应用初始化

#### 旧代码
```python
from woniunote.common import (
    init_simple_logger,
    init_config_manager,
    init_advanced_cache
)

# 初始化各个模块
init_simple_logger()
init_config_manager()
init_advanced_cache()
```

#### 新代码
```python
from woniunote.common import (
    init_unified_logging,
    init_unified_config_manager,
    init_unified_cache_manager,
    init_unified_validator,
    init_unified_utils
)

# 初始化统一模块
log_manager = init_unified_logging()
config_manager = init_unified_config_manager()
cache_manager = init_unified_cache_manager()
validator = init_unified_validator()
utils_manager = init_unified_utils()
```

## ⚠️ 重要注意事项

### 1. 向后兼容性
- 所有旧的函数名都保留为别名
- 旧的模块仍然可以导入，但建议迁移到新模块
- 迁移过程中可以逐步替换，不需要一次性全部更改

### 2. 性能考虑
- 新的统一模块经过优化，性能应该不会降低
- 建议在测试环境中验证性能表现
- 监控内存使用和响应时间

### 3. 错误处理
- 新的模块提供更统一的错误处理
- 建议更新错误处理逻辑以利用新功能
- 测试各种异常情况

## 📊 迁移检查清单

### 缓存模块
- [ ] 更新导入语句
- [ ] 替换缓存管理器初始化
- [ ] 更新缓存装饰器使用
- [ ] 测试缓存功能

### 日志模块
- [ ] 更新导入语句
- [ ] 配置新的日志管理器
- [ ] 更新日志装饰器使用
- [ ] 验证日志输出格式

### 配置模块
- [ ] 更新导入语句
- [ ] 迁移配置文件
- [ ] 更新配置访问方式
- [ ] 测试配置加载

### 验证模块
- [ ] 更新导入语句
- [ ] 替换验证器初始化
- [ ] 更新验证规则
- [ ] 测试验证功能

### 工具模块
- [ ] 更新导入语句
- [ ] 替换工具管理器初始化
- [ ] 更新装饰器使用
- [ ] 测试工具功能

## 🧪 测试建议

### 1. 单元测试
- 为每个新模块编写单元测试
- 测试所有公共接口
- 验证错误处理逻辑

### 2. 集成测试
- 测试模块间的交互
- 验证配置加载和验证
- 测试缓存和日志功能

### 3. 性能测试
- 对比迁移前后的性能
- 测试高负载情况
- 监控资源使用

## 🔄 回滚计划

如果迁移过程中遇到问题，可以按以下步骤回滚：

1. **恢复旧的导入语句**
2. **重新初始化旧模块**
3. **检查功能是否正常**
4. **分析问题原因**
5. **修复后重新迁移**

## 📞 支持

如果在迁移过程中遇到问题：

1. 查看模块的文档字符串
2. 检查错误日志
3. 参考示例代码
4. 联系开发团队

## 📝 更新日志

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2025-01-XX | 2.0 | 第二阶段迁移指南创建 |

---

**注意：** 本文档将根据实际迁移过程中的反馈进行更新和完善。
