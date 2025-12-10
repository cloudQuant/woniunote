/**
 * @file UploadController.cc
 * @brief File Upload API Controller Implementation
 */

#include "UploadController.h"
#include "core/config.h"
#include "core/logger.h"
#include <drogon/HttpResponse.h>
#include <drogon/utils/Utilities.h>
#include <fstream>
#include <random>
#include <chrono>
#include <filesystem>

namespace fs = std::filesystem;
using namespace drogon;

namespace woniunote {
namespace controllers {

// Allowed image file types using Drogon's FileType enum
static const std::set<drogon::FileType> ALLOWED_IMAGE_TYPES = {
    drogon::FileType::FT_IMAGE
};

// For file uploads, we'll be more permissive
static const std::set<drogon::FileType> ALLOWED_FILE_TYPES = {
    drogon::FileType::FT_DOCUMENT,
    drogon::FileType::FT_ARCHIVE,
    drogon::FileType::FT_CUSTOM
};

std::string UploadController::generateFilename(const std::string& originalName)
{
    // Get extension from original name
    std::string ext;
    auto dotPos = originalName.rfind('.');
    if (dotPos != std::string::npos) {
        ext = originalName.substr(dotPos);
    }
    
    // Generate unique filename: timestamp + random
    auto now = std::chrono::system_clock::now();
    auto timestamp = std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()).count();
    
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(1000, 9999);
    
    return std::to_string(timestamp) + "_" + std::to_string(dis(gen)) + ext;
}

bool UploadController::isAllowedImageType(drogon::FileType fileType)
{
    return fileType == drogon::FileType::FT_IMAGE;
}

bool UploadController::isAllowedFileType(drogon::FileType fileType)
{
    return ALLOWED_FILE_TYPES.count(fileType) > 0 || fileType == drogon::FileType::FT_DOCUMENT;
}

void UploadController::uploadImage(const HttpRequestPtr& req,
                                   std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::info("[Upload] Image upload request", {{"ip", req->getPeerAddr().toIp()}});
    auto& config = Config::instance();
    
    MultiPartParser fileParser;
    if (fileParser.parse(req) != 0) {
        Logger::warning("[Upload] Image upload failed: parse error");
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "解析文件失败";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }
    
    auto& files = fileParser.getFiles();
    if (files.empty()) {
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "未找到上传文件";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }
    
    auto& file = files[0];
    
    // Check file type
    if (!isAllowedImageType(file.getFileType())) {
        Logger::warning("[Upload] Image upload failed: invalid type", {{"filename", file.getFileName()}});
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "不支持的图片格式";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }
    
    // Check file size (max 5MB)
    if (file.fileLength() > 5 * 1024 * 1024) {
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "图片大小不能超过5MB";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }
    
    // Generate path: uploads/images/YYYY/MM/filename
    auto now = std::chrono::system_clock::now();
    auto timeT = std::chrono::system_clock::to_time_t(now);
    std::tm tm = *std::localtime(&timeT);
    
    std::ostringstream pathStream;
    pathStream << "uploads/images/" 
               << std::put_time(&tm, "%Y/%m");
    std::string relativePath = pathStream.str();
    
    std::string uploadDir = config.getUploadPath() + "/" + relativePath;
    fs::create_directories(uploadDir);
    
    std::string filename = generateFilename(file.getFileName());
    std::string fullPath = uploadDir + "/" + filename;
    
    // Save file
    file.saveAs(fullPath);
    
    // Return URL
    std::string url = "/static/" + relativePath + "/" + filename;
    
    Logger::info("[Upload] Image uploaded", {{"filename", filename}, {"size", std::to_string(file.fileLength())}});
    
    Json::Value ret;
    ret["code"] = 200;
    ret["message"] = "上传成功";
    ret["data"]["url"] = url;
    ret["data"]["filename"] = filename;
    callback(HttpResponse::newHttpJsonResponse(ret));
}

void UploadController::uploadFile(const HttpRequestPtr& req,
                                  std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::info("[Upload] File upload request", {{"ip", req->getPeerAddr().toIp()}});
    auto& config = Config::instance();
    
    MultiPartParser fileParser;
    if (fileParser.parse(req) != 0) {
        Logger::warning("[Upload] File upload failed: parse error");
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "解析文件失败";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }
    
    auto& files = fileParser.getFiles();
    if (files.empty()) {
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "未找到上传文件";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }
    
    auto& file = files[0];
    
    // Check file size (max 50MB)
    if (file.fileLength() > 50 * 1024 * 1024) {
        Logger::warning("[Upload] File upload failed: size exceeded", {{"size", std::to_string(file.fileLength())}});
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "文件大小不能超过50MB";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }
    
    // Generate path
    auto now = std::chrono::system_clock::now();
    auto timeT = std::chrono::system_clock::to_time_t(now);
    std::tm tm = *std::localtime(&timeT);
    
    std::ostringstream pathStream;
    pathStream << "uploads/files/" 
               << std::put_time(&tm, "%Y/%m");
    std::string relativePath = pathStream.str();
    
    std::string uploadDir = config.getUploadPath() + "/" + relativePath;
    fs::create_directories(uploadDir);
    
    std::string filename = generateFilename(file.getFileName());
    std::string fullPath = uploadDir + "/" + filename;
    
    file.saveAs(fullPath);
    
    std::string url = "/static/" + relativePath + "/" + filename;
    
    Logger::info("[Upload] File uploaded", {{"filename", filename}, {"size", std::to_string(file.fileLength())}});
    
    Json::Value ret;
    ret["code"] = 200;
    ret["message"] = "上传成功";
    ret["data"]["url"] = url;
    ret["data"]["filename"] = filename;
    callback(HttpResponse::newHttpJsonResponse(ret));
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
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "解析文件失败";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }
    
    auto& files = fileParser.getFiles();
    if (files.empty()) {
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "未找到上传文件";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }
    
    auto& file = files[0];
    
    if (!isAllowedImageType(file.getFileType())) {
        Logger::warning("[Upload] Avatar upload failed: invalid type", {{"userid", userId}});
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "不支持的图片格式";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }
    
    // Max 2MB for avatars
    if (file.fileLength() > 2 * 1024 * 1024) {
        Logger::warning("[Upload] Avatar upload failed: size exceeded", {{"userid", userId}, {"size", std::to_string(file.fileLength())}});
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "头像大小不能超过2MB";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }
    
    std::string uploadDir = config.getUploadPath() + "/uploads/avatars";
    fs::create_directories(uploadDir);
    
    // Use user ID as filename for easy replacement
    std::string ext;
    auto dotPos = file.getFileName().rfind('.');
    if (dotPos != std::string::npos) {
        ext = file.getFileName().substr(dotPos);
    } else {
        ext = ".jpg";
    }
    
    std::string filename = userId + ext;
    std::string fullPath = uploadDir + "/" + filename;
    
    file.saveAs(fullPath);
    
    std::string url = "/static/uploads/avatars/" + filename;
    
    Logger::info("[Upload] Avatar uploaded", {{"userid", userId}, {"filename", filename}});
    
    Json::Value ret;
    ret["code"] = 200;
    ret["message"] = "上传成功";
    ret["data"]["url"] = url;
    callback(HttpResponse::newHttpJsonResponse(ret));
}

} // namespace controllers
} // namespace woniunote
