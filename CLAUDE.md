# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WoniuNote (蜗牛笔记) is a comprehensive Flask-based blog and content management system built with modern web development best practices. It's a production-ready web application currently running at https://www.yunjinqi.top, serving as a personal blog platform with advanced features.

### Core Features
- **Content Management**: Article publishing, editing, categorization, and search
- **User System**: Registration, authentication, role-based access control, credit system
- **Interactive Learning**: Flashcard system (Card Center) for spaced repetition learning
- **Task Management**: Todo Center with categories and scheduling
- **Mathematical Training**: Special module for mathematical exercises and training
- **Rich Text Editing**: Integrated UEditor for Chinese content editing
- **Comment System**: Full-featured commenting with moderation
- **Favorites System**: Bookmark and organize favorite articles
- **Admin Panel**: Comprehensive administration interface
- **Performance Monitoring**: Built-in metrics, caching, and optimization

### Advanced Technical Features
- **Multi-layer Caching**: Redis primary with memory fallback
- **Security Enhancements**: Rate limiting, CSRF protection, input validation, JWT authentication
- **Performance Optimization**: Query optimization, connection pooling, monitoring
- **High Availability**: Error recovery, circuit breakers, graceful degradation
- **Comprehensive Testing**: Unit, integration, and performance tests with 85%+ coverage

## Development Commands

### Installation and Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install project package (REQUIRED for development - enables imports to work correctly)
pip install -e .

# Create configuration file (REQUIRED before first run)
# Windows:
copy configs\user_password_config.yaml.example configs\user_password_config.yaml
# Linux/Mac:
cp configs/user_password_config.yaml.example configs/user_password_config.yaml

# Edit configs/user_password_config.yaml with your database and Redis settings
# Required fields: database host/port/name/username/password, security secret_key
# Optional: Redis configuration (will use in-memory cache if not configured)

# Create SSL certificates for local HTTPS testing (optional)
cd woniunote\configs  # Windows
# cd woniunote/configs  # Linux/Mac
openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365
```

### Running the Application
```bash
# Development server (direct run, default port 5000)
cd woniunote
python app.py

# Development server with Flask CLI
# Windows:
set FLASK_APP=woniunote.app
set FLASK_ENV=development
flask run

# Linux/Mac:
export FLASK_APP=woniunote.app
export FLASK_ENV=development
flask run

# Production server with Gunicorn (Linux/Mac only)
cd woniunote
gunicorn -w 4 -b 0.0.0.0:8888 --timeout 120 app:app

# Background production server (Linux/Mac)
nohup gunicorn -w 4 -b 0.0.0.0:8888 --log-level debug app:app > woniunote_run.log 2>&1 &
```

### Testing
```bash
# IMPORTANT: Install project package first (required for tests to run)
pip install -e .

# Install test dependencies (included in requirements.txt)
playwright install

# 🚀 Recommended: Run all tests with parallel execution and coverage
# This runs tests in parallel, analyzes pass rates, and generates coverage reports
python tests/run_all_tests.py

# Run with specific mode flags
python tests/run_all_tests.py --parallel      # Explicit parallel mode with optimal worker count
python tests/run_all_tests.py --fast          # Fast mode with reduced timeout
python tests/run_all_tests.py --coverage      # Full coverage analysis
python tests/run_all_tests.py --debug         # Debug mode with verbose output
python tests/run_all_tests.py --verbose       # Verbose output showing all details

# Traditional pytest commands (non-parallel)
# Run all tests with coverage (recommended)
pytest . -v --cov=woniunote --cov-report=html --cov-report=term-missing

# Run all tests in parallel with pytest-xdist
pytest . -v -n auto

# Run tests without coverage (faster for development)
pytest . -v

# Run specific test file
pytest tests/unit/test_common_utils.py -v

# Run specific test class or function
pytest tests/unit/test_common_utils.py::TestUtils::test_generate_id -v

# Run tests matching pattern
pytest -k "test_user" -v          # All tests with 'test_user' in name
pytest -k "test_article" -v       # All tests with 'test_article' in name

# Run tests with markers (defined in pytest.ini)
pytest -m "not slow" -v           # Skip slow tests
pytest -m "not browser" -v        # Skip browser tests
pytest -m unit -v                 # Run only unit tests
pytest -m integration -v          # Run only integration tests

# Debugging options
pytest . -v -x                    # Stop at first failure (useful for debugging)
pytest . -v --tb=long             # Show local variables on failure
pytest . -v -s                    # Run with verbose output and print statements

# Generate HTML coverage report
pytest . --cov=woniunote --cov-report=html
# View report: open htmlcov/index.html

# Performance/load testing (requires running server)
locust -f tests/test_performance.py --host=http://localhost:5000
```

#### Test Results & Coverage
The test suite includes **300+ test cases** with:
- **100% pass rate**: All tests passing
- **85%+ code coverage**: Core functionality comprehensively tested
- **Multi-layer testing**: Unit, integration, controller, model, and error handling tests
- **Parallel execution**: Automatic optimal worker count calculation based on CPU and memory
- **Comprehensive reporting**: Detailed pass/fail statistics and coverage analysis

### Database Operations
```bash
# Database optimization and maintenance
python scripts/optimize_database_indexes.py   # Optimize database indexes

# Note: Database is auto-initialized on first app.py run through SQLAlchemy
# Models are defined in:
# - woniunote/common/create_database.py (User, Article, Comment models)
# - woniunote/models/card.py (Card, CardCategory models)
# - woniunote/models/todo.py (Item, Category models)
```

### Code Quality and Linting
```bash
# Install pre-commit hooks (optional but recommended)
pip install pre-commit
pre-commit install

# Run code formatting and linting manually
black --line-length=100 woniunote            # Code formatting
isort --profile black woniunote              # Import sorting
flake8 woniunote --max-line-length=100       # Linting
mypy woniunote                               # Type checking
bandit -r woniunote -ll                      # Security checking
safety check                                 # Dependency vulnerability checking

# Run all pre-commit checks manually
pre-commit run --all-files
```

### Development Utilities
```bash
# Redis setup for Windows
python scripts/install_redis_windows.py      # Install Redis on Windows
python scripts/quick_redis_setup.py          # Quick Redis configuration

# Database optimization
python scripts/optimize_database_indexes.py  # Optimize database indexes

# Environment configuration for different modes
# Windows:
set WONIUNOTE_TEST_MODE=true
set TESTING=1
set DEBUG=true
set FLASK_ENV=testing

# Linux/Mac:
export WONIUNOTE_TEST_MODE=true
export TESTING=1
export DEBUG=true
export FLASK_ENV=testing
```

## Architecture Overview

### Project Structure (Updated 2025-08-21)
```
woniunote/                      # Root directory (cleaned and organized)
├── README.md                   # Project documentation
├── LICENSE                     # MIT License
├── requirements.txt            # Python dependencies
├── setup.py                    # Package installation configuration
├── setup.cfg                   # Configuration for tools
├── pytest.ini                 # Testing configuration
├── CLAUDE.md                   # AI assistant guidance (this file)
├── .gitignore                  # Git ignore patterns
├── .pre-commit-config.yaml     # Pre-commit hooks configuration
│
├── configs/                    # Configuration files
│   ├── config.py              # Main Flask configuration classes
│   ├── user_password_config.yaml.example # Template for sensitive config
│   ├── user_password_config.yaml # Sensitive configuration (not in VCS)
│   └── development_config.yaml   # Development environment config
│
├── docs/                       # Documentation and guides
│   ├── README.md              # Documentation index
│   ├── API_DOCUMENTATION.md   # API reference
│   ├── DEPLOYMENT_GUIDE.md    # Deployment instructions
│   ├── woniunote_db.sql       # Database schema
│   └── *.md                   # Various documentation files
│
├── scripts/                    # Development and deployment scripts
│   ├── start_server.py        # Application startup script
│   ├── init_db_direct.py      # Database initialization
│   ├── run_tests.py           # Test runner with options
│   ├── install_unix.sh        # Unix installation script
│   ├── install_win.bat        # Windows installation script
│   ├── push_to_both.*         # Repository sync scripts
│   └── *.py                   # Other utility scripts
│
├── tests/                      # Comprehensive test suite (100% pass rate)
│   ├── __init__.py            # Test package marker
│   ├── conftest.py            # Test configuration and fixtures
│   ├── unit/                  # Unit tests for individual components
│   │   ├── test_common_utils.py # Common utilities tests
│   │   ├── test_articles_comprehensive.py # Article module tests
│   │   ├── test_users_comprehensive.py # User module tests
│   │   └── *.py              # Other unit tests
│   ├── utils/                 # Test utilities and helpers
│   │   ├── app_launcher.py    # Test application launcher
│   │   ├── server_manager.py  # Test server management
│   │   └── *.py              # Test helper modules
│   └── configs/               # Test configuration files
│       ├── test_config.yaml   # Test environment config
│       └── user_password_config.yaml # Test database config
│
├── logs/                       # Centralized logging directory (NEW)
│   ├── security_audit.log     # Security event logs
│   └── *.log                  # Application and module logs
│
├── tools/                      # Additional development tools
│   └── on_time_run.py         # Scheduling utilities
│
└── woniunote/                  # Main application package
    ├── __init__.py            # Package marker
    ├── app.py                 # Flask application entry point
    ├── app_factory.py         # Application factory pattern
    │
    ├── controller/            # Flask blueprints (URL routing layer)
    │   ├── __init__.py       # Controller package marker
    │   ├── index.py          # Homepage routes and pagination
    │   ├── article.py        # Article CRUD operations
    │   ├── user.py           # User authentication and session management
    │   ├── admin.py          # Admin panel and management functions
    │   ├── ucenter.py        # User center and profile management
    │   ├── ueditor.py        # Rich text editor integration
    │   ├── comment.py        # Comment system
    │   ├── favorite.py       # Bookmarks and favorites
    │   ├── card_center.py    # Flashcard learning system
    │   └── todo_center.py    # Task management system
    │
    ├── module/                # Data access layer (business logic)
    │   ├── __init__.py       # Module package marker
    │   ├── articles.py       # Article data operations with logging
    │   ├── users.py          # User data operations with logging
    │   ├── comments.py       # Comment data operations
    │   ├── credits.py        # Credit/points system
    │   └── favorites.py      # Favorites data operations
    │
    ├── models/                # SQLAlchemy model definitions
    │   ├── __init__.py       # Models package marker
    │   ├── card.py           # Card and CardCategory models
    │   └── todo.py           # Item and Category models for todos
    │
    ├── common/                # Shared utilities and infrastructure
    │   ├── __init__.py       # Common package marker
    │   │
    │   ├── 🔧 Core Database & Models
    │   ├── database.py       # Database configuration and connection
    │   ├── create_database.py # Core model definitions (User, Article, Comment)
    │   ├── card_database.py  # Card system database operations
    │   ├── todo_database.py  # Todo system database operations
    │   │
    │   ├── 🎯 Unified Architecture Modules (Phase 1-6 Optimization)
    │   ├── unified_cache.py  # ⚡ Unified cache management (Redis + memory fallback)
    │   ├── unified_config.py # ⚙️ Unified configuration management
    │   ├── unified_database_optimizer.py # 🗄️ Advanced database optimization
    │   ├── unified_error_handler.py # ⚠️ Unified error handling and recovery
    │   ├── unified_logging.py # 📝 Structured logging with trace IDs
    │   ├── unified_monitoring.py # 📊 Performance monitoring and metrics
    │   ├── unified_response.py # 📤 Standardized API responses
    │   ├── unified_security.py # 🛡️ Security (JWT, CSRF, rate limiting, API auth)
    │   ├── unified_session.py # 🔐 Session management and security
    │   ├── unified_utils.py  # 🛠️ Common utility functions
    │   ├── unified_validator.py # ✅ Input validation and sanitization
    │   │
    │   ├── 🚀 Advanced Enhancement Modules
    │   ├── async_tasks.py    # 🔄 Asynchronous task execution
    │   ├── rate_limiter.py   # 🚦 API rate limiting system
    │   ├── static_optimizer.py # 🎨 Static resource optimization
    │   ├── performance_enhanced.py # ⚡ Performance enhancement features
    │   ├── user_experience_optimizer.py # 🎯 UX optimization and tracking
    │   │
    │   ├── 🔒 Security & Authentication
    │   ├── password_utils.py # Password hashing and validation
    │   ├── secure_password.py # Enhanced password security
    │   ├── auth_utils.py     # Authentication utilities
    │   ├── authorization.py  # Authorization and permissions
    │   │
    │   ├── 📊 Resource Management
    │   ├── memory_monitor.py # Memory usage monitoring
    │   ├── memory_optimizer.py # Memory optimization
    │   ├── resource_manager.py # System resource management
    │   ├── cache_manager.py  # Cache management
    │   ├── secure_redis_manager.py # Secure Redis connection management
    │   ├── db_connection_manager.py # Database connection pooling
    │   │
    │   ├── 🛠️ Utilities & Helpers
    │   ├── utils.py          # Core utility functions
    │   ├── redisdb.py        # Redis database utilities
    │   ├── safe_credit_manager.py # Credit system utilities
    │   ├── readcount_flusher.py # Read count batch updates
    │   ├── log_decorator.py  # Logging decorators
    │   ├── base_model.py     # Base model classes
    │   └── code_refactor_helper.py # Code refactoring utilities
    │
    ├── template/              # Jinja2 HTML templates
    │   ├── base.html         # Base template
    │   ├── index.html        # Homepage template
    │   ├── article-*.html    # Article-related templates
    │   ├── user-*.html       # User-related templates
    │   └── *.html           # Other templates
    │
    ├── resource/              # Static assets (CSS, JS, images)
    │   ├── css/              # Stylesheets
    │   ├── js/               # JavaScript files
    │   ├── img/              # Images
    │   ├── icon/             # Icon fonts and images
    │   └── upload/           # User uploaded files
    │
    ├── services/              # Service layer for complex operations
    │   └── article_service.py # Article business services
    │
    └── configs/               # Application-specific configurations
        ├── config.py         # Flask configuration classes
        ├── article_type_config.yaml # Article categorization
        ├── cert.pem          # SSL certificate (local development)
        ├── key.pem           # SSL private key (local development)
        └── *.yaml           # Other configuration files
```

### Technology Stack
- **Backend Framework**: Flask 2.x with SQLAlchemy ORM and Flask-Session
- **Database**: MySQL 8.0+ (production), SQLite (development/testing)
- **Caching**: Redis 4.5+ with memory fallback
- **Frontend**: HTML5, CSS3, JavaScript ES6+, Bootstrap 4, Vue.js components
- **Rich Text Editor**: UEditor (百度编辑器) - Chinese-optimized WYSIWYG editor
- **Testing**: pytest ecosystem (pytest-flask, pytest-cov, pytest-mock, playwright)
- **Performance Testing**: Locust for load testing
- **Deployment**: Gunicorn WSGI server with Nginx proxy
- **Security**: Flask-WTF for CSRF, custom rate limiting, JWT authentication
- **Monitoring**: Custom metrics collection and performance monitoring

### Key Architecture Features
- **App Factory Pattern**: Uses direct app.py instantiation with modular configuration loading
- **Modular Blueprint Architecture**: 10 specialized blueprints (index, user, article, admin, ucenter, ueditor, comment, favorite, card, todo)
- **Unified Architecture System**: 11 core unified modules providing consistent interfaces across the application:
  - `unified_cache.py`: Multi-layer caching (Redis primary with intelligent memory fallback)
  - `unified_config.py`: Centralized configuration management with runtime updates
  - `unified_database_optimizer.py`: Advanced query optimization, connection pooling, slow query detection
  - `unified_error_handler.py`: Comprehensive error handling with circuit breakers and graceful degradation
  - `unified_logging.py`: Structured logging with trace IDs for request correlation
  - `unified_monitoring.py`: Real-time performance monitoring, metrics collection, intelligent ops management
  - `unified_response.py`: Standardized API response formats
  - `unified_security.py`: JWT authentication, CSRF protection, API key/signature validation
  - `unified_session.py`: Enhanced session management with security features
  - `unified_utils.py`: Common utility functions with consistent error handling
  - `unified_validator.py`: Input validation and sanitization
- **Advanced Enhancement Modules**:
  - `async_tasks.py`: Background task execution for email, image compression, etc.
  - `rate_limiter.py`: Configurable API rate limiting with whitelist support
  - `static_optimizer.py`: Frontend resource optimization (minification, compression, CDN)
  - `performance_enhanced.py`: Smart caching decorators and performance tracking
  - `user_experience_optimizer.py`: User action tracking, personalization, notifications
- **Database Optimization**: Advanced query optimization, connection pooling, automatic recovery, slow query detection
- **Security Enhancements**: Multi-layer security with JWT, CSRF, rate limiting, input validation, API authentication
- **Resource Management**: Memory monitoring, session cleanup automation, Redis connection pooling
- **Error Recovery**: Circuit breakers, graceful degradation, automatic reconnection for external services
- **Structured Logging**: Comprehensive logging with trace IDs via `unified_logging.py` (replaces `simple_logger.py`)

### Configuration Management
- **Main Configuration**: `woniunote/configs/config.py` - Flask app configuration classes
- **Sensitive Configuration**: `configs/user_password_config.yaml` (create from `.example`) - Database, Redis, email, security credentials
  - REQUIRED: Copy `user_password_config.yaml.example` to `user_password_config.yaml` before first run
  - Required fields:
    - `database`: host, port, name, username, password
    - `security.secret_key`: Flask secret key for session encryption
  - Optional fields:
    - `redis`: host, port, db, password (falls back to memory cache if not configured)
    - `mail`: SMTP configuration for email notifications
- **Database Configuration**: `common/database.py` - Database connection and model definitions
- **Article Types**: Dynamic configuration via YAML files for content categorization
- **Environment Support**: Development, testing, production configurations with override capabilities
- **Unified Configuration**: `unified_config.py` provides runtime configuration updates for non-critical settings

### Testing Architecture (100% Pass Rate Achieved)
- **Unit Tests**: `/tests/unit/` - Test individual functions and classes with comprehensive mocking
- **Integration Tests**: Database operations, external service integration, and API testing
- **Comprehensive Coverage**: Multi-layered test suites with 100% test pass rate and high code coverage
- **Performance Tests**: Load testing with Locust framework for scalability validation
- **Browser Tests**: Playwright for end-to-end UI testing and user workflow validation
- **Test Utilities**: `/tests/utils/` - Shared test helpers and fixtures
- **Configuration Testing**: Separate test configurations for isolated test environments
- **Bug Fix Validation**: All tests include verification of 6+ critical bug fixes implemented during development
- **Mock-based Testing**: Extensive use of mocking to avoid Flask context issues and ensure test isolation
- **Automated Test Running**: Custom test runners with filtering options for different test categories

### Development Notes
- **Language**: Project uses Chinese comments and documentation extensively (mixed Chinese/English codebase)
- **UEditor Integration**: Rich text editor requires specific CSP policies and iframe permissions for proper functionality
- **SSL Support**: HTTPS development requires SSL certificates (use provided OpenSSL commands)
- **Database Initialization**: Comprehensive scripts handle table creation, sample data, and migrations
- **Performance Monitoring**: Built-in monitoring accessible through admin panel with real-time metrics
- **Logging System**: Structured logging with trace IDs for request correlation and debugging
- **Error Handling**: Advanced error recovery mechanisms with graceful degradation
- **Session Management**: Enhanced session handling with security features and automatic cleanup

### Code Quality Standards
- **Documentation**: Functions should be documented with comprehensive docstrings (Chinese/English)
- **Decorator Pattern**: Use decorators for cross-cutting concerns (authentication, error handling, performance monitoring)
- **Function Decomposition**: Large functions should be decomposed into smaller, testable helper functions
- **Naming Conventions**: Follow existing patterns (snake_case for functions, PascalCase for classes)
- **Error Handling**: Implement comprehensive error handling with logging and user-friendly messages
- **Performance**: Consider caching, database optimization, and resource management in implementations
- **Security**: Validate all inputs, use parameterized queries, implement proper authentication/authorization
- **Testing**: Write tests for new functionality with appropriate coverage

### Common Development Patterns

#### Blueprint Registration Pattern
All controllers follow a standard blueprint pattern:
```python
from flask import Blueprint
blueprint_name = Blueprint('name', __name__)
# Routes are registered with @blueprint_name.route()
# Blueprint is registered in app_factory.py with url_prefix
```

#### Database Session Management
Use context managers for database operations:
```python
from woniunote.common.database import db
with db.session.begin():
    # Database operations
    db.session.add(model)
# Session auto-commits on success, rolls back on exception
```

#### Caching Pattern
Use the unified cache strategy:
```python
from woniunote.common.cache_utils import cached
@cached(key_prefix='article', timeout=300)
def get_article(article_id):
    # Expensive operation
    return result
```

#### Logging Pattern
All modules use structured logging with trace IDs:
```python
from woniunote.common.simple_logger import get_simple_logger
logger = get_simple_logger('module_name')
logger.info(f"Operation completed", extra={'trace_id': g.request_id})
```

#### Authentication Pattern
Use session-based authentication:
```python
from woniunote.common.session_utils import is_user_logged_in, get_current_user
if not is_user_logged_in():
    return redirect(url_for('user.login'))
user = get_current_user()
```

#### Error Handling Pattern
Comprehensive error handling with recovery via unified_error_handler:
```python
from woniunote.common.unified_error_handler import handle_error, ErrorType

try:
    # Operation
    result = perform_operation()
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    db.session.rollback()
    return handle_error(e, ErrorType.DATABASE_ERROR)
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    return handle_error(e, ErrorType.SYSTEM_ERROR)
```

## Development Patterns with Unified Modules

### Using Unified Logging with Trace IDs
```python
from woniunote.common.unified_logging import get_simple_logger
from flask import g

logger = get_simple_logger(__name__)

# Automatically includes trace_id from Flask's request context
logger.info("Operation started", extra={'user_id': user_id})
logger.error("Operation failed", exc_info=True)
```

### Using Unified Cache for Performance
```python
from woniunote.common.unified_cache import cached

@cached(key_prefix='article', timeout=300)
def get_article_by_id(article_id):
    """This will be cached for 300 seconds, with Redis primary fallback"""
    return Article.query.get(article_id)

# Or use decorator for function-level caching
@app.route('/api/articles/<int:id>')
@cached(key_prefix='api_article', timeout=600)
def get_article_api(id):
    return jsonify(get_article_by_id(id))
```

### Using Unified Security for Authentication
```python
from woniunote.common.unified_security import require_jwt_auth, admin_required

@app.route('/api/admin/users', methods=['GET'])
@require_jwt_auth  # Validates JWT token
@admin_required    # Checks admin role
def list_all_users():
    """Only accessible to authenticated admin users"""
    return jsonify(get_all_users())
```

### Using Rate Limiter
```python
from woniunote.common.rate_limiter import rate_limit

@app.route('/api/login', methods=['POST'])
@rate_limit(max_requests=5, window_seconds=60)  # 5 requests per minute
def login():
    """Rate limited to prevent brute force attacks"""
    return handle_login()
```

### Using Async Tasks
```python
from woniunote.common.async_tasks import async_send_email, async_compress_image

@app.route('/register', methods=['POST'])
def register():
    # Register user
    user = create_user(...)

    # Send welcome email asynchronously
    async_send_email(user.email, 'Welcome!', template='welcome')

    # Compress uploaded image asynchronously
    async_compress_image(upload_path, output_path)

    return jsonify({'success': True})
```

### Using Unified Configuration
```python
from woniunote.common.unified_config import get_config_manager

config_manager = get_config_manager()

# Get configuration value with fallback
debug_mode = config_manager.get('DEBUG', False)
cache_ttl = config_manager.get('CACHE_TTL', 300)

# Update configuration at runtime
config_manager.set('FEATURE_FLAG_X', True)
```

### Using Performance Monitoring
```python
from woniunote.common.unified_monitoring import monitor_function
from woniunote.common.performance_enhanced import smart_cache, async_task

@monitor_function
def expensive_operation(data):
    """Automatically logs execution time and performance metrics"""
    return process(data)

@smart_cache(ttl=600)
def get_user_stats(user_id):
    """Combines caching and performance monitoring"""
    return calculate_stats(user_id)

@async_task
def send_bulk_emails(recipients, subject, body):
    """Executes in background thread"""
    for recipient in recipients:
        send_email(recipient, subject, body)
```

### Important Files to Understand

#### Core Application Files
- `woniunote/app.py`: Main Flask application entry point with comprehensive route definitions, security headers, and middleware
  - Imports and initializes all 11 unified modules during startup
  - Sets up security headers, CORS, and error handlers
  - Registers all 10 controller blueprints
- `woniunote/configs/config.py`: Flask configuration classes for different environments (Development, Testing, Production)

#### Unified Module Imports in app.py (Reference Pattern)
```python
# Logging & Monitoring
from woniunote.common.unified_logging import get_simple_logger
from woniunote.common.unified_monitoring import init_monitoring, monitor_function

# Caching & Configuration
from woniunote.common.unified_cache import init_cache, cached
from woniunote.common.unified_config import get_config_manager

# Security & Validation
from woniunote.common.unified_security import init_security, require_jwt_auth, admin_required
from woniunote.common.unified_validator import validate_input

# Performance & Enhancement
from woniunote.common.async_tasks import init_task_executor, async_send_email
from woniunote.common.rate_limiter import init_rate_limiter, rate_limit
from woniunote.common.performance_enhanced import smart_cache, async_task
```

#### Database and Models
- `woniunote/common/database.py`: Database configuration, session management, connection pooling
- `woniunote/common/create_database.py`: Core model definitions (User, Article, Comment, Category, Tag)
- `woniunote/models/card.py`: Card and CardCategory models for flashcard learning system
- `woniunote/models/todo.py`: Item and Category models for task management system

#### Business Logic Layer
- `woniunote/module/articles.py`: Article operations with comprehensive logging and trace management
- `woniunote/module/users.py`: User operations with authentication and credit system integration
- `woniunote/module/comments.py`: Comment system data operations
- `woniunote/module/credits.py`: Credit/points system for user engagement
- `woniunote/module/favorites.py`: Favorites data operations

#### Controller Layer (Blueprints)
- `woniunote/controller/index.py`: Homepage routes, pagination, and content display with logging
- `woniunote/controller/user.py`: User authentication, registration, login/logout with security
- `woniunote/controller/article.py`: Article CRUD operations and content management
- `woniunote/controller/admin.py`: Administrative functions and management panel
- `woniunote/controller/card_center.py`: Flashcard learning system interface
- `woniunote/controller/todo_center.py`: Task management system interface

#### Configuration and Testing
- `woniunote/configs/config.py`: Flask configuration classes for different environments
- `configs/user_password_config.yaml`: Sensitive configuration (database, Redis, email credentials)
- `tests/conftest.py`: Test configuration, fixtures, and shared test utilities
- `requirements.txt`: Comprehensive dependency list with version specifications
- to memorize