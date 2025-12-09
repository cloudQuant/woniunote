# WoniuNote C++ Backend

High-performance C++ backend for WoniuNote using the [Drogon](https://github.com/drogonframework/drogon) web framework.

## Features

- 🚀 High-performance async HTTP server
- 🔐 JWT authentication with bcrypt password hashing
- 🗄️ MySQL database with async queries
- 📦 Redis caching and rate limiting
- 📁 File upload support
- 🔒 Admin role-based access control

## Requirements

- **CMake** 3.20+
- **C++ Compiler**: MSVC 2019+, GCC 10+, or Clang 13+
- **vcpkg** package manager
- **MySQL** 8.0+
- **Redis** 6.0+ (optional, for caching)

## Quick Start

### 1. Install vcpkg

```bash
# Clone vcpkg
git clone https://github.com/microsoft/vcpkg.git

# Bootstrap (Windows)
.\vcpkg\bootstrap-vcpkg.bat

# Bootstrap (Linux/macOS)
./vcpkg/bootstrap-vcpkg.sh

# Set environment variable
# Windows: set VCPKG_ROOT=C:\path\to\vcpkg
# Linux:   export VCPKG_ROOT=~/vcpkg
```

### 2. Build

**Windows:**
```cmd
cd backend_cpp
build.bat
```

**Linux/macOS:**
```bash
cd backend_cpp
chmod +x build.sh
./build.sh
```

**Manual Build:**
```bash
mkdir build && cd build
cmake .. -DCMAKE_TOOLCHAIN_FILE=$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake
cmake --build . --config Release
```

### 3. Configure

Edit `config.json` to set your environment:

```json
{
    "app": {
        "jwt_secret": "your-secret-key",
        "upload_path": "./uploads"
    },
    "db_clients": [{
        "host": "localhost",
        "port": 3306,
        "dbname": "woniunote",
        "user": "root",
        "password": "your-password"
    }],
    "redis_clients": [{
        "host": "127.0.0.1",
        "port": 6379
    }]
}
```

### 4. Run

```bash
./woniunote_backend
# Server starts at http://localhost:8000
```

## Project Structure

```
backend_cpp/
├── main.cc                 # Application entry point
├── config.json             # Runtime configuration
├── CMakeLists.txt          # Build configuration
├── vcpkg.json              # Dependencies manifest
├── core/                   # Core infrastructure
│   ├── config.h/cc         # Configuration loader
│   ├── database.h/cc       # Database utilities
│   ├── security.h/cc       # JWT & password hashing
│   └── logger.h/cc         # Logging utilities
├── models/                 # Database models
│   ├── User.h/cc
│   ├── Article.h/cc
│   └── ...
├── controllers/            # API endpoints
│   ├── AuthController.h/cc
│   ├── ArticleController.h/cc
│   └── ...
└── filters/                # Middleware
    ├── AuthFilter.h/cc
    ├── AdminFilter.h/cc
    └── RateLimitFilter.h/cc
```

## API Endpoints

| Controller | Endpoints | Auth |
|------------|-----------|------|
| Auth | register, login, refresh, me, logout | Mixed |
| User | getUser, updateProfile, changePassword | Auth |
| Article | list, get, create, update, delete, hot, types | Mixed |
| Comment | listByArticle, create, delete, vote | Mixed |
| Favorite | list, add, remove, check | Auth |
| Credit | balance, history | Auth |
| Todo | categories/items CRUD | Auth |
| Card | categories/cards CRUD, timer | Auth |
| Upload | image, file, avatar | Auth |
| Captcha | generate, verify | Public |
| Admin | stats, users, articles, comments | Admin |
| System | health, status, db | Mixed |

## Dependencies

Managed via vcpkg:
- **drogon** - Web framework
- **jwt-cpp** - JWT tokens
- **openssl** - Cryptography
- **jsoncpp** - JSON parsing
- **hiredis** - Redis client
- **libmysql** - MySQL client

## Performance

Expected performance improvements over Python FastAPI:
- 5-10x lower latency
- 3-5x higher throughput
- 50% less memory usage

## License

MIT License - See [LICENSE](../LICENSE) for details.
