/**
 * @file RateLimitFilter.cc
 * @brief Rate Limiting Filter Implementation
 */

#include "RateLimitFilter.h"
#include "core/logger.h"
#include <drogon/HttpResponse.h>
#include <drogon/drogon.h>

using namespace drogon;

namespace woniunote {

void RateLimitFilter::doFilter(const HttpRequestPtr& req,
                               FilterCallback&& callback,
                               FilterChainCallback&& chainCallback)
{
    // Get client IP
    std::string clientIp = req->getPeerAddr().toIp();
    
    // Get Redis client
    auto redisClient = app().getRedisClient("default");
    if (!redisClient) {
        // Redis not configured, skip rate limiting
        Logger::warning("Redis not configured, skipping rate limit");
        chainCallback();
        return;
    }

    std::string key = "rate_limit:" + clientIp;

    // Use Redis INCR with expiration for simple rate limiting
    redisClient->execCommandAsync(
        [req, callback = std::move(callback), chainCallback = std::move(chainCallback), key]
        (const nosql::RedisResult& result) mutable {
            if (result.isNil() || result.type() == nosql::RedisResultType::kError) {
                // Redis error, allow request
                chainCallback();
                return;
            }

            int64_t count = result.asInteger();
            
            if (count == 1) {
                // First request in window, set expiration
                auto redis = app().getRedisClient("default");
                redis->execCommandAsync(
                    [](const nosql::RedisResult&) {},
                    "EXPIRE %s 60", key.c_str()
                );
            }

            if (count > REQUESTS_PER_MINUTE) {
                Logger::warning("Rate limit exceeded for IP: " + 
                               req->getPeerAddr().toIp());
                Json::Value ret;
                ret["code"] = 429;
                ret["message"] = "请求过于频繁，请稍后再试";
                auto resp = HttpResponse::newHttpJsonResponse(ret);
                resp->setStatusCode(k429TooManyRequests);
                resp->addHeader("Retry-After", "60");
                callback(resp);
                return;
            }

            chainCallback();
        },
        "INCR %s", key.c_str()
    );
}

} // namespace woniunote
