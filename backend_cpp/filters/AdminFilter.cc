/**
 * @file AdminFilter.cc
 * @brief Admin Authentication Filter Implementation
 */

#include "AdminFilter.h"
#include "core/security.h"
#include "core/database.h"
#include "core/logger.h"
#include <drogon/HttpResponse.h>
#include <cctype>

using namespace drogon;

namespace woniunote {

void AdminFilter::doFilter(const HttpRequestPtr& req,
                           FilterCallback&& fcb,
                           FilterChainCallback&& fccb)
{
    // Extract token from Authorization header
    auto authHeader = req->getHeader("Authorization");
    Logger::debug("[AdminFilter] Check admin access", {{"path", req->getPath()}});
    
    if (authHeader.empty() || authHeader.substr(0, 7) != "Bearer ") {
        Logger::warning("[AdminFilter] No token provided", {{"path", req->getPath()}});
        Json::Value ret;
        ret["code"] = 401;
        ret["message"] = "未提供认证令牌";
        auto resp = HttpResponse::newHttpJsonResponse(ret);
        resp->setStatusCode(k401Unauthorized);
        fcb(resp);
        return;
    }

    std::string token = authHeader.substr(7);
    auto payload = Security::decodeToken(token);

    if (!payload.has_value()) {
        Json::Value ret;
        ret["code"] = 401;
        ret["message"] = "无效的认证令牌";
        auto resp = HttpResponse::newHttpJsonResponse(ret);
        resp->setStatusCode(k401Unauthorized);
        fcb(resp);
        return;
    }

    // Check if token is access type
    if (payload->type != "access") {
        Json::Value ret;
        ret["code"] = 401;
        ret["message"] = "无效的令牌类型";
        auto resp = HttpResponse::newHttpJsonResponse(ret);
        resp->setStatusCode(k401Unauthorized);
        fcb(resp);
        return;
    }

    std::string userId = payload->sub;

    // Defensive parse: a validly signed token could carry a non-numeric sub.
    bool numericId = !userId.empty();
    for (char c : userId) {
        if (!std::isdigit(static_cast<unsigned char>(c))) { numericId = false; break; }
    }
    if (!numericId) {
        Json::Value ret;
        ret["code"] = 401;
        ret["message"] = "无效的认证令牌";
        auto resp = HttpResponse::newHttpJsonResponse(ret);
        resp->setStatusCode(k401Unauthorized);
        fcb(resp);
        return;
    }

    // Check if user is admin
    auto dbClient = Database::getClient();
    dbClient->execSqlAsync(
        "SELECT role FROM users WHERE userid = ?",
        [req, fcb = std::move(fcb), fccb = std::move(fccb), userId]
        (const orm::Result& result) mutable {
            if (result.size() == 0) {
                Json::Value ret;
                ret["code"] = 401;
                ret["message"] = "用户不存在";
                auto resp = HttpResponse::newHttpJsonResponse(ret);
                resp->setStatusCode(k401Unauthorized);
                fcb(resp);
                return;
            }

            std::string role = result[0]["role"].as<std::string>();
            if (role != "admin") {
                Logger::warning("[AdminFilter] Access denied: not admin", {{"userid", userId}, {"role", role}});
                Json::Value ret;
                ret["code"] = 403;
                ret["message"] = "需要管理员权限";
                auto resp = HttpResponse::newHttpJsonResponse(ret);
                resp->setStatusCode(k403Forbidden);
                fcb(resp);
                return;
            }

            // Store user ID in request attributes for controllers
            req->getAttributes()->insert("user_id", userId);
            req->getAttributes()->insert("is_admin", true);

            Logger::info("[AdminFilter] Admin access granted", {{"userid", userId}});
            // Continue to next filter/controller
            fccb();
        },
        [fcb = std::move(fcb)](const orm::DrogonDbException& e) mutable {
            Logger::error("Admin check failed: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "认证失败";
            auto resp = HttpResponse::newHttpJsonResponse(ret);
            resp->setStatusCode(k500InternalServerError);
            fcb(resp);
        },
        std::stoll(userId)
    );
}

} // namespace woniunote
