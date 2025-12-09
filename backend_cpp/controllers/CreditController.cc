/**
 * @file CreditController.cc
 * @brief Credit API Controller Implementation
 */

#include "CreditController.h"
#include "core/database.h"
#include "core/logger.h"
#include "models/Credit.h"
#include <drogon/HttpResponse.h>

using namespace drogon;

namespace woniunote {
namespace controllers {

void CreditController::getBalance(const HttpRequestPtr& req,
                                  std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT credit FROM users WHERE userid = ?",
        [callback](const orm::Result& result) {
            if (result.size() == 0) {
                Json::Value ret;
                ret["code"] = 404;
                ret["message"] = "用户不存在";
                callback(HttpResponse::newHttpJsonResponse(ret));
                return;
            }

            int credit = result[0]["credit"].as<int>();
            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "success";
            ret["data"]["balance"] = credit;
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        std::stoll(userId)
    );
}

void CreditController::getHistory(const HttpRequestPtr& req,
                                  std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    int page = 1, pageSize = 20;

    if (req->getParameter("page").length() > 0) {
        page = std::stoi(req->getParameter("page"));
    }
    if (req->getParameter("page_size").length() > 0) {
        pageSize = std::stoi(req->getParameter("page_size"));
    }

    int offset = (page - 1) * pageSize;
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT * FROM credit WHERE userid = ? ORDER BY createtime DESC LIMIT ? OFFSET ?",
        [callback](const orm::Result& result) {
            Json::Value history(Json::arrayValue);
            for (const auto& row : result) {
                models::Credit credit(row);
                history.append(credit.toJson());
            }

            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "success";
            ret["data"] = history;
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        std::stoll(userId), pageSize, offset
    );
}

} // namespace controllers
} // namespace woniunote
