/**
 * @file AuthFilter.cc
 * @brief JWT Authentication Filter Implementation
 */

#include "AuthFilter.h"
#include "core/security.h"
#include "core/logger.h"
#include <drogon/HttpResponse.h>
#include <cctype>

using namespace drogon;

namespace woniunote {

void AuthFilter::doFilter(const HttpRequestPtr& req,
                          FilterCallback&& callback,
                          FilterChainCallback&& chainCallback)
{
    // Get Authorization header
    auto authHeader = req->getHeader("Authorization");
    
    if (authHeader.empty()) {
        Logger::debug("[AuthFilter] No Authorization header", {{"path", req->getPath()}});
        Json::Value ret;
        ret["code"] = 401;
        ret["message"] = "认证令牌缺失";
        auto resp = HttpResponse::newHttpJsonResponse(ret);
        resp->setStatusCode(k401Unauthorized);
        callback(resp);
        return;
    }

    // Check Bearer prefix
    const std::string bearerPrefix = "Bearer ";
    if (authHeader.substr(0, bearerPrefix.size()) != bearerPrefix) {
        Logger::debug("Invalid Authorization header format");
        Json::Value ret;
        ret["code"] = 401;
        ret["message"] = "无效的认证令牌格式";
        auto resp = HttpResponse::newHttpJsonResponse(ret);
        resp->setStatusCode(k401Unauthorized);
        callback(resp);
        return;
    }

    // Extract and decode token
    std::string token = authHeader.substr(bearerPrefix.size());
    auto payload = Security::decodeToken(token);
    
    if (!payload.has_value()) {
        Logger::debug("Token decode failed");
        Json::Value ret;
        ret["code"] = 401;
        ret["message"] = "无效或过期的认证令牌";
        auto resp = HttpResponse::newHttpJsonResponse(ret);
        resp->setStatusCode(k401Unauthorized);
        callback(resp);
        return;
    }

    // Check token type
    if (payload->type != "access") {
        Logger::debug("Wrong token type: " + payload->type);
        Json::Value ret;
        ret["code"] = 401;
        ret["message"] = "无效的令牌类型";
        auto resp = HttpResponse::newHttpJsonResponse(ret);
        resp->setStatusCode(k401Unauthorized);
        callback(resp);
        return;
    }

    // Defensive parse: a validly signed token could carry a non-numeric "sub".
    // Downstream controllers call std::stoll(user_id) unguarded, so validate
    // here at the single choke point to avoid uncaught exceptions crashing the
    // request handler.
    const std::string& sub = payload->sub;
    bool numericId = !sub.empty();
    for (char c : sub) {
        if (!std::isdigit(static_cast<unsigned char>(c))) { numericId = false; break; }
    }
    if (!numericId) {
        Logger::warning("[AuthFilter] Non-numeric token subject rejected", {{"sub", sub}});
        Json::Value ret;
        ret["code"] = 401;
        ret["message"] = "无效的认证令牌";
        auto resp = HttpResponse::newHttpJsonResponse(ret);
        resp->setStatusCode(k401Unauthorized);
        callback(resp);
        return;
    }

    // Store user ID in request attributes for controllers
    req->getAttributes()->insert("user_id", payload->sub);
    
    Logger::debug("[AuthFilter] User authenticated", {{"userid", payload->sub}, {"path", req->getPath()}});
    chainCallback();
}

void OptionalAuthFilter::doFilter(const HttpRequestPtr& req,
                                   FilterCallback&& callback,
                                   FilterChainCallback&& chainCallback)
{
    auto authHeader = req->getHeader("Authorization");
    
    if (authHeader.empty()) {
        // Allow anonymous access
        chainCallback();
        return;
    }

    const std::string bearerPrefix = "Bearer ";
    if (authHeader.substr(0, bearerPrefix.size()) != bearerPrefix) {
        chainCallback();
        return;
    }

    std::string token = authHeader.substr(bearerPrefix.size());
    auto payload = Security::decodeToken(token);
    
    if (payload.has_value() && payload->type == "access") {
        // Only store a numeric subject; downstream callers std::stoll(user_id).
        const std::string& sub = payload->sub;
        bool numericId = !sub.empty();
        for (char c : sub) {
            if (!std::isdigit(static_cast<unsigned char>(c))) { numericId = false; break; }
        }
        if (numericId) {
            req->getAttributes()->insert("user_id", payload->sub);
        }
    }

    chainCallback();
}

} // namespace woniunote
