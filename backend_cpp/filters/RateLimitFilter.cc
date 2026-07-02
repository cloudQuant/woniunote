/**
 * @file RateLimitFilter.cc
 * @brief Rate Limiting Filter Implementation
 *
 * Per-IP fixed-window rate limit backed by Redis. Uses an atomic Lua script
 * (INCR + conditional EXPIRE) so the window TTL can never be lost to a race.
 * When Redis is unavailable the behaviour is governed by the configured
 * fail policy (default: fail-open to preserve availability).
 */

#include "RateLimitFilter.h"
#include "core/logger.h"
#include "core/config.h"
#include "core/response.h"
#include <drogon/HttpResponse.h>
#include <drogon/drogon.h>
#include <atomic>
#include <memory>

using namespace drogon;

namespace woniunote {

namespace {
// Atomic fixed-window counter: INCR the key, and on first hit set the TTL.
// Returns the current count. Keeps INCR and EXPIRE in a single round-trip so
// they cannot interleave with other requests.
constexpr const char* kRateLimitLua =
    "local c = redis.call('INCR', KEYS[1]) "
    "if c == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end "
    "return c";
} // namespace

void RateLimitFilter::doFilter(const HttpRequestPtr& req,
                               FilterCallback&& callback,
                               FilterChainCallback&& chainCallback)
{
    std::string clientIp = req->getPeerAddr().toIp();
    Logger::debug("[RateLimit] Check", {{"ip", clientIp}, {"path", req->getPath()}});

    const bool failClosed = Config::instance().getRateLimitFailClosed();

    auto redisClient = app().getRedisClient("default");
    if (!redisClient) {
        if (failClosed) {
            Logger::warning("[RateLimit] Redis unavailable, fail-closed -> rejecting");
            callback(Response::error(503, "服务暂时不可用，请稍后再试",
                                     drogon::k503ServiceUnavailable));
        } else {
            Logger::warning("[RateLimit] Redis unavailable, fail-open -> allowing");
            chainCallback();
        }
        return;
    }

    const int limit = Config::instance().getRateLimitPerMinute();
    std::string key = "rate_limit:" + clientIp;

    auto sharedChain = std::make_shared<FilterChainCallback>(std::move(chainCallback));
    auto sharedCallback = std::make_shared<FilterCallback>(std::move(callback));
    auto completed = std::make_shared<std::atomic_bool>(false);

    app().getLoop()->runAfter(1.0, [req, sharedCallback, sharedChain, completed, failClosed]() {
        bool expected = false;
        if (!completed->compare_exchange_strong(expected, true)) {
            return;
        }

        Logger::warning("[RateLimit] Redis check timed out", {
            {"ip", req->getPeerAddr().toIp()},
            {"path", req->getPath()}
        });
        if (failClosed) {
            (*sharedCallback)(Response::error(503, "服务暂时不可用，请稍后再试",
                                              drogon::k503ServiceUnavailable));
        } else {
            (*sharedChain)();
        }
    });

    redisClient->execCommandAsync(
        [req, sharedCallback, sharedChain, completed, limit]
        (const nosql::RedisResult& result) {
            bool expected = false;
            if (!completed->compare_exchange_strong(expected, true)) {
                return;
            }

            int64_t count = 0;
            if (result.type() == nosql::RedisResultType::kInteger) {
                count = result.asInteger();
            } else {
                // Unexpected reply shape -> allow rather than block legitimate traffic.
                (*sharedChain)();
                return;
            }

            if (count > limit) {
                Logger::warning("[RateLimit] Exceeded", {{"ip", req->getPeerAddr().toIp()}, {"count", std::to_string(count)}});
                auto resp = Response::tooManyRequests("请求过于频繁，请稍后再试");
                resp->addHeader("Retry-After", "60");
                (*sharedCallback)(resp);
                return;
            }

            (*sharedChain)();
        },
        [sharedCallback, sharedChain, completed, failClosed](const nosql::RedisException& e) {
            bool expected = false;
            if (!completed->compare_exchange_strong(expected, true)) {
                return;
            }

            Logger::error("[RateLimit] Redis error: " + std::string(e.what()));
            if (failClosed) {
                (*sharedCallback)(Response::error(503, "服务暂时不可用，请稍后再试",
                                                  drogon::k503ServiceUnavailable));
            } else {
                (*sharedChain)();
            }
        },
        "EVAL %s 1 %s 60", kRateLimitLua, key.c_str()
    );
}

} // namespace woniunote
