# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WoniuNote is a full-featured Flask-based blog and content management system. It's a production-ready web application currently running at https://www.yunjinqi.top, serving as a personal blog platform with features including article management, user authentication, comment system, flashcard learning (card center), todo management, and mathematical training modules.

## Development Commands

### Installation and Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install project package (for development)
pip install -U --no-build-isolation .

# Initialize database (first time only)
python scripts/init_db_direct.py

# Create SSL certificates for local HTTPS testing
cd configs
openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365
```

### Running the Application
```bash
# Development server (HTTP, default port 5001)
python scripts/start_server.py

# Development server with options
python scripts/start_server.py --host 0.0.0.0 --port 5000 --debug

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
│   ├── app.py                   # Flask application entry point
│   ├── controller/              # Flask blueprints (URL routing)
│   │   ├── index.py            # Homepage routes
│   │   ├── article.py          # Article management
│   │   ├── user.py             # User authentication
│   │   ├── admin.py            # Admin panel
│   │   ├── card_center.py      # Flashcard system
│   │   └── todo_center.py      # Todo management
│   ├── module/                 # Data access layer
│   │   ├── articles.py         # Article operations
│   │   ├── users.py            # User operations
│   │   └── cards.py            # Card operations
│   ├── common/                 # Shared utilities
│   │   ├── database.py         # Database configuration
│   │   ├── utils.py            # Helper functions
│   │   ├── cache_utils.py      # Caching system
│   │   ├── security_enhanced.py# Security features
│   │   └── performance_enhanced.py # Performance monitoring
│   ├── models/                 # SQLAlchemy model definitions
│   ├── template/               # Jinja2 HTML templates
│   └── resource/               # Static assets (CSS, JS, images)
├── configs/                    # Configuration files
├── tests/                      # Test suite
├── scripts/                    # Development scripts
└── docs/                       # Documentation
```

### Technology Stack
- **Backend**: Flask with SQLAlchemy ORM
- **Database**: MySQL (production), SQLite (testing)
- **Caching**: Redis
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap, Vue.js
- **Rich Text**: UEditor (integrated Chinese editor)
- **Testing**: pytest with comprehensive coverage
- **Deployment**: Gunicorn WSGI server

### Key Features
- **App Factory Pattern**: Uses `app_factory.py` with environment-based configuration
- **Modular Blueprint Architecture**: 10 blueprints (index, user, article, admin, ucenter, ueditor, comment, favorite, card, todo)
- **Multi-layer Caching**: Redis-based caching with memory fallback via cache_utils module
- **Security Enhancements**: Rate limiting, CSRF protection, input validation, enhanced security modules
- **Performance Monitoring**: Built-in metrics collection, performance tracking, memory optimization
- **Advanced Database Optimization**: Query optimization, connection pooling, automatic reconnection
- **CI/CD Pipeline**: GitHub Actions with automated testing, code quality checks, security scanning

### Configuration Management
- Main config: `woniunote/configs/config.py`
- User credentials: `configs/user_password_config.yaml` (create from example)
- Database settings configured in `common/database.py`
- Environment-specific overrides supported

### Testing Architecture
- **Unit Tests**: `/tests/unit/` - Test individual functions and classes
- **Functional Tests**: `/tests/functional/` - Test feature workflows
- **Integration Tests**: Database and external service integration
- **Performance Tests**: Load testing with Locust
- **Browser Tests**: Playwright for UI testing

### Development Notes
- The project uses Chinese comments and documentation extensively
- UEditor rich text editor requires specific CSP and iframe permissions
- SSL certificates are required for HTTPS (use provided OpenSSL command for local development)
- Database initialization scripts handle table creation and sample data
- Performance monitoring is built-in and can be accessed through admin panel

### Code Quality Standards
- Functions should be documented with docstrings
- Use decorator pattern for cross-cutting concerns (login_required, db_error_handler)
- Large functions should be decomposed into smaller helper functions
- Follow the existing naming conventions and code organization patterns

### Important Files to Understand
- `woniunote/app.py`: Main Flask application entry point (delegates to app_factory)
- `woniunote/app_factory.py`: App factory pattern implementation with environment configuration
- `woniunote/common/database.py`: Database connection, model configuration, and optimization
- `woniunote/common/utils.py`: Core utility functions used throughout the application
- `woniunote/common/cache_utils.py`: Multi-layer caching system with Redis and memory fallback
- `woniunote/common/security_enhanced.py`: Security features and rate limiting
- `woniunote/common/performance_enhanced.py`: Performance monitoring and optimization
- `tests/conftest.py`: Test configuration and fixtures
- `.pre-commit-config.yaml`: Code quality tools configuration
- `.github/workflows/ci.yml`: CI/CD pipeline configuration