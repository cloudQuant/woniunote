/**
 * @file SystemController.h
 * @brief System API Controller
 * 
 * Provides system health and status endpoints.
 */

#ifndef WONIUNOTE_CONTROLLERS_SYSTEM_CONTROLLER_H
#define WONIUNOTE_CONTROLLERS_SYSTEM_CONTROLLER_H

#include <drogon/HttpController.h>

namespace woniunote {
namespace controllers {

class SystemController : public drogon::HttpController<SystemController>
{
public:
    METHOD_LIST_BEGIN
    ADD_METHOD_TO(SystemController::health, "/api/system/health", drogon::Get);
    ADD_METHOD_TO(SystemController::status, "/api/system/status", drogon::Get, "woniunote::AdminFilter");
    ADD_METHOD_TO(SystemController::dbStatus, "/api/system/db", drogon::Get, "woniunote::AdminFilter");
    METHOD_LIST_END

    void health(const drogon::HttpRequestPtr& req,
                std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void status(const drogon::HttpRequestPtr& req,
                std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void dbStatus(const drogon::HttpRequestPtr& req,
                  std::function<void(const drogon::HttpResponsePtr&)>&& callback);
};

} // namespace controllers
} // namespace woniunote

#endif // WONIUNOTE_CONTROLLERS_SYSTEM_CONTROLLER_H
