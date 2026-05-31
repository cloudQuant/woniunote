/**
 * @file UploadController.cc
 * @brief File Upload API Controller Implementation
 */

#include "UploadController.h"
#include "core/config.h"
#include "core/logger.h"
#include "core/response.h"
#include "core/upload_safety.h"
#include <drogon/HttpResponse.h>
#include <drogon/utils/Utilities.h>
#include <algorithm>
#include <cctype>
#include <ctime>
#include <fstream>
#include <random>
#include <chrono>
#include <filesystem>

namespace fs = std::filesystem;
using namespace drogon;

namespace woniunote {
namespace controllers {

namespace {

// Build "YYYY/MM" using a thread-safe localtime_r (the shared static buffer of
// std::localtime is a data race under Drogon's multi-threaded event loop).
std::string yearMonthPath()
{
    auto now = std::chrono::system_clock::now();
    std::time_t timeT = std::chrono::system_clock::to_time_t(now);
    std::tm tmBuf{};
#if defined(_WIN32)
    localtime_s(&tmBuf, &timeT);
#else
    localtime_r(&timeT, &tmBuf);
#endif
    char buf[16];
    std::strftime(buf, sizeof(buf), "%Y/%m", &tmBuf);
    return std::string(buf);
}

// Verify finalPath resolves to a location inside baseDir. Defends against any
// residual traversal in the constructed path. Returns true when safe.
bool isWithinBase(const fs::path& baseDir, const fs::path& finalPath)
{
    std::error_code ec;
    fs::path base = fs::weakly_canonical(baseDir, ec);
    if (ec) base = baseDir.lexically_normal();
    fs::path target = fs::weakly_canonical(finalPath, ec);
    if (ec) target = finalPath.lexically_normal();

    auto baseStr = base.generic_string();
    auto targetStr = target.generic_string();
    if (!baseStr.empty() && baseStr.back() != '/') baseStr += '/';
    return targetStr.rfind(baseStr, 0) == 0;
}

}  // namespace

std::string UploadController::generateFilename(const std::string& originalName)
{
    std::string ext = sanitizeExtension(originalName);

    // Generate unique filename: timestamp + random
    auto now = std::chrono::system_clock::now();
    auto timestamp = std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()).count();

    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(1000, 9999);

    std::string name = std::to_string(timestamp) + "_" + std::to_string(dis(gen));
    if (!ext.empty()) {
        name += "." + ext;
    }
    return name;
}

bool UploadController::isAllowedImageType(drogon::FileType fileType)
{
    return fileType == drogon::FileType::FT_IMAGE;
}

bool UploadController::isAllowedFileType(drogon::FileType fileType)
{
    // Disallow images-as-files only matters for the dedicated image endpoint.
    // Here we accept documents/archives; the authoritative gate is the
    // extension allow-list applied by the caller.
    return fileType == drogon::FileType::FT_DOCUMENT ||
           fileType == drogon::FileType::FT_ARCHIVE ||
           fileType == drogon::FileType::FT_CUSTOM;
}

void UploadController::uploadImage(const HttpRequestPtr& req,
                                   std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::info("[Upload] Image upload request", {{"ip", req->getPeerAddr().toIp()}});
    auto& config = Config::instance();

    MultiPartParser fileParser;
    if (fileParser.parse(req) != 0) {
        Logger::warning("[Upload] Image upload failed: parse error");
        callback(Response::badRequest("解析文件失败"));
        return;
    }

    auto& files = fileParser.getFiles();
    if (files.empty()) {
        callback(Response::badRequest("未找到上传文件"));
        return;
    }

    auto& file = files[0];

    // Validate by sniffed type AND sanitized extension allow-list.
    std::string ext = sanitizeExtension(file.getFileName());
    if (!isAllowedImageType(file.getFileType()) ||
        !isExtAllowed(ext, config.getAllowedImageExts())) {
        Logger::warning("[Upload] Image upload failed: invalid type",
                        {{"filename", file.getFileName()}, {"ext", ext}});
        callback(Response::badRequest("不支持的图片格式"));
        return;
    }

    if (static_cast<int64_t>(file.fileLength()) > config.getMaxImageSize()) {
        callback(Response::badRequest("图片大小超过限制"));
        return;
    }

    std::string relativePath = "uploads/images/" + yearMonthPath();
    std::string uploadDir = config.getUploadPath() + "/" + relativePath;
    fs::create_directories(uploadDir);

    std::string filename = generateFilename(file.getFileName());
    fs::path fullPath = fs::path(uploadDir) / filename;

    // Final guard: ensure the resolved path stays under the upload root.
    if (!isWithinBase(config.getUploadPath(), fullPath)) {
        Logger::warning("[Upload] Rejected path outside upload root",
                        {{"path", fullPath.string()}});
        callback(Response::badRequest("非法的文件路径"));
        return;
    }

    file.saveAs(fullPath.string());

    std::string url = "/static/" + relativePath + "/" + filename;
    Logger::info("[Upload] Image uploaded", {{"filename", filename}, {"size", std::to_string(file.fileLength())}});

    Json::Value data;
    data["url"] = url;
    data["filename"] = filename;
    callback(Response::ok("上传成功", data));
}

void UploadController::uploadFile(const HttpRequestPtr& req,
                                  std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::info("[Upload] File upload request", {{"ip", req->getPeerAddr().toIp()}});
    auto& config = Config::instance();

    MultiPartParser fileParser;
    if (fileParser.parse(req) != 0) {
        Logger::warning("[Upload] File upload failed: parse error");
        callback(Response::badRequest("解析文件失败"));
        return;
    }

    auto& files = fileParser.getFiles();
    if (files.empty()) {
        callback(Response::badRequest("未找到上传文件"));
        return;
    }

    auto& file = files[0];

    // Authoritative gate: sanitized extension must be on the allow-list.
    std::string ext = sanitizeExtension(file.getFileName());
    if (!isExtAllowed(ext, config.getAllowedFileExts())) {
        Logger::warning("[Upload] File upload failed: extension not allowed",
                        {{"filename", file.getFileName()}, {"ext", ext}});
        callback(Response::badRequest("不支持的文件类型"));
        return;
    }

    if (static_cast<int64_t>(file.fileLength()) > config.getMaxFileSize()) {
        Logger::warning("[Upload] File upload failed: size exceeded", {{"size", std::to_string(file.fileLength())}});
        callback(Response::badRequest("文件大小超过限制"));
        return;
    }

    std::string relativePath = "uploads/files/" + yearMonthPath();
    std::string uploadDir = config.getUploadPath() + "/" + relativePath;
    fs::create_directories(uploadDir);

    std::string filename = generateFilename(file.getFileName());
    fs::path fullPath = fs::path(uploadDir) / filename;

    if (!isWithinBase(config.getUploadPath(), fullPath)) {
        Logger::warning("[Upload] Rejected path outside upload root",
                        {{"path", fullPath.string()}});
        callback(Response::badRequest("非法的文件路径"));
        return;
    }

    file.saveAs(fullPath.string());

    std::string url = "/static/" + relativePath + "/" + filename;
    Logger::info("[Upload] File uploaded", {{"filename", filename}, {"size", std::to_string(file.fileLength())}});

    Json::Value data;
    data["url"] = url;
    data["filename"] = filename;
    callback(Response::ok("上传成功", data));
}

void UploadController::uploadAvatar(const HttpRequestPtr& req,
                                    std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::info("[Upload] Avatar upload request", {{"userid", userId}});
    auto& config = Config::instance();

    MultiPartParser fileParser;
    if (fileParser.parse(req) != 0) {
        Logger::warning("[Upload] Avatar upload failed: parse error", {{"userid", userId}});
        callback(Response::badRequest("解析文件失败"));
        return;
    }

    auto& files = fileParser.getFiles();
    if (files.empty()) {
        callback(Response::badRequest("未找到上传文件"));
        return;
    }

    auto& file = files[0];

    std::string ext = sanitizeExtension(file.getFileName());
    if (!isAllowedImageType(file.getFileType()) ||
        !isExtAllowed(ext, config.getAllowedImageExts())) {
        Logger::warning("[Upload] Avatar upload failed: invalid type", {{"userid", userId}, {"ext", ext}});
        callback(Response::badRequest("不支持的图片格式"));
        return;
    }

    if (static_cast<int64_t>(file.fileLength()) > config.getMaxAvatarSize()) {
        Logger::warning("[Upload] Avatar upload failed: size exceeded", {{"userid", userId}, {"size", std::to_string(file.fileLength())}});
        callback(Response::badRequest("头像大小超过限制"));
        return;
    }

    std::string uploadDir = config.getUploadPath() + "/uploads/avatars";
    fs::create_directories(uploadDir);

    // Filename derives only from the numeric user id and a sanitized
    // extension, so user-controlled input can never inject path separators.
    if (ext.empty()) ext = "jpg";
    std::string filename = userId + "." + ext;
    fs::path fullPath = fs::path(uploadDir) / filename;

    if (!isWithinBase(config.getUploadPath(), fullPath)) {
        Logger::warning("[Upload] Rejected avatar path outside upload root",
                        {{"path", fullPath.string()}});
        callback(Response::badRequest("非法的文件路径"));
        return;
    }

    file.saveAs(fullPath.string());

    std::string url = "/static/uploads/avatars/" + filename;
    Logger::info("[Upload] Avatar uploaded", {{"userid", userId}, {"filename", filename}});

    Json::Value data;
    data["url"] = url;
    callback(Response::ok("上传成功", data));
}

} // namespace controllers
} // namespace woniunote
