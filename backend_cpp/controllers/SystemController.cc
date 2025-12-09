/**
 * @file SystemController.cc
 * @brief System API Controller Implementation
 */

#include "SystemController.h"
#include "core/database.h"
#include "core/logger.h"
#include <drogon/HttpResponse.h>

using namespace drogon;

namespace woniunote {
namespace controllers {

void SystemController::health(const HttpRequestPtr& req,
                              std::function<void(const HttpResponsePtr&)>&& callback)
{
    Json::Value ret;
    ret["code"] = 200;
    ret["message"] = "success";
    
    Json::Value data;
    data["status"] = "healthy";
    data["version"] = "2.0.0-cpp";
    ret["data"] = data;

    callback(HttpResponse::newHttpJsonResponse(ret));
}

void SystemController::status(const HttpRequestPtr& req,
                              std::function<void(const HttpResponsePtr&)>&& callback)
{
    Json::Value ret;
    ret["code"] = 200;
    ret["message"] = "success";
    
    Json::Value data;
    data["status"] = "running";
    data["version"] = "2.0.0-cpp";
    data["framework"] = "Drogon";
    data["threads"] = static_cast<int>(app().getThreadNum());
    
    ret["data"] = data;
    callback(HttpResponse::newHttpJsonResponse(ret));
}

void SystemController::dbStatus(const HttpRequestPtr& req,
                                std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto dbClient = Database::getClient();
    
    dbClient->execSqlAsync(
        "SELECT 1 AS ok",
        [callback](const orm::Result& result) {
            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "success";
            
            Json::Value data;
            data["database"] = "connected";
            data["type"] = "mysql";
            ret["data"] = data;
            
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库连接失败";
            
            Json::Value data;
            data["database"] = "disconnected";
            data["error"] = e.base().what();
            ret["data"] = data;
            
            auto resp = HttpResponse::newHttpJsonResponse(ret);
            resp->setStatusCode(k500InternalServerError);
            callback(resp);
        }
    );
}

} // namespace controllers
} // namespace woniunote
