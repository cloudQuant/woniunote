/**
 * @file UEditorController.cc
 * @brief UEditor Rich Text Editor API Controller Implementation
 */

#include "UEditorController.h"
#include "core/logger.h"
#include <drogon/HttpResponse.h>
#include <filesystem>
#include <fstream>
#include <chrono>
#include <random>
#include <algorithm>

namespace fs = std::filesystem;
using namespace drogon;

namespace woniunote {
namespace controllers {

// Allowed file extensions
static const std::vector<std::string> IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"};
static const std::vector<std::string> VIDEO_EXTENSIONS = {".flv", ".swf", ".mkv", ".avi", ".rm", ".rmvb", 
    ".mpeg", ".mpg", ".ogg", ".ogv", ".mov", ".wmv", ".mp4", ".webm", ".mp3", ".wav", ".mid"};
static const std::vector<std::string> FILE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp",
    ".flv", ".swf", ".mkv", ".avi", ".rm", ".rmvb", ".mpeg", ".mpg", ".ogg", ".ogv", ".mov", ".wmv", 
    ".mp4", ".webm", ".mp3", ".wav", ".mid", ".rar", ".zip", ".tar", ".gz", ".7z", ".bz2", ".cab", ".iso",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf", ".txt", ".md", ".xml"};

std::string UEditorController::getUploadDir()
{
    static std::string cachedPath;
    static bool initialized = false;
    
    if (initialized) {
        return cachedPath;
    }

    fs::path cwd = fs::current_path();
    std::vector<fs::path> candidates = {
        // 优先使用 backend_cpp 内的 uploads 目录
        cwd / ".." / "uploads",
        cwd / "uploads",
        // 兼容旧的 backend 目录
        cwd / ".." / ".." / "backend" / "uploads",
        cwd / ".." / "backend" / "uploads",
        "/Users/yunjinqi/Documents/woniunote/backend_cpp/uploads",
        "/Users/yunjinqi/Documents/woniunote/backend/uploads"
    };

    for (const auto& candidate : candidates) {
        if (fs::exists(candidate) && fs::is_directory(candidate)) {
            cachedPath = fs::canonical(candidate).string();
            initialized = true;
            Logger::info("[UEditor] Upload dir found: " + cachedPath);
            return cachedPath;
        }
    }

    // Create default uploads directory
    cachedPath = (cwd / "uploads").string();
    fs::create_directories(cachedPath);
    initialized = true;
    Logger::info("[UEditor] Created upload dir: " + cachedPath);
    return cachedPath;
}

Json::Value UEditorController::getConfig()
{
    Json::Value config;
    
    config["imageActionName"] = "uploadimage";
    config["imageFieldName"] = "upfile";
    config["imageMaxSize"] = 10485760;
    config["imageCompressEnable"] = true;
    config["imageCompressBorder"] = 1600;
    config["imageInsertAlign"] = "none";
    config["imageUrlPrefix"] = "";
    config["imagePathFormat"] = "/uploads/{yyyy}{mm}{dd}/{time}{rand:6}";
    
    Json::Value imageAllowFiles(Json::arrayValue);
    for (const auto& ext : IMAGE_EXTENSIONS) {
        imageAllowFiles.append(ext);
    }
    config["imageAllowFiles"] = imageAllowFiles;

    config["scrawlActionName"] = "uploadscrawl";
    config["scrawlFieldName"] = "upfile";
    config["scrawlMaxSize"] = 2048000;
    config["scrawlUrlPrefix"] = "";
    config["scrawlInsertAlign"] = "none";

    config["videoActionName"] = "uploadvideo";
    config["videoFieldName"] = "upfile";
    config["videoMaxSize"] = 102400000;
    config["videoUrlPrefix"] = "";
    
    Json::Value videoAllowFiles(Json::arrayValue);
    for (const auto& ext : VIDEO_EXTENSIONS) {
        videoAllowFiles.append(ext);
    }
    config["videoAllowFiles"] = videoAllowFiles;

    config["fileActionName"] = "uploadfile";
    config["fileFieldName"] = "upfile";
    config["fileMaxSize"] = 51200000;
    config["fileUrlPrefix"] = "";
    
    Json::Value fileAllowFiles(Json::arrayValue);
    for (const auto& ext : FILE_EXTENSIONS) {
        fileAllowFiles.append(ext);
    }
    config["fileAllowFiles"] = fileAllowFiles;

    config["imageManagerActionName"] = "listimage";
    config["imageManagerListPath"] = "/uploads/";
    config["imageManagerListSize"] = 20;
    config["imageManagerUrlPrefix"] = "";
    config["imageManagerInsertAlign"] = "none";
    config["imageManagerAllowFiles"] = imageAllowFiles;

    config["fileManagerActionName"] = "listfile";
    config["fileManagerListPath"] = "/uploads/";
    config["fileManagerListSize"] = 20;
    config["fileManagerUrlPrefix"] = "";
    config["fileManagerAllowFiles"] = fileAllowFiles;

    return config;
}

static std::string generateFilename(const std::string& prefix, const std::string& suffix)
{
    auto now = std::chrono::system_clock::now();
    auto time = std::chrono::system_clock::to_time_t(now);
    std::tm* tm = std::localtime(&time);
    
    char timestamp[32];
    std::strftime(timestamp, sizeof(timestamp), "%Y%m%d_%H%M%S", tm);
    
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(100000, 999999);
    int randomNum = dis(gen);
    
    return prefix + timestamp + "_" + std::to_string(randomNum) + suffix;
}

static std::string getFileSuffix(const std::string& filename)
{
    size_t pos = filename.rfind('.');
    if (pos != std::string::npos) {
        std::string suffix = filename.substr(pos);
        std::transform(suffix.begin(), suffix.end(), suffix.begin(), ::tolower);
        return suffix;
    }
    return "";
}

static bool isAllowedExtension(const std::string& suffix, const std::vector<std::string>& allowed)
{
    return std::find(allowed.begin(), allowed.end(), suffix) != allowed.end();
}

void UEditorController::handler(const HttpRequestPtr& req,
                                std::function<void(const HttpResponsePtr&)>&& callback)
{
    std::string action = req->getParameter("action");
    Logger::info("[UEditor] Request", {{"action", action}});

    if (action == "config") {
        auto resp = HttpResponse::newHttpJsonResponse(getConfig());
        callback(resp);
        return;
    }

    if (action == "uploadimage") {
        handleUploadImage(req, std::move(callback));
        return;
    }

    if (action == "listimage") {
        handleListImage(std::move(callback));
        return;
    }

    if (action == "uploadvideo") {
        handleUploadVideo(req, std::move(callback));
        return;
    }

    if (action == "uploadfile") {
        handleUploadFile(req, std::move(callback));
        return;
    }

    if (action == "uploadscrawl") {
        handleUploadImage(req, std::move(callback));
        return;
    }

    // Unknown action
    Json::Value ret;
    ret["state"] = "FAIL";
    ret["message"] = "Unknown action: " + action;
    callback(HttpResponse::newHttpJsonResponse(ret));
}

void UEditorController::handleUploadImage(const HttpRequestPtr& req,
                                          std::function<void(const HttpResponsePtr&)>&& callback)
{
    MultiPartParser fileParser;
    if (fileParser.parse(req) != 0) {
        Json::Value ret;
        ret["state"] = "FAIL";
        ret["message"] = "Failed to parse multipart data";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }

    auto& files = fileParser.getFiles();
    if (files.empty()) {
        Json::Value ret;
        ret["state"] = "FAIL";
        ret["message"] = "No file uploaded";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }

    const auto& file = files[0];
    std::string originalName = file.getFileName();
    std::string suffix = getFileSuffix(originalName);

    if (!isAllowedExtension(suffix, IMAGE_EXTENSIONS)) {
        Json::Value ret;
        ret["state"] = "FAIL";
        ret["message"] = "Invalid file type";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }

    std::string newFilename = generateFilename("", suffix);
    std::string uploadDir = getUploadDir();
    std::string savePath = uploadDir + "/" + newFilename;

    try {
        file.saveAs(savePath);
        Logger::info("[UEditor] Image uploaded: " + newFilename);

        Json::Value ret;
        ret["state"] = "SUCCESS";
        ret["url"] = "/api/uploads/" + newFilename;
        ret["title"] = originalName;
        ret["original"] = originalName;
        callback(HttpResponse::newHttpJsonResponse(ret));
    } catch (const std::exception& e) {
        Logger::error("[UEditor] Upload failed: " + std::string(e.what()));
        Json::Value ret;
        ret["state"] = "FAIL";
        ret["message"] = e.what();
        callback(HttpResponse::newHttpJsonResponse(ret));
    }
}

void UEditorController::handleListImage(std::function<void(const HttpResponsePtr&)>&& callback)
{
    std::string uploadDir = getUploadDir();
    Json::Value imageList(Json::arrayValue);

    try {
        if (fs::exists(uploadDir)) {
            for (const auto& entry : fs::directory_iterator(uploadDir)) {
                if (entry.is_regular_file()) {
                    std::string filename = entry.path().filename().string();
                    std::string suffix = getFileSuffix(filename);
                    if (isAllowedExtension(suffix, IMAGE_EXTENSIONS)) {
                        Json::Value item;
                        item["url"] = "/api/uploads/" + filename;
                        imageList.append(item);
                    }
                }
            }
        }

        Json::Value ret;
        ret["state"] = "SUCCESS";
        ret["list"] = imageList;
        ret["start"] = 0;
        ret["total"] = static_cast<int>(imageList.size());
        callback(HttpResponse::newHttpJsonResponse(ret));
    } catch (const std::exception& e) {
        Logger::error("[UEditor] List images failed: " + std::string(e.what()));
        Json::Value ret;
        ret["state"] = "FAIL";
        ret["message"] = e.what();
        callback(HttpResponse::newHttpJsonResponse(ret));
    }
}

void UEditorController::handleUploadVideo(const HttpRequestPtr& req,
                                          std::function<void(const HttpResponsePtr&)>&& callback)
{
    MultiPartParser fileParser;
    if (fileParser.parse(req) != 0) {
        Json::Value ret;
        ret["state"] = "FAIL";
        ret["message"] = "Failed to parse multipart data";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }

    auto& files = fileParser.getFiles();
    if (files.empty()) {
        Json::Value ret;
        ret["state"] = "FAIL";
        ret["message"] = "No file uploaded";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }

    const auto& file = files[0];
    std::string originalName = file.getFileName();
    std::string suffix = getFileSuffix(originalName);

    if (!isAllowedExtension(suffix, VIDEO_EXTENSIONS)) {
        Json::Value ret;
        ret["state"] = "FAIL";
        ret["message"] = "Invalid video type";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }

    std::string newFilename = generateFilename("video_", suffix);
    std::string uploadDir = getUploadDir();
    std::string savePath = uploadDir + "/" + newFilename;

    try {
        file.saveAs(savePath);
        Logger::info("[UEditor] Video uploaded: " + newFilename);

        Json::Value ret;
        ret["state"] = "SUCCESS";
        ret["url"] = "/api/uploads/" + newFilename;
        ret["title"] = originalName;
        ret["original"] = originalName;
        callback(HttpResponse::newHttpJsonResponse(ret));
    } catch (const std::exception& e) {
        Logger::error("[UEditor] Video upload failed: " + std::string(e.what()));
        Json::Value ret;
        ret["state"] = "FAIL";
        ret["message"] = e.what();
        callback(HttpResponse::newHttpJsonResponse(ret));
    }
}

void UEditorController::handleUploadFile(const HttpRequestPtr& req,
                                         std::function<void(const HttpResponsePtr&)>&& callback)
{
    MultiPartParser fileParser;
    if (fileParser.parse(req) != 0) {
        Json::Value ret;
        ret["state"] = "FAIL";
        ret["message"] = "Failed to parse multipart data";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }

    auto& files = fileParser.getFiles();
    if (files.empty()) {
        Json::Value ret;
        ret["state"] = "FAIL";
        ret["message"] = "No file uploaded";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }

    const auto& file = files[0];
    std::string originalName = file.getFileName();
    std::string suffix = getFileSuffix(originalName);

    if (!isAllowedExtension(suffix, FILE_EXTENSIONS)) {
        Json::Value ret;
        ret["state"] = "FAIL";
        ret["message"] = "Invalid file type";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }

    std::string newFilename = generateFilename("file_", suffix);
    std::string uploadDir = getUploadDir();
    std::string savePath = uploadDir + "/" + newFilename;

    try {
        file.saveAs(savePath);
        Logger::info("[UEditor] File uploaded: " + newFilename);

        Json::Value ret;
        ret["state"] = "SUCCESS";
        ret["url"] = "/api/uploads/" + newFilename;
        ret["title"] = originalName;
        ret["original"] = originalName;

        // Special handling for PDF files
        if (suffix == ".pdf") {
            ret["fileType"] = "pdf";
            ret["pdfUrl"] = "/api/uploads/" + newFilename;
            ret["html"] = "<p class=\"pdf-viewer-placeholder\" data-pdf-url=\"/api/uploads/" + newFilename + 
                "\" data-type=\"pdf\" style=\"background:#f5f5f5;padding:20px;border:1px dashed #ccc;"
                "border-radius:4px;text-align:center;margin:10px 0;\">"
                "📄 PDF文档: " + originalName + "<br/><small style=\"color:#999;\">文档将在发布后以PDF查看器形式显示</small></p>";
        }

        callback(HttpResponse::newHttpJsonResponse(ret));
    } catch (const std::exception& e) {
        Logger::error("[UEditor] File upload failed: " + std::string(e.what()));
        Json::Value ret;
        ret["state"] = "FAIL";
        ret["message"] = e.what();
        callback(HttpResponse::newHttpJsonResponse(ret));
    }
}

void UEditorController::serveUpload(const HttpRequestPtr& req,
                                    std::function<void(const HttpResponsePtr&)>&& callback,
                                    const std::string& filename)
{
    std::string uploadDir = getUploadDir();
    std::string filePath = uploadDir + "/" + filename;

    Logger::info("[serveUpload] Serving file: " + filePath);

    if (!fs::exists(filePath)) {
        Logger::error("[serveUpload] File not found: " + filePath);
        auto resp = HttpResponse::newNotFoundResponse();
        callback(resp);
        return;
    }

    auto resp = HttpResponse::newFileResponse(filePath);

    // 根据文件扩展名设置 Content-Type
    std::string ext = fs::path(filePath).extension().string();
    std::string contentType = "application/octet-stream";

    if (ext == ".pdf") {
        contentType = "application/pdf";
    } else if (ext == ".jpg" || ext == ".jpeg") {
        contentType = "image/jpeg";
    } else if (ext == ".png") {
        contentType = "image/png";
    } else if (ext == ".gif") {
        contentType = "image/gif";
    } else if (ext == ".svg") {
        contentType = "image/svg+xml";
    } else if (ext == ".webp") {
        contentType = "image/webp";
    }

    resp->addHeader("Content-Type", contentType);

    // 添加 CORS 头，允许前端访问文件
    auto origin = req->getHeader("Origin");
    if (!origin.empty()) {
        resp->addHeader("Access-Control-Allow-Origin", origin);
        resp->addHeader("Access-Control-Allow-Credentials", "true");
    } else {
        // 如果没有 Origin 头，允许所有源（用于同源请求）
        resp->addHeader("Access-Control-Allow-Origin", "*");
    }

    // 添加缓存头
    resp->addHeader("Cache-Control", "public, max-age=31536000");

    Logger::info("[serveUpload] Serving file with Content-Type: " + contentType);
    callback(resp);
}

} // namespace controllers
} // namespace woniunote
