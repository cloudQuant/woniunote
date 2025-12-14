/**
 * @file ThumbController.cc
 * @brief Thumbnail resources API Controller implementation
 */

#include "ThumbController.h"
#include "core/logger.h"

#include <drogon/HttpResponse.h>

#include <filesystem>
#include <vector>

namespace fs = std::filesystem;
using namespace drogon;

namespace woniunote {
namespace controllers {

// Resolve thumbnail root directory.
// 目标目录与 Python 版保持一致：项目根目录下 backend/resource/thumb
static fs::path getThumbRoot()
{
    static fs::path cachedPath;
    static bool initialized = false;
    
    if (initialized) {
        return cachedPath;
    }
    
    try {
        fs::path cwd = fs::current_path();
        
        // 候选路径列表
        std::vector<fs::path> candidates = {
            // 优先使用 backend_cpp 内的资源目录
            cwd / ".." / "resource" / "thumb",
            cwd / "resource" / "thumb",
            // 兼容旧的 backend 目录（迁移期间）
            cwd / ".." / ".." / "backend" / "resource" / "thumb",
            cwd / ".." / "backend" / "resource" / "thumb",
            cwd / "backend" / "resource" / "thumb",
            // 绝对路径备选（开发环境）
            "/Users/yunjinqi/Documents/woniunote/backend_cpp/resource/thumb",
            "/Users/yunjinqi/Documents/woniunote/backend/resource/thumb"
        };
        
        Logger::info("[Thumb] Searching for thumb root, cwd: " + cwd.string());
        
        for (const auto& candidate : candidates) {
            if (fs::exists(candidate) && fs::is_directory(candidate)) {
                cachedPath = fs::canonical(candidate);
                initialized = true;
                Logger::info("[Thumb] Root directory found", {{"path", cachedPath.string()}});
                return cachedPath;
            }
        }

        // 如果都不存在，返回第一种路径
        cachedPath = fs::weakly_canonical(candidates[0]);
        initialized = true;
        Logger::warning("[Thumb] Root directory not found, using default", {{"path", cachedPath.string()}});
        return cachedPath;
    } catch (const std::exception &e) {
        Logger::error("[Thumb] Failed to resolve thumb root", {{"error", e.what()}});
        cachedPath = fs::current_path();
        initialized = true;
        return cachedPath;
    }
}

void ThumbController::getThumb(const HttpRequestPtr &req,
                               std::function<void(const HttpResponsePtr &)> &&callback,
                               const std::string &filename)
{
    auto root = getThumbRoot();
    Logger::info("[Thumb] Request", {{"filename", filename}, {"root", root.string()}});

    // 简单安全校验，禁止路径穿越
    if (filename.find("..") != std::string::npos ||
        filename.find('/') != std::string::npos ||
        filename.find('\\') != std::string::npos) {
        Logger::warning("[Thumb] Invalid filename", {{"filename", filename}});
        auto resp = HttpResponse::newHttpResponse();
        resp->setStatusCode(k400BadRequest);
        resp->setContentTypeCode(CT_TEXT_PLAIN);
        resp->setBody("Invalid thumbnail filename");
        callback(resp);
        return;
    }

    fs::path filePath = root / filename;

    if (fs::exists(filePath) && fs::is_regular_file(filePath)) {
        auto resp = HttpResponse::newFileResponse(filePath.string());
        resp->setStatusCode(k200OK);
        resp->setContentTypeCode(CT_IMAGE_PNG);
        callback(resp);
        return;
    }

    // 回退：使用 1.png 作为默认缩略图
    fs::path fallback = root / "1.png";
    if (fs::exists(fallback) && fs::is_regular_file(fallback)) {
        Logger::debug("[Thumb] Fallback to 1.png", {{"requested", filename}});
        auto resp = HttpResponse::newFileResponse(fallback.string());
        resp->setStatusCode(k200OK);
        resp->setContentTypeCode(CT_IMAGE_PNG);
        callback(resp);
        return;
    }

    Logger::warning("[Thumb] Thumbnail not found", {{"filename", filename}, {"root", root.string()}});
    auto resp = HttpResponse::newHttpResponse();
    resp->setStatusCode(k404NotFound);
    resp->setContentTypeCode(CT_TEXT_PLAIN);
    resp->setBody("Thumbnail not found");
    callback(resp);
}

} // namespace controllers
} // namespace woniunote
