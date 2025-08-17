# Woniunote - Modern Personal Blog System

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-0.1.4-orange.svg)](setup.py)

> A modern, high-performance personal blog system built with Python Flask framework, featuring rich functional modules and optimization features.

## 🌟 Features

- **Modern Architecture**: MVC design pattern, modular architecture, easy to maintain and extend
- **High Performance**: Integrated caching system, database optimization, asynchronous task processing
- **Security Protection**: Complete permission management, CSRF protection, input validation, secure sessions
- **User Experience**: Responsive design, intelligent caching, performance monitoring, user behavior analysis
- **Developer Friendly**: Complete testing framework, code quality checks, automated deployment support

## 🏗️ Architecture

```
woniunote/
├── 📁 woniunote/                 # Core application package
│   ├── 📁 controller/            # Controller layer (C in MVC)
│   ├── 📁 models/                # Data model layer (M in MVC)
│   ├── 📁 common/                # Common modules
│   ├── 📁 services/              # Business service layer
│   ├── 📁 template/              # Template files (V in MVC)
│   ├── 📁 resource/              # Static resources
│   ├── app.py                    # Main application file
│   ├── app_factory.py            # Application factory
│   └── __init__.py               # Package initialization
├── 📁 configs/                   # Configuration files
├── 📁 tests/                     # Test files
├── 📁 docs/                      # Documentation
├── requirements.txt               # Python dependencies
├── setup.py                      # Installation configuration
└── README.md                     # Project description
```

## 🚀 Core Features

### 📝 Content Management
- **Article System**: Support for original, reprinted, translated content
- **Rich Text Editor**: Integrated UEditor with image upload support
- **Categories & Tags**: Flexible article classification and tagging system
- **Draft Function**: Article draft saving and editing

### 👥 User System
- **User Registration**: Secure user registration and verification
- **Permission Management**: Multi-role access control (user, admin)
- **Personal Center**: User information management, avatar upload
- **Credit System**: User activity credit mechanism

### 💬 Interactive Features
- **Comment System**: Article comments and replies
- **Favorites**: User favorite management
- **Like System**: Content likes and recommendations

### 📊 Management Features
- **Content Review**: Article review and publication control
- **User Management**: User information viewing and management
- **System Monitoring**: Performance monitoring and log management
- **Data Statistics**: Access statistics and user behavior analysis

### 🎯 Special Features
- **Todo Items**: Personal task management
- **Card Center**: Information card display
- **Math Training**: Mathematics practice tools
- **File Upload**: Secure file upload and management

## 🛠️ Technology Stack

### Backend
- **Python 3.8+**: Core programming language
- **Flask 2.0+**: Web framework
- **SQLAlchemy**: ORM database operations
- **PyMySQL**: MySQL database driver
- **Redis**: Caching and session storage
- **Jinja2**: Template engine

### Frontend
- **HTML5/CSS3**: Page structure and styling
- **JavaScript**: Interactive functionality
- **Bootstrap**: Responsive UI framework
- **Vue.js**: Frontend framework
- **jQuery**: DOM manipulation and AJAX

### Database
- **MySQL**: Primary database
- **SQLite**: Development environment database
- **Redis**: Cache database

### Deployment & Operations
- **Gunicorn**: WSGI server
- **Nginx**: Reverse proxy
- **Docker**: Containerized deployment
- **Git**: Version control

## 📦 Installation & Deployment

### Requirements
- Python 3.8+
- MySQL 5.7+ or SQLite 3
- Redis 4.0+ (optional)
- Modern browser support

### Quick Start

#### 1. Clone Project
```bash
# Domestic users
git clone https://gitee.com/yunjinqi/woniunote.git

# International users
git clone https://github.com/cloudQuant/woniunote.git

cd woniunote
```

#### 2. Install Dependencies
```bash
# Install Python dependencies
pip install -r requirements.txt

# Or use conda
conda install --file requirements.txt
```

#### 3. Configure Database
```bash
# Copy configuration file
cp configs/user_password_config.yaml.example configs/user_password_config.yaml

# Edit configuration file
nano configs/user_password_config.yaml
```

Configuration example:
```yaml
# Database configuration
database:
  SQLALCHEMY_DATABASE_URI: mysql://username:password@localhost:3306/woniunote
  SQLALCHEMY_TRACK_MODIFICATIONS: false

# Security configuration
SECRET_KEY: 'your-secret-key-here'
WTF_CSRF_SECRET_KEY: 'your-csrf-key-here'
```

#### 4. Initialize Database
```bash
cd woniunote/woniunote
python common/create_database.py
```

#### 5. Start Application
```bash
# Development environment
python app.py

# Production environment
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Development Environment Configuration

#### Using SQLite (Recommended for development)
```yaml
database:
  SQLALCHEMY_DATABASE_URI: sqlite:///woniunote_dev.db
```

#### Using MySQL (Production environment)
```yaml
database:
  SQLALCHEMY_DATABASE_URI: mysql://user:pass@localhost:3306/woniunote
```

## 🧪 Testing

### Run Tests
```bash
# Install test dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install

# Run functional tests
pytest . -v --cov=woniunote --cov-report=html

# Run performance tests
locust -f tests/test_performance.py --host=http://localhost:5000
```

### Test Coverage
- Unit Tests: Core functional modules
- Integration Tests: API interfaces and database operations
- Performance Tests: Load and stress testing
- Security Tests: Permission and input validation

## 🔧 Configuration

### Environment Variables
```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
export DATABASE_URL=sqlite:///woniunote_dev.db
export SECRET_KEY=your-secret-key
```

### Configuration File Structure
- **configs/config.py**: Python configuration classes
- **configs/user_password_config.yaml**: Main configuration file
- **configs/development_config.yaml**: Development environment configuration

## 🚀 Performance Optimization

### Caching Strategy
- **Redis Cache**: Hot data caching
- **Memory Cache**: Fast access caching
- **Smart Cache**: Access pattern-based caching strategy

### Database Optimization
- **Connection Pool**: Database connection reuse
- **Query Optimization**: N+1 query problem solution
- **Index Optimization**: Database performance improvement

### Frontend Optimization
- **Static Resources**: CDN acceleration and compression
- **Lazy Loading**: Image and content lazy loading
- **Code Splitting**: JavaScript modularization

## 🔒 Security Features

### Authentication & Authorization
- **JWT Tokens**: Secure identity authentication
- **Permission Control**: Role-based access control
- **Session Management**: Secure session handling

### Data Protection
- **CSRF Protection**: Cross-site request forgery protection
- **XSS Protection**: Cross-site scripting attack protection
- **SQL Injection Protection**: Parameterized queries

### Input Validation
- **Data Sanitization**: Secure input data processing
- **File Upload**: Secure file upload validation
- **API Rate Limiting**: Prevent API abuse

## 📊 Monitoring & Logging

### System Monitoring
- **Performance Monitoring**: Response time and throughput
- **Resource Monitoring**: CPU, memory, disk usage
- **Error Monitoring**: Exception and error statistics

### Logging System
- **Structured Logging**: JSON format log output
- **Log Levels**: Configurable log levels
- **Log Rotation**: Automatic log file management

## 🌐 Deployment Guide

### Docker Deployment
```bash
# Build image
docker build -t woniunote .

# Run container
docker run -d -p 5000:5000 woniunote
```

### Production Environment Deployment
```bash
# Using Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 app:app

# Using Nginx reverse proxy
# Configure nginx.conf file
```

### Environment Configuration
- **Development**: Debug mode, SQLite database
- **Testing**: Test data, MySQL database
- **Production**: Production configuration, MySQL database

## 🤝 Contributing

### Development Process
1. Fork the project
2. Create a feature branch
3. Commit your code
4. Create a Pull Request

### Code Standards
- Follow PEP 8 Python code standards
- Add appropriate comments and documentation
- Write unit tests
- Ensure code quality

### Issue Reporting
- Use GitHub Issues to report problems
- Provide detailed error information and reproduction steps
- Label issue type and priority

## 📚 Documentation

- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Development Guide](docs/development.md)
- [Troubleshooting](TROUBLESHOOTING.md)

## 📄 License

This project is licensed under the [MIT License](LICENSE).

## 👨‍💻 Author

- **Author**: cloudQuant (云金杞)
- **Email**: yunjinqi@gmail.com
- **Website**: https://www.yunjinqi.top
- **GitHub**: https://github.com/cloudQuant

## 🙏 Acknowledgments

Thanks to all developers and users who have contributed to this project.

## 📞 Contact

- **Project Homepage**: https://github.com/cloudQuant/woniunote
- **Online Demo**: https://www.yunjinqi.top
- **Issue Reporting**: https://github.com/cloudQuant/woniunote/issues
- **Technical Discussion**: Welcome to submit Issues and Pull Requests

---

⭐ If this project helps you, please give it a star!
