/**
 * @file UserController.cc
 * @brief User API Controller Implementation
 */

#include "UserController.h"
#include "core/database.h"
#include "core/security.h"
#include "core/logger.h"
#include "core/response.h"
#include "models/User.h"
#include <drogon/HttpResponse.h>

using namespace drogon;

namespace woniunote {
namespace controllers {

void UserController::getUser(const HttpRequestPtr& req,
                             std::function<void(const HttpResponsePtr&)>&& callback,
                             int64_t id)
{
    Logger::debug("[User] Get user", {{"userid", std::to_string(id)}});
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT * FROM users WHERE userid = ?",
        [callback, id](const orm::Result& result) {
            if (result.size() == 0) {
                Logger::debug("[User] Not found", {{"userid", std::to_string(id)}});
                callback(Response::notFound("用户不存在"));
                return;
            }

            models::User user(result[0]);
            Logger::debug("[User] Found", {{"userid", std::to_string(id)}, {"username", user.getUsername()}});
            callback(Response::success(user.toJsonWithoutPassword()));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        id
    );
}

void UserController::updateProfile(const HttpRequestPtr& req,
                                   std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::info("[User] Update profile", {{"userid", userId}});
    auto json = req->getJsonObject();

    if (!json) {
        Logger::warning("[User] Update failed: invalid JSON");
        callback(Response::badRequest("请求格式错误"));
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
                [callback, userId](const orm::Result& userResult) {
                    if (userResult.size() > 0) {
                        models::User user(userResult[0]);
                        Logger::info("[User] Profile updated", {{"userid", userId}});
                        callback(Response::ok("更新成功", user.toJsonWithoutPassword()));
                    } else {
                        callback(Response::notFound("用户不存在"));
                    }
                },
                [callback](const orm::DrogonDbException& e) {
                    Logger::error("Fetch error: " + std::string(e.base().what()));
                    callback(Response::serverError("更新失败"));
                },
                std::stoll(userId)
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Update error: " + std::string(e.base().what()));
            callback(Response::serverError("更新失败"));
        },
        nickname, qq, avatar, std::stoll(userId)
    );
}

void UserController::changePassword(const HttpRequestPtr& req,
                                    std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::info("[User] Change password request", {{"userid", userId}});
    auto json = req->getJsonObject();

    if (!json || !json->isMember("old_password") || !json->isMember("new_password")) {
        Logger::warning("[User] Change password failed: missing fields");
        callback(Response::badRequest("请提供旧密码和新密码"));
        return;
    }

    std::string oldPassword = (*json)["old_password"].asString();
    std::string newPassword = (*json)["new_password"].asString();

    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT password FROM users WHERE userid = ?",
        [callback, userId, oldPassword, newPassword, dbClient](const orm::Result& result) {
            if (result.size() == 0) {
                callback(Response::notFound("用户不存在"));
                return;
            }

            std::string currentHash = result[0]["password"].as<std::string>();
            if (!Security::verifyPassword(oldPassword, currentHash)) {
                Logger::warning("[User] Password change failed: wrong old password", {{"userid", userId}});
                callback(Response::badRequest("旧密码错误"));
                return;
            }

            std::string newHash = Security::hashPassword(newPassword);
            dbClient->execSqlAsync(
                "UPDATE users SET password = ?, updatetime = NOW() WHERE userid = ?",
                [callback, userId](const orm::Result&) {
                    Logger::info("[User] Password changed", {{"userid", userId}});
                    callback(Response::ok("密码修改成功"));
                },
                [callback](const orm::DrogonDbException& e) {
                    Logger::error("Password update error: " + std::string(e.base().what()));
                    callback(Response::serverError("密码修改失败"));
                },
                newHash, std::stoll(userId)
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        std::stoll(userId)
    );
}

} // namespace controllers
} // namespace woniunote
