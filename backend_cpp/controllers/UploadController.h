/**
 * @file UploadController.h
 * @brief File Upload API Controller
 */

#ifndef WONIUNOTE_CONTROLLERS_UPLOAD_CONTROLLER_H
#define WONIUNOTE_CONTROLLERS_UPLOAD_CONTROLLER_H

#include <drogon/HttpController.h>

namespace woniunote {
namespace controllers {

class UploadController : public drogon::HttpController<UploadController>
{
public:
    METHOD_LIST_BEGIN
    ADD_METHOD_TO(UploadController::uploadImage, "/api/upload/image", drogon::Post, "woniunote::AuthFilter");
    ADD_METHOD_TO(UploadController::uploadFile, "/api/upload/file", drogon::Post, "woniunote::AuthFilter");
    ADD_METHOD_TO(UploadController::uploadAvatar, "/api/upload/avatar", drogon::Post, "woniunote::AuthFilter");
    METHOD_LIST_END

    void uploadImage(const drogon::HttpRequestPtr& req,
                     std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void uploadFile(const drogon::HttpRequestPtr& req,
                    std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void uploadAvatar(const drogon::HttpRequestPtr& req,
                      std::function<void(const drogon::HttpResponsePtr&)>&& callback);

private:
    static std::string generateFilename(const std::string& originalName);
    static bool isAllowedImageType(drogon::FileType fileType);
    static bool isAllowedFileType(drogon::FileType fileType);
};

} // namespace controllers
} // namespace woniunote

#endif // WONIUNOTE_CONTROLLERS_UPLOAD_CONTROLLER_H
