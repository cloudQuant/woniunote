# Logging System Changelog

## 2025-12-09 - Enhanced Logging System

### Log Rotation Improvements
- **Increased file size**: 10MB → **128MB** per log file
- **Extended retention**: 5 files → **30 files** (~30 days of logs)
- **Total capacity**: ~500MB → **~3.8GB** maximum disk usage
- Applied to all log files: `backend.log`, `access.log`, `drogon.log`

### New Logging Coverage

#### CommentController
- `listByArticle`: Comment retrieval with count
- `create`: Comment creation with article/user tracking
- Error handling for database operations

#### UserController
- `getUser`: User profile retrieval
- `updateProfile`: Profile update tracking
- `changePassword`: Password change requests
- User not found scenarios

#### UploadController
- `uploadImage`: Image upload requests with IP tracking
- File validation failures (type, size)
- Successful uploads with filename and size
- Parse errors

### Enhanced Existing Logging

#### AuthController
- Added IP address tracking for login/register
- Detailed failure reasons (empty fields, wrong password, user exists)
- Success tracking with user ID and username

#### ArticleController
- Request path tracking
- Query parameter logging (page, pageSize, type)
- Result count tracking
- Article details (ID, headline)

#### Database
- Client acquisition tracking
- Connection name logging

#### AuthFilter
- Request path in authentication logs
- User ID tracking for authenticated requests

#### Main Application
- Startup banner with version
- Configuration loading steps
- Shutdown logging

### Configuration Updates

**config.json**:
```json
{
  "app": {
    "log": {
      "log_size_limit": 134217728,  // 128MB
      "max_files": 30
    }
  },
  "plugins": [{
    "name": "drogon::plugin::AccessLogger",
    "config": {
      "log_size_limit": 134217728,  // 128MB
      "max_files": 30
    }
  }]
}
```

**logger.h**:
```cpp
static inline constexpr std::size_t kRotateSizeBytes = 128 * 1024 * 1024; // 128MB
static inline constexpr std::size_t kRotateFiles = 30; // Keep 30 days of logs
```

### Log Format Examples

#### Authentication
```
[2025-12-09 22:30:15.123] [info] [Auth] Login request received {"ip": "127.0.0.1"}
[2025-12-09 22:30:15.125] [debug] [Auth] Attempting login {"username": "user@example.com"}
[2025-12-09 22:30:15.130] [info] [Auth] Login successful {"userid": "123", "username": "user@example.com"}
```

#### Comments
```
[2025-12-09 22:31:20.456] [debug] [Comment] List by article {"articleid": "42"}
[2025-12-09 22:31:20.460] [debug] [Comment] List returned {"count": "15"}
[2025-12-09 22:31:25.789] [info] [Comment] Create request {"userid": "123"}
[2025-12-09 22:31:25.795] [info] [Comment] Created {"commentid": "456", "articleid": "42", "userid": "123"}
```

#### User Operations
```
[2025-12-09 22:32:10.123] [debug] [User] Get user {"userid": "123"}
[2025-12-09 22:32:10.125] [debug] [User] Found {"userid": "123", "username": "user@example.com"}
[2025-12-09 22:32:15.456] [info] [User] Update profile {"userid": "123"}
[2025-12-09 22:32:15.460] [info] [User] Profile updated {"userid": "123"}
```

#### File Uploads
```
[2025-12-09 22:33:20.123] [info] [Upload] Image upload request {"ip": "127.0.0.1"}
[2025-12-09 22:33:20.125] [warning] [Upload] Image upload failed: invalid type {"filename": "document.pdf"}
[2025-12-09 22:33:25.456] [info] [Upload] Image uploaded {"filename": "1733772805456_1234.jpg", "size": "524288"}
```

### Benefits
1. **Extended History**: 30 days vs 5 days of logs
2. **Better Debugging**: More context in all operations
3. **Audit Trail**: Complete tracking of user actions
4. **Performance Monitoring**: Request/response tracking
5. **Security**: IP tracking for authentication
6. **Troubleshooting**: Detailed error messages with context

### Files Modified
- `core/logger.h` - Updated rotation constants
- `core/logger.cc` - No changes (uses header constants)
- `config.json` - Updated all log size limits and max files
- `controllers/AuthController.cc` - Enhanced auth logging
- `controllers/ArticleController.cc` - Enhanced article logging
- `controllers/CommentController.cc` - Added comment logging
- `controllers/UserController.cc` - Added user logging
- `controllers/UploadController.cc` - Added upload logging
- `core/database.cc` - Enhanced database logging
- `filters/AuthFilter.cc` - Enhanced filter logging
- `main.cc` - Enhanced startup/shutdown logging
- `LOGGING.md` - Updated documentation

### Build Status
✅ Successfully compiled with MSVC
✅ All lambda captures fixed
✅ No warnings or errors
