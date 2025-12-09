/**
 * @file UserController.cc
 * @brief User API Controller Implementation
 */

#include "UserController.h"
#include "core/database.h"
#include "core/security.h"
#include "core/logger.h"
#include "models/User.h"
#include <drogon/HttpResponse.h>

using namespace drogon;

namespace woniunote {
namespace controllers {

void UserController::getUser(const HttpRequestPtr& req,
                             std::function<void(const HttpResponsePtr&)>&& callback,
                             int64_t id)
{
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT * FROM users WHERE userid = ?",
        [callback](const orm::Result& result) {
            if (result.size() == 0) {
                Json::Value ret;
                ret["code"] = 404;
                ret["message"] = "用户不存在";
                auto resp = HttpResponse::newHttpJsonResponse(ret);
                resp->setStatusCode(k404NotFound);
                callback(resp);
                return;
            }

            models::User user(result[0]);
            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "success";
            ret["data"] = user.toJsonWithoutPassword();
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            auto resp = HttpResponse::newHttpJsonResponse(ret);
            resp->setStatusCode(k500InternalServerError);
            callback(resp);
        },
        id
    );
}

void UserController::updateProfile(const HttpRequestPtr& req,
                                   std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto json = req->getJsonObject();

    if (!json) {
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "请求格式错误";
        auto resp = HttpResponse::newHttpJsonResponse(ret);
        resp->setStatusCode(k400BadRequest);
        callback(resp);
        return;
    }

    std::string nickname = json->get("nickname", "").asString();
    std::string qq = json->get("qq", "").asString();
    std::string avatar = json->get("avatar", "").asString();

    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "UPDATE users SET nickname = ?, qq = ?, avatar = ?, updatetime = NOW() WHERE userid = ?",
        [callback, userId, dbClient](const orm::Result& result) {
            dbClient->execSqlAsync(
                "SELECT * FROM users WHERE userid = ?",
                [callback](const orm::Result& userResult) {
                    if (userResult.size() > 0) {
                        models::User user(userResult[0]);
                        Json::Value ret;
                        ret["code"] = 200;
                        ret["message"] = "更新成功";
                        ret["data"] = user.toJsonWithoutPassword();
                        callback(HttpResponse::newHttpJsonResponse(ret));
                    }
                },
                [callback](const orm::DrogonDbException& e) {
                    Logger::error("Fetch error: " + std::string(e.base().what()));
                },
                std::stoll(userId)
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Update error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "更新失败";
            auto resp = HttpResponse::newHttpJsonResponse(ret);
            resp->setStatusCode(k500InternalServerError);
            callback(resp);
        },
        nickname, qq, avatar, std::stoll(userId)
    );
}

void UserController::changePassword(const HttpRequestPtr& req,
                                    std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto json = req->getJsonObject();

    if (!json || !json->isMember("old_password") || !json->isMember("new_password")) {
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "请提供旧密码和新密码";
        auto resp = HttpResponse::newHttpJsonResponse(ret);
        resp->setStatusCode(k400BadRequest);
        callback(resp);
        return;
    }

    std::string oldPassword = (*json)["old_password"].asString();
    std::string newPassword = (*json)["new_password"].asString();

    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT password FROM users WHERE userid = ?",
        [callback, userId, oldPassword, newPassword, dbClient](const orm::Result& result) {
            if (result.size() == 0) {
                Json::Value ret;
                ret["code"] = 404;
                ret["message"] = "用户不存在";
                auto resp = HttpResponse::newHttpJsonResponse(ret);
                resp->setStatusCode(k404NotFound);
                callback(resp);
                return;
            }

            std::string currentHash = result[0]["password"].as<std::string>();
            if (!Security::verifyPassword(oldPassword, currentHash)) {
                Json::Value ret;
                ret["code"] = 400;
                ret["message"] = "旧密码错误";
                auto resp = HttpResponse::newHttpJsonResponse(ret);
                resp->setStatusCode(k400BadRequest);
                callback(resp);
                return;
            }

            std::string newHash = Security::hashPassword(newPassword);
            dbClient->execSqlAsync(
                "UPDATE users SET password = ?, updatetime = NOW() WHERE userid = ?",
                [callback](const orm::Result&) {
                    Json::Value ret;
                    ret["code"] = 200;
                    ret["message"] = "密码修改成功";
                    callback(HttpResponse::newHttpJsonResponse(ret));
                },
                [callback](const orm::DrogonDbException& e) {
                    Logger::error("Password update error: " + std::string(e.base().what()));
                    Json::Value ret;
                    ret["code"] = 500;
                    ret["message"] = "密码修改失败";
                    auto resp = HttpResponse::newHttpJsonResponse(ret);
                    resp->setStatusCode(k500InternalServerError);
                    callback(resp);
                },
                newHash, std::stoll(userId)
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            auto resp = HttpResponse::newHttpJsonResponse(ret);
            resp->setStatusCode(k500InternalServerError);
            callback(resp);
        },
        std::stoll(userId)
    );
}

} // namespace controllers
} // namespace woniunote
