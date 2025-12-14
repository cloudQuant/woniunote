/**
 * @file UEditorController.h
 * @brief UEditor Rich Text Editor API Controller
 */

#ifndef WONIUNOTE_CONTROLLERS_UEDITOR_CONTROLLER_H
#define WONIUNOTE_CONTROLLERS_UEDITOR_CONTROLLER_H

#include <drogon/HttpController.h>

namespace woniunote {
namespace controllers {

class UEditorController : public drogon::HttpController<UEditorController>
{
public:
    METHOD_LIST_BEGIN
    ADD_METHOD_TO(UEditorController::handler,
                  "/api/uedit",
                  drogon::Get, drogon::Post);
    ADD_METHOD_TO(UEditorController::serveUpload,
                  "/api/uploads/{filename}",
                  drogon::Get);
    METHOD_LIST_END

    void handler(const drogon::HttpRequestPtr& req,
                 std::function<void(const drogon::HttpResponsePtr&)>&& callback);
    void serveUpload(const drogon::HttpRequestPtr& req,
                     std::function<void(const drogon::HttpResponsePtr&)>&& callback,
                     const std::string& filename);

private:
    std::string getUploadDir();
    Json::Value getConfig();
    void handleUploadImage(const drogon::HttpRequestPtr& req,
                          std::function<void(const drogon::HttpResponsePtr&)>&& callback);
    void handleListImage(std::function<void(const drogon::HttpResponsePtr&)>&& callback);
    void handleUploadVideo(const drogon::HttpRequestPtr& req,
                          std::function<void(const drogon::HttpResponsePtr&)>&& callback);
    void handleUploadFile(const drogon::HttpRequestPtr& req,
                         std::function<void(const drogon::HttpResponsePtr&)>&& callback);
};

} // namespace controllers
} // namespace woniunote

#endif // WONIUNOTE_CONTROLLERS_UEDITOR_CONTROLLER_H
