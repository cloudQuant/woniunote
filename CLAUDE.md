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

# Install project package (for development)
pip install -U --no-build-isolation .

# Create configuration file (REQUIRED before first run)
cp configs/user_password_config.yaml.example configs/user_password_config.yaml
# Edit configs/user_password_config.yaml with your database and Redis settings

# Initialize database (first time only)
python scripts/init_db_direct.py

# Create SSL certificates for local HTTPS testing (optional)
cd configs
openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365
```

### Running the Application
```bash
# Development server (HTTP, default port 5001)
python scripts/start_server.py

# Development server with options
python scripts/start_server.py --host 0.0.0.0 --port 5000 --debug
python scripts/start_server.py --test  # Use test database
python scripts/start_server.py --http  # Force HTTP instead of HTTPS

# Production server
cd woniunote
gunicorn -w 3 -b 0.0.0.0:8888 app:app

# Background production server
nohup gunicorn -w 3 -b 0.0.0.0:8888 --log-level debug app:app > woniunote_run.log 2>&1 &
```

### Testing
```bash
# Install test dependencies (included in requirements.txt)
playwright install

# Run all tests with coverage
pytest . -v --cov=woniunote --cov-report=html -n auto

# Run specific test categories
python scripts/run_tests.py --unit-only      # Unit tests only
python scripts/run_tests.py --cards-only     # Card system tests only
python scripts/run_tests.py --todos-only     # Todo system tests only
python scripts/run_tests.py --model-only     # Model validation only
python scripts/run_tests.py --direct         # Direct test mode

# Run a single test file
pytest tests/unit/test_common_utils.py -v

# Run tests matching pattern
pytest -k "test_user" -v  # Run all tests with 'test_user' in name

# Run tests with markers
pytest -m "not slow"     # Skip slow tests
pytest -m "not browser"  # Skip browser tests
pytest -m unit          # Run only unit tests

# Run performance testing
locust -f tests/test_performance.py --host=http://localhost:5000

# Quick test runner (custom script)
python scripts/run_tests.py
```

### Database Operations
```bash
# Initialize database tables
python scripts/init_db_direct.py

# Reset specific tables
python scripts/reset_card_tables.py
python scripts/init_card_tables.py
python scripts/init_todo_tables.py

# Database optimization and maintenance
python scripts/optimize_database_indexes.py   # Optimize database indexes
python scripts/migrate_password_field.py      # Password field migration
```

### Code Quality and Linting
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run code formatting and linting
black --line-length=100 woniunote            # Code formatting
isort --profile black woniunote              # Import sorting
flake8 woniunote --max-line-length=100       # Linting with docstrings
mypy woniunote                               # Type checking
bandit -r woniunote -ll                      # Security checking
safety check                                 # Dependency vulnerability checking

# Run all pre-commit checks manually
pre-commit run --all-files
```

### Development Utilities
```bash
# Code cleanup and optimization
python scripts/cleanup_unused_imports.py      # Remove unused imports
python scripts/optimize_frontend_resources.py # Frontend optimization
python scripts/verify_optimizations.py        # Verify optimizations

# Environment configuration for different modes
export WONIUNOTE_TEST_MODE=true    # Test mode
export TESTING=1                   # Testing environment
export DEBUG=true                  # Debug mode
export FLASK_ENV=testing          # Flask environment
```

## Architecture Overview

### Project Structure
```
woniunote/
├── woniunote/                    # Main package directory
│   ├── app.py                   # Flask application entry point (delegates to app_factory)
│   ├── app_factory.py          # Application factory with environment configuration
│   ├── controller/              # Flask blueprints (URL routing layer)
│   │   ├── index.py            # Homepage routes and pagination
│   │   ├── article.py          # Article CRUD operations
│   │   ├── user.py             # User authentication and session management
│   │   ├── admin.py            # Admin panel and management functions
│   │   ├── ucenter.py          # User center and profile management
│   │   ├── ueditor.py          # Rich text editor integration
│   │   ├── comment.py          # Comment system
│   │   ├── favorite.py         # Bookmarks and favorites
│   │   ├── card_center.py      # Flashcard learning system
│   │   └── todo_center.py      # Task management system
│   ├── module/                 # Data access layer (business logic)
│   │   ├── articles.py         # Article data operations with logging
│   │   ├── users.py            # User data operations with logging
│   │   ├── comments.py         # Comment data operations
│   │   ├── credits.py          # Credit/points system
│   │   └── favorites.py        # Favorites data operations
│   ├── models/                 # SQLAlchemy model definitions
│   │   ├── card.py             # Card and CardCategory models
│   │   └── todo.py             # Item and Category models for todos
│   ├── common/                 # Shared utilities and infrastructure
│   │   ├── database.py         # Database configuration and connection
│   │   ├── create_database.py  # Core model definitions (User, Article, Comment)
│   │   ├── utils.py            # Utility functions and helpers
│   │   ├── simple_logger.py    # Structured logging system
│   │   ├── cache_utils.py      # Multi-layer caching system
│   │   ├── security_enhanced.py# Advanced security features
│   │   ├── performance_enhanced.py # Performance monitoring
│   │   ├── session_manager.py  # Session management utilities
│   │   ├── password_utils.py   # Password hashing and validation
│   │   ├── error_handler.py    # Error handling and recovery
│   │   └── monitoring.py       # System monitoring and metrics
│   ├── template/               # Jinja2 HTML templates
│   ├── resource/               # Static assets (CSS, JS, images)
│   └── services/               # Service layer for complex operations
├── configs/                    # Configuration files
│   ├── config.py              # Main Flask configuration
│   ├── user_password_config.yaml # Sensitive configuration (not in VCS)
│   └── development_config.yaml   # Development environment config
├── tests/                      # Comprehensive test suite
│   ├── unit/                  # Unit tests for individual components
│   ├── broken/                # Tests for error scenarios
│   ├── utils/                 # Test utilities and helpers
│   └── configs/               # Test configuration files
├── scripts/                    # Development and deployment scripts
├── docs/                       # Documentation and SQL schemas
└── tools/                      # Additional development tools
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
- **App Factory Pattern**: Uses `app_factory.py` with environment-based configuration and dependency injection
- **Modular Blueprint Architecture**: 10 specialized blueprints (index, user, article, admin, ucenter, ueditor, comment, favorite, card, todo)
- **Multi-layer Caching**: Redis primary with intelligent memory fallback via unified cache strategy
- **Advanced Security**: Rate limiting, CSRF protection, input validation, JWT authentication, API security enhancements
- **Performance Monitoring**: Real-time metrics collection, performance tracking, memory optimization, database monitoring
- **Database Optimization**: Advanced query optimization, connection pooling, automatic recovery, slow query detection
- **Error Recovery**: Circuit breakers, graceful degradation, automatic reconnection for external services
- **Structured Logging**: Comprehensive logging with trace IDs for request correlation and debugging
- **Resource Management**: Memory monitoring, session management, cleanup automation

### Configuration Management
- **Main Configuration**: `woniunote/configs/config.py` - Flask app configuration classes
- **Sensitive Configuration**: `configs/user_password_config.yaml` (create from `.example`) - Database, Redis, email credentials
  - REQUIRED: Copy `user_password_config.yaml.example` to `user_password_config.yaml` before first run
  - Configure database URI format: `mysql://username:password@host:port/database` or `sqlite:///path/to/database.db`
  - Redis is optional but recommended for production (fallback to memory cache if unavailable)
- **Database Configuration**: `common/database.py` - Database connection and model definitions
- **Article Types**: Dynamic configuration via YAML files for content categorization
- **Environment Support**: Development, testing, production configurations with override capabilities
- **Dynamic Configuration**: Runtime configuration updates for non-critical settings

### Testing Architecture
- **Unit Tests**: `/tests/unit/` - Test individual functions and classes with mocking
- **Integration Tests**: Database operations, external service integration, and API testing
- **Broken Tests**: `/tests/broken/` - Error scenario testing and exception handling
- **Comprehensive Coverage**: Multi-layered test suites with 85%+ code coverage
- **Performance Tests**: Load testing with Locust framework for scalability validation
- **Browser Tests**: Playwright for end-to-end UI testing and user workflow validation
- **Test Utilities**: `/tests/utils/` - Shared test helpers and fixtures
- **Configuration Testing**: Separate test configurations for isolated test environments

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
Comprehensive error handling with recovery:
```python
try:
    # Operation
    result = perform_operation()
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    db.session.rollback()
    # Attempt recovery or return graceful error
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    return jsonify({'success': False, 'message': 'System error'}), 500
```

### Important Files to Understand

#### Core Application Files
- `woniunote/app.py`: Main Flask application entry point with comprehensive route definitions and middleware
- `woniunote/app_factory.py`: App factory pattern implementation with environment-specific configuration
- `scripts/start_server.py`: Application startup script with development server configuration

#### Database and Models
- `woniunote/common/database.py`: Database connection management, configuration, and core setup
- `woniunote/common/create_database.py`: Core model definitions (User, Article, Comment) with SQLAlchemy
- `woniunote/models/card.py`: Card and CardCategory models for flashcard learning system
- `woniunote/models/todo.py`: Item and Category models for task management system

#### Business Logic Layer
- `woniunote/module/articles.py`: Article operations with comprehensive logging and trace management
- `woniunote/module/users.py`: User operations with authentication and credit system integration
- `woniunote/module/comments.py`: Comment system data operations
- `woniunote/module/credits.py`: Credit/points system for user engagement

#### Core Infrastructure
- `woniunote/common/utils.py`: Core utility functions, validation, and helper methods
- `woniunote/common/simple_logger.py`: Structured logging system with trace ID support
- `woniunote/common/cache_utils.py`: Multi-layer caching with Redis primary and memory fallback
- `woniunote/common/security_enhanced.py`: Advanced security features, rate limiting, JWT authentication
- `woniunote/common/performance_enhanced.py`: Performance monitoring, metrics collection, optimization
- `woniunote/common/session_manager.py`: Enhanced session management with security features
- `woniunote/common/error_handler.py`: Error handling and recovery mechanisms

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