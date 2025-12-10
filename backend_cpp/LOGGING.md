# WoniuNote C++ Backend Logging

## Overview
The C++ backend uses **spdlog** for high-performance, structured logging with both console and file output.

## Features
- **Async logging** with thread pool for minimal performance impact
- **Rotating file logs** (128MB per file, 30 files max ~30 days retention)
- **Dual output**: Console (INFO+) and File (DEBUG+)
- **Structured context** support with key-value pairs
- **Color-coded console** output for better readability

## Log Files
- **Location**: `backend_cpp/build/Release/logs/`
- **Main log**: `backend.log` - Application logs (DEBUG level)
- **Access log**: `access.log` - HTTP request logs (via Drogon plugin)

## Log Levels
- **DEBUG**: Detailed diagnostic information (file only)
- **INFO**: General informational messages
- **WARN**: Warning messages for potential issues
- **ERROR**: Error messages for failures

## Usage in Code

### Basic Logging
```cpp
#include "core/logger.h"

// Simple messages
Logger::info("Server started");
Logger::warning("Connection timeout");
Logger::error("Database connection failed");
Logger::debug("Processing request");
```

### Structured Logging with Context
```cpp
// With context map
Logger::info("[Auth] Login successful", {
    {"userid", std::to_string(userId)},
    {"username", username}
});

Logger::error("[Database] Query failed", {
    {"query", sql},
    {"error", e.what()}
});
```

## Log Format
- **Console**: `[HH:MM:SS] [LEVEL] message`
- **File**: `[YYYY-MM-DD HH:MM:SS.mmm] [LEVEL] message`

## Key Logging Points

### Authentication (AuthController)
- Registration attempts and results
- Login attempts (success/failure)
- Logout events
- Token validation failures

### Articles (ArticleController)
- Article list requests with pagination
- Article retrieval by ID
- Article creation/update/deletion
- Database query errors

### Database (database.cc)
- Client acquisition
- Connection failures
- Transaction errors

### Comments (CommentController)
- Comment list by article
- Comment creation
- Database errors

### Users (UserController)
- User profile retrieval
- Profile updates
- Password changes

### Upload (UploadController)
- Image upload requests
- File validation (type, size)
- Upload success/failure

### Favorites (FavoriteController)
- Favorite list requests
- Add/remove favorites
- Reactivate canceled favorites
- Check favorite status

### Credit (CreditController)
- Balance queries
- Credit history retrieval

### Todo (TodoController)
- Category CRUD operations
- Todo item CRUD operations
- Toggle done status

### Card (CardController)
- Card category operations
- Card CRUD operations
- Timer start/stop

### Admin (AdminController)
- System statistics
- User/Article/Comment management
- Delete operations (warning level)

### System (SystemController)
- Health checks
- Status checks
- Database connectivity

### Captcha (CaptchaController)
- Captcha generation
- Captcha verification

### Filters (AuthFilter, AdminFilter, RateLimitFilter)
- Authentication attempts
- Token validation
- Admin access control
- Rate limiting checks
- User identification

### Application Lifecycle (main.cc)
- Startup sequence
- Configuration loading
- Server initialization
- Shutdown sequence

## Configuration
Logging is configured in `config.json`:

```json
{
  "app": {
    "log": {
      "use_spdlog": true,
      "log_path": "./logs",
      "logfile_base_name": "drogon",
      "log_level": "DEBUG",
      "log_size_limit": 104857600,
      "max_files": 10,
      "use_local_time": true
    }
  },
  "plugins": [
    {
      "name": "drogon::plugin::AccessLogger",
      "config": {
        "use_spdlog": true,
        "log_path": "./logs",
        "log_file": "access.log"
      }
    }
  ]
}
```

## Initialization
Logger is initialized in `main.cc`:
```cpp
woniunote::Logger::init("logs");  // Creates logs directory if needed
```

## Performance
- Async logging minimizes blocking
- Thread pool handles I/O operations
- Automatic log rotation prevents disk space issues (128MB × 30 files = ~3.8GB max)
- Console output limited to INFO+ to reduce overhead
- Approximately 30 days of logs retained with daily rotation

## Debugging Tips
1. Check `backend.log` for application-level issues
2. Check `access.log` for HTTP request patterns
3. Use DEBUG level logs to trace request flow
4. Search for `[ERROR]` tags to find failures quickly
5. Context fields help correlate related log entries

## Example Log Output

### Startup
```
[2025-12-09 22:30:15.123] [info] === WoniuNote C++ Backend Starting ===
[2025-12-09 22:30:15.124] [info] Version: 2.0.0-cpp
[2025-12-09 22:30:15.125] [info] Loading configuration from config.json
[2025-12-09 22:30:15.130] [info] Configuration loaded successfully
[2025-12-09 22:30:15.135] [info] WoniuNote API v2.0.0 (C++) started successfully
[2025-12-09 22:30:15.136] [info] Server listening on configured ports
```

### Authentication
```
[2025-12-09 22:31:20.456] [info] [Auth] Login request received {"ip": "127.0.0.1"}
[2025-12-09 22:31:20.458] [debug] [Auth] Attempting login {"username": "test@example.com"}
[2025-12-09 22:31:20.462] [info] [Auth] Login successful {"userid": "123", "username": "test@example.com"}
```

### Article Operations
```
[2025-12-09 22:32:10.789] [debug] [Article] List request {"path": "/api/articles"}
[2025-12-09 22:32:10.790] [debug] [Article] Executing list query {"page": "1", "pageSize": "10", "type": "0"}
[2025-12-09 22:32:10.795] [debug] [Article] List returned {"total": "42", "count": "10"}
```

## Maintenance
- Logs automatically rotate when reaching 128MB
- Old logs are kept (up to 30 files, ~30 days)
- No manual cleanup required
- Maximum disk usage: ~3.8GB for all logs
- Oldest logs automatically deleted when limit reached
