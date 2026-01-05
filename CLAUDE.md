# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WoniuNote is a high-performance blog system with a **hybrid architecture**: the project contains two parallel backend implementations (C++ and Python), but the **C++ backend is the active development target**. The Python Flask backend is legacy code.

**Current branch:** `dev_cpp` (C++ development)
**Main branch:** `master`

### Architecture

```
[Frontend: Vue 3 + Vite + Element Plus]
           ↓ (API calls)
[Nginx] → Reverse proxy / static file serving
           ↓ (/api/*)
[C++ Backend: Drogon framework]
           ↓
[MySQL 8.0 + Redis]
```

## Development Commands

### Starting the Application

Use the provided scripts instead of manual commands:

```bash
# Development mode (frontend with hot-reload on :8888)
bash start_app.sh dev

# Production mode (frontend built + served by Nginx on :80/:443)
bash start_app.sh prod

# Stop all services
bash stop_app.sh

# Restart services
bash restart_app.sh [prod|dev]
```

### Backend (C++)

```bash
cd backend_cpp

# Build (uses build.sh which wraps CMake + vcpkg)
./build.sh

# Manual build
mkdir build && cd build
cmake .. -DCMAKE_TOOLCHAIN_FILE=~/vcpkg/scripts/buildsystems/vcpkg.cmake
cmake --build . --config Release -j8

# Run (after build)
cd build
./woniunote_backend  # Runs on port 5173
```

### Frontend (Vue 3)

```bash
cd frontend

# Install dependencies
npm install

# Development server (port 8888)
npm run dev

# Production build
npm run build
```

### Testing

The Python tests cover the legacy backend and integration testing:

```bash
# Run all tests with coverage (recommended)
python tests/run_all_tests.py

# Fast mode (skip slow/integration tests)
python tests/run_all_tests.py --fast

# Debug mode (verbose output)
python tests/run_all_tests.py --debug

# Sequential execution (no parallelization)
python tests/run_all_tests.py --sequential

# Direct pytest commands
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/ -v --cov=woniunote --cov-report=html
```

### Linting (Python - Legacy Backend)

Pre-commit hooks are configured. Install with:

```bash
pip install pre-commit
pre-commit install
```

Tools configured:
- **black**: Code formatting (line length: 100)
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

## Architecture Notes

### C++ Backend Structure (`backend_cpp/`)

- **main.cc**: Application entry point
- **core/**: Infrastructure modules
  - `config.h/cc`: Configuration loading from config.json
  - `database.h/cc`: Database connection utilities
  - `security.h/cc`: JWT token generation/validation, bcrypt password hashing
  - `logger.h/cc`: Logging utilities using spdlog
- **controllers/**: API endpoint handlers (Auth, Article, Comment, User, Admin, etc.)
- **models/**: Data models (User, Article, Comment, Favorite, Credit, MathTraining)
- **filters/**: Middleware (AuthFilter for JWT validation, AdminFilter for admin access, RateLimitFilter)
- **third_party/**: Contains bcrypt headers (bcrypt.h, bcrypt.cpp)

### Configuration

- `backend_cpp/config.json`: Development configuration (backend runs on port 5173)
- `backend_cpp/config.prod.json`: Production configuration
- Key config sections:
  - `listeners`: HTTP server binding (address/port)
  - `db_clients`: MySQL connection settings
  - `redis_clients`: Redis connection for caching
  - `custom_config`: JWT secrets, CORS origins, token expiration

### Frontend Structure (`frontend/`)

- **src/api/**: Axios API wrappers (communicate with backend on :5173)
- **src/components/**: Reusable Vue components
- **src/views/**: Page components (Home, ArticleDetail, Login, admin/, etc.)
- **src/stores/**: Pinia state management
- **src/router/**: Vue Router configuration

### Port Configuration

| Service | Port | Notes |
|---------|------|-------|
| C++ Backend | 5173 | Drogon HTTP server |
| Frontend (dev) | 8888 | Vite dev server |
| Frontend (prod) | 80/443 | Served by Nginx |

### Dependencies

**C++ Backend (via vcpkg):**
- drogon (web framework)
- jwt-cpp (JWT tokens)
- openssl (cryptography)
- jsoncpp (JSON parsing)
- hiredis (Redis client)
- libmariadb (MySQL client)
- spdlog (logging)

**Frontend (npm):**
- vue 3.4
- vite 5
- element-plus 2.5
- pinia (state management)
- vue-router
- axios

## Migration Context

The project is transitioning from Python Flask to C++ Drogon. When working on features:
1. Prioritize the C++ backend implementation
2. The Python backend (`woniunote/` directory) is maintained for reference but not actively developed
3. API endpoints should match between implementations for compatibility

## Database Setup

```sql
CREATE DATABASE woniunote CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'woniunote_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON woniunote.* TO 'woniunote_user'@'localhost';
FLUSH PRIVILEGES;
```

## Production Deployment

For production deployment on Ubuntu, use:
```bash
sudo bash scripts/setup_ubuntu.sh
```

This installs system dependencies, MySQL, Redis, Node.js, vcpkg, and compiles the C++ backend.
