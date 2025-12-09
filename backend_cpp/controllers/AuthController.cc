/**
 * @file AuthController.cc
 * @brief Authentication API Controller Implementation
 */

#include "AuthController.h"
#include "core/security.h"
#include "core/database.h"
#include "core/logger.h"
#include "models/User.h"
#include <drogon/HttpResponse.h>

using namespace drogon;

namespace woniunote {
namespace controllers {

HttpResponsePtr AuthController::makeJsonResponse(int code, 
                                                  const std::string& message,
                                                  const Json::Value& data)
{
    Json::Value ret;
    ret["code"] = code;
    ret["message"] = message;
    if (!data.isNull()) {
        ret["data"] = data;
    }
    return HttpResponse::newHttpJsonResponse(ret);
}

HttpResponsePtr AuthController::makeErrorResponse(int httpCode, 
                                                   const std::string& message)
{
    Json::Value ret;
    ret["code"] = httpCode;
    ret["message"] = message;
    auto resp = HttpResponse::newHttpJsonResponse(ret);
    resp->setStatusCode(static_cast<HttpStatusCode>(httpCode));
    return resp;
}

void AuthController::registerUser(const HttpRequestPtr& req,
                                   std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto json = req->getJsonObject();
    if (!json) {
        callback(makeErrorResponse(400, "请求格式错误"));
        return;
    }

    // Validate required fields
    if (!json->isMember("username") || !json->isMember("password")) {
        callback(makeErrorResponse(400, "用户名和密码不能为空"));
        return;
    }

    std::string username = (*json)["username"].asString();
    std::string password = (*json)["password"].asString();
    std::string nickname = json->get("nickname", username).asString();
    std::string qq = json->get("qq", "").asString();

    if (username.empty() || password.empty()) {
        callback(makeErrorResponse(400, "用户名和密码不能为空"));
        return;
    }

    auto dbClient = Database::getClient();

    // Check if username exists
    dbClient->execSqlAsync(
        "SELECT userid FROM users WHERE username = ?",
        [this, callback, username, password, nickname, qq, dbClient]
        (const orm::Result& result) {
            if (result.size() > 0) {
                callback(makeErrorResponse(400, "用户名已存在"));
                return;
            }

            // Create new user
            std::string hashedPassword = Security::hashPassword(password);
            
            dbClient->execSqlAsync(
                "INSERT INTO users (username, password, nickname, qq, role, credit, createtime, updatetime) "
                "VALUES (?, ?, ?, ?, 'user', 50, NOW(), NOW())",
                [this, callback, dbClient](const orm::Result& insertResult) {
                    int64_t userId = insertResult.insertId();
                    
                    // Add credit record for registration
                    dbClient->execSqlAsync(
                        "INSERT INTO credit (userid, category, target, credit, createtime, updatetime) "
                        "VALUES (?, '用户注册', ?, 50, NOW(), NOW())",
                        [](const orm::Result&) {},
                        [](const orm::DrogonDbException& e) {
                            Logger::error("Failed to add credit record: " + std::string(e.base().what()));
                        },
                        userId, userId
                    );

                    // Fetch created user
                    dbClient->execSqlAsync(
                        "SELECT * FROM users WHERE userid = ?",
                        [this, callback](const orm::Result& userResult) {
                            if (userResult.size() > 0) {
                                models::User user(userResult[0]);
                                callback(makeJsonResponse(200, "注册成功", user.toJsonWithoutPassword()));
                            } else {
                                callback(makeErrorResponse(500, "注册失败"));
                            }
                        },
                        [this, callback](const orm::DrogonDbException& e) {
                            Logger::error("Failed to fetch user: " + std::string(e.base().what()));
                            callback(makeErrorResponse(500, "注册失败"));
                        },
                        userId
                    );
                },
                [this, callback](const orm::DrogonDbException& e) {
                    Logger::error("Failed to create user: " + std::string(e.base().what()));
                    callback(makeErrorResponse(500, "注册失败"));
                },
                username, hashedPassword, nickname, qq
            );
        },
        [this, callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            callback(makeErrorResponse(500, "数据库错误"));
        },
        username
    );
}

void AuthController::login(const HttpRequestPtr& req,
                           std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto json = req->getJsonObject();
    if (!json) {
        callback(makeErrorResponse(400, "请求格式错误"));
        return;
    }

    std::string username = json->get("username", "").asString();
    std::string password = json->get("password", "").asString();

    if (username.empty() || password.empty()) {
        callback(makeErrorResponse(400, "用户名和密码不能为空"));
        return;
    }

    // TODO: Validate captcha if provided
    // std::string captchaId = json->get("captcha_id", "").asString();
    // std::string captchaCode = json->get("captcha_code", "").asString();

    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT * FROM users WHERE username = ?",
        [this, callback, password](const orm::Result& result) {
            if (result.size() == 0) {
                callback(makeErrorResponse(401, "用户名或密码错误"));
                return;
            }

            models::User user(result[0]);

            // Verify password
            if (!Security::verifyPassword(password, user.getPassword())) {
                callback(makeErrorResponse(401, "用户名或密码错误"));
                return;
            }

            // Generate tokens
            std::string userId = std::to_string(user.getUserid());
            std::string accessToken = Security::createAccessToken(userId);
            std::string refreshToken = Security::createRefreshToken(userId);

            Json::Value data;
            data["access_token"] = accessToken;
            data["refresh_token"] = refreshToken;
            data["token_type"] = "bearer";
            data["user"] = user.toJsonWithoutPassword();

            callback(makeJsonResponse(200, "登录成功", data));
        },
        [this, callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            callback(makeErrorResponse(500, "数据库错误"));
        },
        username
    );
}

void AuthController::refresh(const HttpRequestPtr& req,
                             std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto json = req->getJsonObject();
    if (!json || !json->isMember("refresh_token")) {
        callback(makeErrorResponse(400, "刷新令牌缺失"));
        return;
    }

    std::string refreshToken = (*json)["refresh_token"].asString();
    auto payload = Security::decodeToken(refreshToken);

    if (!payload.has_value() || payload->type != "refresh") {
        callback(makeErrorResponse(401, "无效的刷新令牌"));
        return;
    }

    std::string userId = payload->sub;

    auto dbClient = Database::getClient();
    dbClient->execSqlAsync(
        "SELECT * FROM users WHERE userid = ?",
        [this, callback, userId](const orm::Result& result) {
            if (result.size() == 0) {
                callback(makeErrorResponse(401, "用户不存在"));
                return;
            }

            // Generate new tokens
            std::string newAccessToken = Security::createAccessToken(userId);
            std::string newRefreshToken = Security::createRefreshToken(userId);

            Json::Value data;
            data["access_token"] = newAccessToken;
            data["refresh_token"] = newRefreshToken;
            data["token_type"] = "bearer";

            callback(makeJsonResponse(200, "刷新成功", data));
        },
        [this, callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            callback(makeErrorResponse(500, "数据库错误"));
        },
        std::stoll(userId)
    );
}

void AuthController::me(const HttpRequestPtr& req,
                        std::function<void(const HttpResponsePtr&)>&& callback)
{
    // User ID is injected by AuthFilter
    auto userId = req->getAttributes()->get<std::string>("user_id");
    
    if (userId.empty()) {
        callback(makeErrorResponse(401, "认证失败"));
        return;
    }

    auto dbClient = Database::getClient();
    dbClient->execSqlAsync(
        "SELECT * FROM users WHERE userid = ?",
        [this, callback](const orm::Result& result) {
            if (result.size() == 0) {
                callback(makeErrorResponse(404, "用户不存在"));
                return;
            }

            models::User user(result[0]);
            callback(makeJsonResponse(200, "success", user.toJsonWithoutPassword()));
        },
        [this, callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            callback(makeErrorResponse(500, "数据库错误"));
        },
        std::stoll(userId)
    );
}

void AuthController::logout(const HttpRequestPtr& req,
                            std::function<void(const HttpResponsePtr&)>&& callback)
{
    // Client should clear tokens; server just returns success
    callback(makeJsonResponse(200, "登出成功"));
}

} // namespace controllers
} // namespace woniunote
