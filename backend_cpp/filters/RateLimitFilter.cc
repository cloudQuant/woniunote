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
#include <memory>
#include <string>

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

struct RateLimitCompletion
{
    RateLimitCompletion(FilterCallback&& callbackIn,
                        FilterChainCallback&& chainCallbackIn)
        : callback_(std::move(callbackIn)),
          chainCallback_(std::move(chainCallbackIn))
    {
    }

    bool tryComplete(FilterCallback& completedCallback,
                     FilterChainCallback& completedChainCallback)
    {
        if (completed)
        {
            return false;
        }

        completed = true;
        completedCallback = std::move(callback_);
        completedChainCallback = std::move(chainCallback_);
        return true;
    }

    FilterCallback callback_;
    FilterChainCallback chainCallback_;
    bool completed{false};
};
} // namespace

void RateLimitFilter::doFilter(const HttpRequestPtr& req,
                               FilterCallback&& callback,
                               FilterChainCallback&& chainCallback)
{
    const std::string clientIp = req->getPeerAddr().toIp();
    const std::string requestPath = req->getPath();
    Logger::debug("[RateLimit] Check", {{"ip", clientIp}, {"path", requestPath}});

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

    auto requestConnection = req->getConnectionPtr().lock();
    auto* requestLoop = requestConnection
                            ? requestConnection->getLoop()
                            : trantor::EventLoop::getEventLoopOfCurrentThread();
    if (!requestLoop)
    {
        Logger::error("[RateLimit] Request event loop unavailable");
        if (failClosed)
        {
            callback(Response::error(503, "服务暂时不可用，请稍后再试",
                                     drogon::k503ServiceUnavailable));
        }
        else
        {
            chainCallback();
        }
        return;
    }

    const auto weakConnection = req->getConnectionPtr();
    auto completion = std::make_shared<RateLimitCompletion>(
        std::move(callback), std::move(chainCallback));
    const std::weak_ptr<RateLimitCompletion> weakCompletion = completion;

    requestLoop->runAfter(1.0,
                          [completion, clientIp, requestPath, failClosed]() {
        FilterCallback timeoutCallback;
        FilterChainCallback timeoutChainCallback;
        if (!completion->tryComplete(timeoutCallback, timeoutChainCallback))
        {
            return;
        }

        Logger::warning("[RateLimit] Redis check timed out", {
            {"ip", clientIp},
            {"path", requestPath}
        });
        if (failClosed) {
            timeoutCallback(Response::error(503, "服务暂时不可用，请稍后再试",
                                            drogon::k503ServiceUnavailable));
        } else {
            timeoutChainCallback();
        }
    });

    redisClient->execCommandAsync(
        [weakCompletion, weakConnection, clientIp, limit]
        (const nosql::RedisResult& result) {
            const bool hasIntegerResult =
                result.type() == nosql::RedisResultType::kInteger;
            const int64_t count = hasIntegerResult ? result.asInteger() : 0;

            auto connection = weakConnection.lock();
            if (!connection)
            {
                return;
            }
            auto* loop = connection->getLoop();
            if (!loop)
            {
                return;
            }

            loop->queueInLoop([weakCompletion, clientIp, limit,
                               hasIntegerResult, count]() {
                auto activeCompletion = weakCompletion.lock();
                if (!activeCompletion)
                {
                    return;
                }

                FilterCallback resultCallback;
                FilterChainCallback resultChainCallback;
                if (!activeCompletion->tryComplete(resultCallback,
                                                   resultChainCallback))
                {
                    return;
                }

                if (!hasIntegerResult)
                {
                    // Unexpected reply shape -> allow rather than block legitimate traffic.
                    resultChainCallback();
                    return;
                }

                if (count > limit)
                {
                    Logger::warning("[RateLimit] Exceeded",
                                    {{"ip", clientIp},
                                     {"count", std::to_string(count)}});
                    auto resp =
                        Response::tooManyRequests("请求过于频繁，请稍后再试");
                    resp->addHeader("Retry-After", "60");
                    resultCallback(resp);
                    return;
                }

                resultChainCallback();
            });
        },
        [weakCompletion, weakConnection, failClosed]
        (const nosql::RedisException& e) {
            const std::string error = e.what();
            auto connection = weakConnection.lock();
            if (!connection)
            {
                return;
            }
            auto* loop = connection->getLoop();
            if (!loop)
            {
                return;
            }

            loop->queueInLoop([weakCompletion, failClosed, error]() {
                auto activeCompletion = weakCompletion.lock();
                if (!activeCompletion)
                {
                    return;
                }

                FilterCallback errorCallback;
                FilterChainCallback errorChainCallback;
                if (!activeCompletion->tryComplete(errorCallback,
                                                   errorChainCallback))
                {
                    return;
                }

                Logger::error("[RateLimit] Redis error: " + error);
                if (failClosed) {
                    errorCallback(Response::error(503, "服务暂时不可用，请稍后再试",
                                                  drogon::k503ServiceUnavailable));
                } else {
                    errorChainCallback();
                }
            });
        },
        "EVAL %s 1 %s 60", kRateLimitLua, key.c_str()
    );
}

} // namespace woniunote
