/**
 * @file AuthController.cc
 * @brief Authentication API Controller Implementation
 */

#include "AuthController.h"
#include "CaptchaController.h"
#include "core/security.h"
#include "core/database.h"
#include "core/config.h"
#include "core/logger.h"
#include "core/response.h"
#include "models/User.h"
#include <drogon/HttpResponse.h>
#include <drogon/drogon.h>
#include <atomic>
#include <memory>
#include <optional>

using namespace drogon;

namespace woniunote {
namespace controllers {

namespace {
// Parse a user id string to int64 defensively. A JWT may carry a validly
// signed but non-numeric "sub"; std::stoll would otherwise throw.
std::optional<int64_t> parseUserId(const std::string& s)
{
    if (s.empty()) return std::nullopt;
    for (char c : s) {
        if (!std::isdigit(static_cast<unsigned char>(c))) return std::nullopt;
    }
    try {
        return std::stoll(s);
    } catch (const std::exception&) {
        return std::nullopt;
    }
}

// Redis key holding the single active refresh-token id (jti) for a user.
// Refresh rotation overwrites it; presenting any other jti is treated as reuse.
std::string refreshJtiKey(const std::string& userId)
{
    return "refresh_jti:" + userId;
}

// Persist the active refresh jti for a user (TTL = refresh token lifetime),
// then invoke done(). If Redis is unavailable, rotation tracking is best-effort
// and we still proceed (done() is called) so login/refresh keep working.
void storeRefreshJti(const std::string& userId, const std::string& jti,
                     std::function<void()> done)
{
    auto redis = drogon::app().getRedisClient("default");
    if (!redis) {
        Logger::warning("[Auth] Redis unavailable; refresh jti not tracked");
        done();
        return;
    }
    int ttlSeconds = Config::instance().getRefreshTokenExpireDays() * 24 * 3600;
    if (ttlSeconds <= 0) ttlSeconds = 7 * 24 * 3600;
    auto sharedDone = std::make_shared<std::function<void()>>(std::move(done));
    auto completed = std::make_shared<std::atomic_bool>(false);

    drogon::app().getLoop()->runAfter(1.0, [userId, sharedDone, completed]() {
        bool expected = false;
        if (!completed->compare_exchange_strong(expected, true)) {
            return;
        }
        Logger::warning("[Auth] Store refresh jti timed out; continuing login",
                        {{"userid", userId}});
        (*sharedDone)();
    });

    redis->execCommandAsync(
        [sharedDone, completed](const nosql::RedisResult&) {
            bool expected = false;
            if (!completed->compare_exchange_strong(expected, true)) {
                return;
            }
            (*sharedDone)();
        },
        [sharedDone, completed](const nosql::RedisException& e) {
            bool expected = false;
            if (!completed->compare_exchange_strong(expected, true)) {
                return;
            }
            Logger::warning("[Auth] Failed to store refresh jti: " + std::string(e.what()));
            (*sharedDone)();
        },
        "SETEX %s %d %s", refreshJtiKey(userId).c_str(), ttlSeconds, jti.c_str());
}
}  // namespace

// Thin wrappers that delegate to the shared Response helpers so the JSON
// envelope and HTTP status mapping live in exactly one place (core/response.h).
HttpResponsePtr AuthController::makeJsonResponse(int code,
                                                  const std::string& message,
                                                  const Json::Value& data)
{
    return Response::make(code, message, data, drogon::k200OK);
}

HttpResponsePtr AuthController::makeErrorResponse(int httpCode,
                                                   const std::string& message)
{
    return Response::error(httpCode, message,
                           static_cast<HttpStatusCode>(httpCode));
}

void AuthController::registerUser(const HttpRequestPtr& req,
                                   std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::info("[Auth] Register request received", {{"ip", req->getPeerAddr().toIp()}});
    
    auto json = req->getJsonObject();
    if (!json) {
        Logger::warning("[Auth] Register failed: invalid JSON");
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
        Logger::warning("[Auth] Register failed: empty username or password");
        callback(makeErrorResponse(400, "用户名和密码不能为空"));
        return;
    }

    Logger::debug("[Auth] Checking if username exists", {{"username", username}});

    // Wrap the whole registration in a transaction so the user row and the
    // initial credit row are written atomically (both or neither).
    Database::beginTransaction(
        [this, callback, username, password, nickname, qq]
        (const std::shared_ptr<orm::Transaction>& trans) {
            if (!trans) {
                callback(makeErrorResponse(500, "无法开启事务"));
                return;
            }

            // Check if username exists
            trans->execSqlAsync(
                "SELECT userid FROM users WHERE username = ?",
                [this, callback, username, password, nickname, qq, trans]
                (const orm::Result& result) {
                    if (result.size() > 0) {
                        Logger::warning("[Auth] Register failed: username exists", {{"username", username}});
                        callback(makeErrorResponse(400, "用户名已存在"));
                        return;
                    }

                    Logger::debug("[Auth] Creating new user", {{"username", username}});
                    std::string hashedPassword = Security::hashPassword(password);

                    trans->execSqlAsync(
                        "INSERT INTO users (username, password, nickname, qq, role, credit, createtime, updatetime) "
                        "VALUES (?, ?, ?, ?, 'user', 50, NOW(), NOW())",
                        [this, callback, trans, username](const orm::Result& insertResult) {
                            int64_t userId = insertResult.insertId();

                            // Add credit record for registration. If this fails,
                            // the whole transaction is rolled back (see below).
                            trans->execSqlAsync(
                                "INSERT INTO credit (userid, category, target, credit, createtime, updatetime) "
                                "VALUES (?, '用户注册', ?, 50, NOW(), NOW())",
                                [this, callback, trans, userId, username](const orm::Result&) {
                                    // Fetch created user for the response.
                                    trans->execSqlAsync(
                                        "SELECT * FROM users WHERE userid = ?",
                                        [this, callback, username](const orm::Result& userResult) {
                                            if (userResult.size() > 0) {
                                                models::User user(userResult[0]);
                                                Logger::info("[Auth] User registered successfully", {{"userid", std::to_string(user.getUserid())}, {"username", username}});
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
                                    // Credit insert failed -> transaction rolls back the user insert.
                                    Logger::error("Failed to add credit record, rolling back: " + std::string(e.base().what()));
                                    callback(makeErrorResponse(500, "注册失败"));
                                },
                                userId, userId
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
    );
}

void AuthController::login(const HttpRequestPtr& req,
                           std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::info("[Auth] Login request received", {{"ip", req->getPeerAddr().toIp()}});
    
    auto json = req->getJsonObject();
    if (!json) {
        Logger::warning("[Auth] Login failed: invalid JSON");
        callback(makeErrorResponse(400, "请求格式错误"));
        return;
    }

    std::string username = json->get("username", "").asString();
    std::string password = json->get("password", "").asString();

    if (username.empty() || password.empty()) {
        Logger::warning("[Auth] Login failed: empty credentials");
        callback(makeErrorResponse(400, "用户名和密码不能为空"));
        return;
    }
    
    Logger::debug("[Auth] Attempting login", {{"username", username}});

    // Validate captcha. The frontend always sends captcha_id/captcha_code;
    // reject the login if they are missing or incorrect.
    std::string captchaId = json->get("captcha_id", "").asString();
    std::string captchaCode = json->get("captcha_code", "").asString();
    if (!CaptchaController::validateCaptcha(captchaId, captchaCode)) {
        Logger::warning("[Auth] Login failed: invalid captcha", {{"username", username}});
        callback(makeErrorResponse(400, "验证码错误或已过期"));
        return;
    }

    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT * FROM users WHERE username = ?",
        [this, callback, password, username](const orm::Result& result) {
            if (result.size() == 0) {
                Logger::warning("[Auth] Login failed: user not found", {{"username", username}});
                callback(makeErrorResponse(401, "用户名或密码错误"));
                return;
            }

            models::User user(result[0]);

            // Verify password
            if (!Security::verifyPassword(password, user.getPassword())) {
                Logger::warning("[Auth] Login failed: wrong password", {{"username", username}});
                callback(makeErrorResponse(401, "用户名或密码错误"));
                return;
            }
            
            Logger::info("[Auth] Login successful", {{"userid", std::to_string(user.getUserid())}, {"username", username}});

            // Generate tokens. The refresh token carries a unique jti that is
            // recorded in Redis so it can be rotated and reuse-detected.
            std::string userId = std::to_string(user.getUserid());
            std::string jti = Security::generateJti();
            std::string accessToken = Security::createAccessToken(userId);
            std::string refreshToken = Security::createRefreshToken(userId, 0, jti);

            Json::Value data;
            data["access_token"] = accessToken;
            data["refresh_token"] = refreshToken;
            data["token_type"] = "bearer";
            data["user"] = user.toJsonWithoutPassword();

            auto self = this;
            storeRefreshJti(userId, jti, [self, callback, data]() {
                callback(self->makeJsonResponse(200, "登录成功", data));
            });
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
    Logger::debug("[Auth] Token refresh request");
    auto json = req->getJsonObject();
    if (!json || !json->isMember("refresh_token")) {
        Logger::warning("[Auth] Refresh failed: missing token");
        callback(makeErrorResponse(400, "刷新令牌缺失"));
        return;
    }

    std::string refreshToken = (*json)["refresh_token"].asString();
    auto payload = Security::decodeToken(refreshToken);

    if (!payload.has_value() || payload->type != "refresh") {
        Logger::warning("[Auth] Refresh failed: invalid token");
        callback(makeErrorResponse(401, "无效的刷新令牌"));
        return;
    }

    std::string userId = payload->sub;
    auto parsedId = parseUserId(userId);
    if (!parsedId.has_value()) {
        Logger::warning("[Auth] Refresh failed: non-numeric subject");
        callback(makeErrorResponse(401, "无效的刷新令牌"));
        return;
    }

    const std::string presentedJti = payload->jti;
    auto self = this;

    // Verify the presented refresh jti against the single active jti stored in
    // Redis, then rotate. This detects reuse of an already-rotated (or stolen)
    // refresh token and revokes the session. Degrades gracefully when Redis is
    // down (issues new tokens without reuse detection) to preserve availability.
    auto issueNewTokens = [self, callback, userId, parsedId]() {
        auto dbClient = Database::getClient();
        dbClient->execSqlAsync(
            "SELECT * FROM users WHERE userid = ?",
            [self, callback, userId](const orm::Result& result) {
                if (result.size() == 0) {
                    callback(self->makeErrorResponse(401, "用户不存在"));
                    return;
                }

                std::string newJti = Security::generateJti();
                std::string newAccessToken = Security::createAccessToken(userId);
                std::string newRefreshToken =
                    Security::createRefreshToken(userId, 0, newJti);

                Logger::info("[Auth] Token refreshed (rotated)", {{"userid", userId}});

                Json::Value data;
                data["access_token"] = newAccessToken;
                data["refresh_token"] = newRefreshToken;
                data["token_type"] = "bearer";

                storeRefreshJti(userId, newJti, [self, callback, data]() {
                    callback(self->makeJsonResponse(200, "刷新成功", data));
                });
            },
            [self, callback](const orm::DrogonDbException& e) {
                Logger::error("Database error: " + std::string(e.base().what()));
                callback(self->makeErrorResponse(500, "数据库错误"));
            },
            parsedId.value());
    };

    auto redis = drogon::app().getRedisClient("default");
    if (!redis || presentedJti.empty()) {
        // No Redis, or a legacy token issued before jti tracking existed:
        // fall back to the original behaviour (sign new tokens, no reuse check).
        if (presentedJti.empty()) {
            Logger::debug("[Auth] Refresh token without jti; skipping reuse check");
        } else {
            Logger::warning("[Auth] Redis unavailable; skipping refresh reuse check");
        }
        issueNewTokens();
        return;
    }

    auto sharedIssue = std::make_shared<std::function<void()>>(std::move(issueNewTokens));
    redis->execCommandAsync(
        [self, callback, userId, presentedJti, sharedIssue, redis]
        (const nosql::RedisResult& result) {
            std::string storedJti =
                result.type() == nosql::RedisResultType::kNil ? "" : result.asString();

            if (storedJti.empty()) {
                // No active session recorded; treat as invalid/expired refresh.
                Logger::warning("[Auth] Refresh rejected: no active session", {{"userid", userId}});
                callback(self->makeErrorResponse(401, "刷新令牌已失效，请重新登录"));
                return;
            }
            if (storedJti != presentedJti) {
                // Reuse of a rotated/stolen refresh token -> revoke all sessions.
                Logger::warning("[Auth] Refresh token reuse detected; revoking session",
                                {{"userid", userId}});
                redis->execCommandAsync(
                    [](const nosql::RedisResult&) {},
                    [](const nosql::RedisException&) {},
                    "DEL %s", refreshJtiKey(userId).c_str());
                callback(self->makeErrorResponse(401, "检测到刷新令牌复用，请重新登录"));
                return;
            }
            // Valid -> rotate.
            (*sharedIssue)();
        },
        [sharedIssue](const nosql::RedisException& e) {
            // Redis read failed mid-flight: degrade to issuing tokens.
            Logger::warning("[Auth] Refresh reuse check failed, degrading: " + std::string(e.what()));
            (*sharedIssue)();
        },
        "GET %s", refreshJtiKey(userId).c_str());
}

void AuthController::me(const HttpRequestPtr& req,
                        std::function<void(const HttpResponsePtr&)>&& callback)
{
    // User ID is injected by AuthFilter
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::debug("[Auth] Get current user", {{"userid", userId}});
    
    if (userId.empty()) {
        callback(makeErrorResponse(401, "认证失败"));
        return;
    }
    auto parsedId = parseUserId(userId);
    if (!parsedId.has_value()) {
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
        parsedId.value()
    );
}

void AuthController::logout(const HttpRequestPtr& req,
                            std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::info("[Auth] User logged out", {{"userid", userId}});

    // Revoke the active refresh session so a stolen refresh token cannot be
    // used after logout. Best-effort: succeed regardless of Redis state.
    auto redis = drogon::app().getRedisClient("default");
    if (redis && !userId.empty() && parseUserId(userId).has_value()) {
        redis->execCommandAsync(
            [](const nosql::RedisResult&) {},
            [](const nosql::RedisException&) {},
            "DEL %s", refreshJtiKey(userId).c_str());
    }

    // Client should clear tokens; server just returns success
    callback(makeJsonResponse(200, "登出成功"));
}

} // namespace controllers
} // namespace woniunote
