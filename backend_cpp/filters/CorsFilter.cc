/**
 * @file CorsFilter.cc
 * @brief CORS Filter Implementation
 */

#include "CorsFilter.h"
#include "core/logger.h"
#include <drogon/HttpResponse.h>

namespace woniunote {

void CorsFilter::doFilter(const drogon::HttpRequestPtr& req,
                          drogon::FilterCallback&& callback,
                          drogon::FilterChainCallback&& chainCallback)
{
    auto origin = req->getHeader("Origin");
    Logger::debug("[CORS] Request", {{"method", req->methodString()}, {"path", req->getPath()}, {"origin", origin}});
    
    // Handle preflight OPTIONS request
    if (req->method() == drogon::Options) {
        auto resp = drogon::HttpResponse::newHttpResponse();
        resp->addHeader("Access-Control-Allow-Origin", origin.empty() ? "*" : origin);
        resp->addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
        resp->addHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With");
        resp->addHeader("Access-Control-Max-Age", "86400");
        resp->addHeader("Access-Control-Allow-Credentials", "true");
        resp->setStatusCode(drogon::k204NoContent);
        Logger::debug("[CORS] Preflight response sent");
        callback(resp);
        return;
    }
    
    // Continue to next filter/handler
    chainCallback();
}

} // namespace woniunote
