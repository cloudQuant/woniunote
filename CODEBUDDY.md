# CODEBUDDY.md

This file provides essential information for Terminal Assistant Agent instances working with the WoniuNote codebase.

## Project Overview

WoniuNote is a modern, feature-rich Flask-based personal blog system with advanced functionality including content management, user systems, flashcard learning, task management, and mathematical training. It's a production-ready application currently running at https://www.yunjinqi.top.

## Essential Development Commands

### Installation & Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install project package (REQUIRED for development)
pip install -e .

# Create configuration file (REQUIRED before first run)
cp configs/user_password_config.yaml.example configs/user_password_config.yaml
# Edit configs/user_password_config.yaml with your database and Redis settings

# Initialize database (first time only)
python scripts/init_db_direct.py
```

### Running the Application
```bash
# Development server (recommended)
python scripts/start_server.py

# Development server with options
python scripts/start_server.py --host 0.0.0.0 --port 5000 --debug
python scripts/start_server.py --test  # Use test database
python scripts/start_server.py --http  # Force HTTP instead of HTTPS

# Direct application start
cd woniunote && python app.py

# Production server
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 app:app
```

### Testing (100% Pass Rate)
```bash
# Install test dependencies (included in requirements.txt)
playwright install

# Run all tests with coverage
pytest . -v --cov=woniunote --cov-report=html --cov-report=term

# Run specific test categories
python scripts/run_tests.py --unit-only      # Unit tests only
python scripts/run_tests.py --cards-only     # Card system tests
python scripts/run_tests.py --todos-only     # Todo system tests
python scripts/run_tests.py --model-only     # Model validation tests

# Run single test file
pytest tests/unit/test_common_utils.py -v

# Run tests with markers
pytest -m "not slow" -v     # Skip slow tests
pytest -m "not browser" -v  # Skip browser tests
pytest -m unit -v          # Run only unit tests

# Performance testing
locust -f tests/test_performance.py --host=http://localhost:5000
```

### Database Operations
```bash
# Initialize database tables
python scripts/init_db_direct.py

# Reset specific tables
python scripts/reset_card_tables.py
python scripts/init_card_tables.py
python scripts/init_todo_tables.py

# Database optimization
python scripts/optimize_database_indexes.py
```

### Code Quality
```bash
# Install pre-commit hooks
pip install pre-commit && pre-commit install

# Run code formatting and linting
black --line-length=100 woniunote
isort --profile black woniunote
flake8 woniunote --max-line-length=100
mypy woniunote
bandit -r woniunote -ll

# Run all pre-commit checks
pre-commit run --all-files
```

## High-Level Architecture

### Core Architecture Pattern
WoniuNote follows a **modular MVC architecture** with unified common modules:

- **Controller Layer** (`woniunote/controller/`): Flask blueprints handling HTTP requests
- **Module Layer** (`woniunote/module/`): Business logic and data operations
- **Model Layer** (`woniunote/models/` + `woniunote/common/create_database.py`): SQLAlchemy models
- **Common Layer** (`woniunote/common/`): Unified infrastructure modules

### Key Architectural Components

#### 1. Unified Common Modules (Critical)
The `woniunote/common/` directory contains **10 unified modules** that eliminate code duplication:

- **`unified_cache.py`**: Multi-layer caching (Redis primary, memory fallback)
- **`unified_security.py`**: Security management, JWT auth, CSRF protection
- **`unified_monitoring.py`**: Performance monitoring and metrics collection
- **`unified_database_optimizer.py`**: Database optimization and query monitoring
- **`unified_logging.py`**: Structured logging with trace IDs
- **`unified_session.py`**: Enhanced session management
- **`unified_config.py`**: Configuration management
- **`unified_validator.py`**: Input validation and sanitization
- **`unified_utils.py`**: Common utilities and helpers
- **`unified_error_handler.py`**: Error handling and recovery

#### 2. Application Factory Pattern
- **`app_factory.py`**: Modular app creation with environment-based configuration
- **`app.py`**: Main Flask application entry point with comprehensive middleware

#### 3. Blueprint Architecture
10 specialized blueprints in `woniunote/controller/`:
- `index.py`: Homepage and content display
- `user.py`: Authentication and user management
- `article.py`: Article CRUD operations
- `admin.py`: Administrative functions
- `ucenter.py`: User center and profiles
- `card_center.py`: Flashcard learning system
- `todo_center.py`: Task management system
- `comment.py`: Comment system
- `favorite.py`: Bookmarks and favorites
- `ueditor.py`: Rich text editor integration

#### 4. Data Layer Architecture
- **Core Models**: `woniunote/common/create_database.py` (User, Article, Comment)
- **Extended Models**: `woniunote/models/card.py`, `woniunote/models/todo.py`
- **Business Logic**: `woniunote/module/` (articles.py, users.py, comments.py, etc.)

### Technology Stack
- **Backend**: Flask 2.x, SQLAlchemy ORM, Flask-Session
- **Database**: MySQL 8.0+ (production), SQLite (development/testing)
- **Caching**: Redis 4.5+ with intelligent memory fallback
- **Frontend**: HTML5, CSS3, JavaScript ES6+, Bootstrap 4, UEditor
- **Testing**: pytest ecosystem with 300+ test cases (100% pass rate)
- **Security**: Flask-WTF, custom rate limiting, JWT authentication

## Critical Configuration Requirements

### 1. Database Configuration (REQUIRED)
```yaml
# configs/user_password_config.yaml (create from .example)
database:
  SQLALCHEMY_DATABASE_URI: mysql://username:password@localhost:3306/woniunote
  # OR for development:
  # SQLALCHEMY_DATABASE_URI: sqlite:///woniunote_dev.db
  SQLALCHEMY_TRACK_MODIFICATIONS: false

SECRET_KEY: 'your-secret-key-here-change-in-production'
WTF_CSRF_SECRET_KEY: 'your-csrf-key-here'
```

### 2. Redis Configuration (Optional but Recommended)
```yaml
# configs/user_password_config.yaml
redis:
  REDIS_URL: redis://localhost:6379/0
```

### 3. Environment Variables
```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
export TESTING=1  # For test environment
```

## Development Patterns & Best Practices

### 1. Database Session Management
```python
from woniunote.common.database import db

# Use context managers for database operations
with db.session.begin():
    db.session.add(model_instance)
    # Auto-commits on success, rolls back on exception
```

### 2. Caching Pattern
```python
from woniunote.common.unified_cache import cached

@cached(key_prefix='article', timeout=300)
def get_article(article_id):
    # Expensive operation
    return result
```

### 3. Logging Pattern
```python
from woniunote.common.unified_logging import get_simple_logger

logger = get_simple_logger('module_name')
logger.info("Operation completed", extra={'trace_id': g.request_id})
```

### 4. Authentication Pattern
```python
from woniunote.common.unified_session import is_user_logged_in, get_current_user

if not is_user_logged_in():
    return redirect(url_for('user.login'))
user = get_current_user()
```

### 5. Error Handling Pattern
```python
try:
    result = perform_operation()
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    db.session.rollback()
    return jsonify({'success': False, 'message': 'Database error'}), 500
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    return jsonify({'success': False, 'message': 'System error'}), 500
```

## Testing Architecture

### Test Structure
- **Unit Tests**: `tests/unit/` - 300+ test cases with 100% pass rate
- **Test Configuration**: `tests/conftest.py` - Fixtures and test setup
- **Test Utilities**: `tests/utils/` - Test helpers and launchers
- **Coverage**: 85%+ code coverage with comprehensive reporting

### Test Categories
- **Unit Tests**: Individual function and class testing
- **Integration Tests**: Database operations and API testing
- **Controller Tests**: Flask route and blueprint testing
- **Model Tests**: SQLAlchemy model validation
- **Performance Tests**: Load testing with Locust
- **Security Tests**: Authentication and input validation

### Test Markers
```bash
pytest -m unit          # Unit tests only
pytest -m "not slow"    # Skip slow tests
pytest -m "not browser" # Skip browser tests
pytest -m integration   # Integration tests only
```

## Security Considerations

### Built-in Security Features
- **CSRF Protection**: Flask-WTF integration
- **Rate Limiting**: Custom rate limiter with whitelist support
- **Input Validation**: Unified validator for all inputs
- **JWT Authentication**: API authentication system
- **Session Security**: Enhanced session management
- **SQL Injection Protection**: Parameterized queries via SQLAlchemy

### Security Headers
The application automatically sets comprehensive security headers including CSP, XSS protection, and content type validation.

## Performance Optimization

### Caching Strategy
- **Multi-layer Caching**: Redis primary with memory fallback
- **Intelligent Cache**: Access pattern-based caching
- **Cache Invalidation**: Automatic cache management

### Database Optimization
- **Connection Pooling**: SQLAlchemy connection management
- **Query Optimization**: Automated slow query detection
- **Index Management**: Database index optimization scripts

### Monitoring
- **Performance Metrics**: Built-in performance monitoring
- **Resource Monitoring**: Memory and CPU usage tracking
- **Error Tracking**: Comprehensive error logging and recovery

## Important Files to Understand

### Core Application
- `woniunote/app.py`: Main Flask application with middleware
- `woniunote/app_factory.py`: Application factory pattern
- `scripts/start_server.py`: Development server launcher

### Configuration
- `configs/config.py`: Flask configuration classes
- `configs/user_password_config.yaml`: Sensitive configuration (create from .example)
- `woniunote/common/database.py`: Database connection management

### Business Logic
- `woniunote/module/articles.py`: Article operations with logging
- `woniunote/module/users.py`: User operations with authentication
- `woniunote/common/create_database.py`: Core model definitions

### Infrastructure
- `woniunote/common/unified_*.py`: Unified infrastructure modules
- `woniunote/common/utils.py`: Core utility functions
- `tests/conftest.py`: Test configuration and fixtures

## Development Notes

### Language & Documentation
- Mixed Chinese/English codebase with extensive Chinese comments
- UEditor integration requires specific CSP policies for Chinese content
- Comprehensive documentation in both languages

### Special Features
- **Card Center**: Spaced repetition flashcard learning system
- **Todo Center**: Task management with categories and scheduling
- **Mathematical Training**: Special module for math exercises
- **Rich Text Editor**: UEditor integration for Chinese content

### Common Issues
- **Package Installation**: Always run `pip install -e .` for development
- **Configuration**: Must create `user_password_config.yaml` before first run
- **Database**: Initialize database with `python scripts/init_db_direct.py`
- **SSL Development**: Use provided OpenSSL commands for HTTPS testing

## Claude Code Rules Integration

Based on the CLAUDE.md file, this project has specific requirements:
- Use the unified common modules for all infrastructure needs
- Follow the established blueprint pattern for new controllers
- Implement comprehensive error handling and logging
- Write tests for all new functionality
- Use the application factory pattern for configuration
- Follow the existing security patterns and validation

## Performance & Monitoring

The application includes built-in monitoring accessible through the admin panel with real-time metrics for:
- System resource usage (CPU, memory, disk)
- Database performance and query optimization
- Cache hit rates and performance
- User activity and behavior analysis
- Error rates and recovery statistics

This monitoring system provides insights for optimization and troubleshooting.