# WoniuNote C++ Backend (Drogon)

A high-performance C++ backend for WoniuNote using the Drogon framework.

## Prerequisites

- CMake 3.20+
- C++17 compiler (GCC 8+, Clang 7+, MSVC 2019+)
- vcpkg package manager
- MySQL 8.0+
- Redis 6.0+

## Dependencies (via vcpkg)

```bash
vcpkg install drogon jwt-cpp bcrypt openssl jsoncpp
```

## Build

```bash
mkdir build && cd build
cmake .. -DCMAKE_TOOLCHAIN_FILE=[path to vcpkg]/scripts/buildsystems/vcpkg.cmake
cmake --build . --config Release
```

## Run

```bash
./woniunote_backend
```

The server will start on port 8080 by default (configurable in `config.json`).

## Project Structure

```
backend_cpp/
├── CMakeLists.txt          # Build configuration
├── config.json             # Drogon runtime configuration
├── main.cc                 # Application entry point
├── core/                   # Core utilities
│   ├── config.h/cc         # Configuration loader
│   ├── database.h/cc       # Database wrapper
│   ├── security.h/cc       # JWT & bcrypt utilities
│   └── logger.h/cc         # Logging utilities
├── controllers/            # HTTP controllers
├── filters/                # HTTP filters (middleware)
├── models/                 # ORM models (generated)
└── tests/                  # Unit tests
```

## API Documentation

See the Python backend documentation for API reference.
All endpoints maintain the same interface for frontend compatibility.
