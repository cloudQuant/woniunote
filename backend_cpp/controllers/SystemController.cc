/**
 * @file SystemController.cc
 * @brief System API Controller Implementation
 */

#include "SystemController.h"
#include "core/database.h"
#include "core/logger.h"
#include "core/response.h"
#include <drogon/HttpResponse.h>

using namespace drogon;

namespace woniunote {
namespace controllers {

void SystemController::health(const HttpRequestPtr& req,
                              std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::debug("[System] Health check");
    Json::Value data;
    data["status"] = "healthy";
    data["version"] = "2.0.0-cpp";
    callback(Response::success(data));
}

void SystemController::status(const HttpRequestPtr& req,
                              std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::debug("[System] Status check");
    Json::Value data;
    data["status"] = "running";
    data["version"] = "2.0.0-cpp";
    data["framework"] = "Drogon";
    data["threads"] = static_cast<int>(app().getThreadNum());
    callback(Response::success(data));
}

void SystemController::dbStatus(const HttpRequestPtr& req,
                                std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::debug("[System] DB status check");
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT 1 AS ok",
        [callback](const orm::Result& result) {
            Json::Value data;
            data["database"] = "connected";
            data["type"] = "mysql";
            callback(Response::success(data));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[System] Database connection failed: " + std::string(e.base().what()));
            Json::Value data;
            data["database"] = "disconnected";
            data["error"] = e.base().what();
            callback(Response::make(500, "数据库连接失败", data,
                                    drogon::k500InternalServerError));
        }
    );
}

} // namespace controllers
} // namespace woniunote
