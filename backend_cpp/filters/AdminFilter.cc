/**
 * @file AdminFilter.cc
 * @brief Admin Authentication Filter Implementation
 */

#include "AdminFilter.h"
#include "core/security.h"
#include "core/database.h"
#include "core/logger.h"
#include <drogon/HttpResponse.h>
#include <atomic>
#include <charconv>
#include <chrono>
#include <cstdint>
#include <functional>
#include <limits>
#include <memory>
#include <mutex>
#include <string>
#include <utility>

using namespace drogon;

namespace woniunote {

namespace {

HttpResponsePtr filterError(int code, const std::string& message)
{
    Json::Value body;
    body["code"] = code;
    body["message"] = message;
    auto response = HttpResponse::newHttpJsonResponse(body);
    response->setStatusCode(static_cast<HttpStatusCode>(code));
    return response;
}

bool parseAdminUserId(const std::string& raw, int64_t& userId)
{
    const auto parsed = std::from_chars(raw.data(), raw.data() + raw.size(), userId, 10);
    return !raw.empty() && parsed.ec == std::errc{} && parsed.ptr == raw.data() + raw.size() &&
           userId > 0 && userId <= std::numeric_limits<int32_t>::max();
}

class FilterCompletion final : public std::enable_shared_from_this<FilterCompletion> {
public:
    FilterCompletion(FilterCallback&& response, FilterChainCallback&& next)
        : response_(std::move(response)), next_(std::move(next))
    {
    }

    void armTimeout()
    {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (completed_.load(std::memory_order_acquire)) {
                return;
            }
            deadline_ = std::chrono::steady_clock::now() + std::chrono::seconds(5);
        }
        auto* loop = drogon::app().getLoop();
        if (loop == nullptr) {
            respond(filterError(503, "认证服务暂时不可用"));
            return;
        }
        auto self = shared_from_this();
        const auto timerId = loop->runAfter(5.0, [self]() {
            self->respond(filterError(503, "认证服务暂时不可用"));
        });
        bool cancelTimer = false;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (completed_.load(std::memory_order_acquire)) {
                cancelTimer = true;
            } else {
                loop_ = loop;
                timerId_ = timerId;
            }
        }
        if (cancelTimer) {
            loop->runInLoop([loop, timerId]() { loop->invalidateTimer(timerId); });
        }
    }

    void respond(const HttpResponsePtr& response)
    {
        bool timedOut = false;
        if (!claimCompletion(timedOut)) {
            return;
        }
        cancelTimer();
        if (response_) {
            response_(timedOut ? filterError(503, "认证服务暂时不可用") : response);
        }
    }

    void continueChain(const std::function<void()>& onSuccess)
    {
        bool timedOut = false;
        if (!claimCompletion(timedOut)) {
            return;
        }
        cancelTimer();
        if (timedOut) {
            if (response_) {
                response_(filterError(503, "认证服务暂时不可用"));
            }
            return;
        }
        if (onSuccess) {
            onSuccess();
        }
        if (next_) {
            next_();
        }
    }

private:
    bool claimCompletion(bool& timedOut)
    {
        std::lock_guard<std::mutex> lock(mutex_);
        if (completed_.load(std::memory_order_acquire)) {
            return false;
        }
        timedOut = deadline_ != std::chrono::steady_clock::time_point{} &&
                   std::chrono::steady_clock::now() >= deadline_;
        completed_.store(true, std::memory_order_release);
        return true;
    }

    void cancelTimer()
    {
        trantor::EventLoop* loop = nullptr;
        trantor::TimerId timerId;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            loop = loop_;
            timerId = timerId_;
            timerId_ = trantor::InvalidTimerId;
        }
        if (loop != nullptr && timerId != trantor::InvalidTimerId) {
            loop->runInLoop([loop, timerId]() { loop->invalidateTimer(timerId); });
        }
    }

    std::atomic<bool> completed_{false};
    FilterCallback response_;
    FilterChainCallback next_;
    std::mutex mutex_;
    trantor::EventLoop* loop_{nullptr};
    trantor::TimerId timerId_{trantor::InvalidTimerId};
    std::chrono::steady_clock::time_point deadline_{};
};

} // namespace

void AdminFilter::doFilter(const HttpRequestPtr& req,
                           FilterCallback&& fcb,
                           FilterChainCallback&& fccb)
{
    auto completion = std::make_shared<FilterCompletion>(std::move(fcb), std::move(fccb));
    // Extract token from Authorization header
    auto authHeader = req->getHeader("Authorization");
    Logger::debug("[AdminFilter] Check admin access", {{"path", req->getPath()}});
    
    if (authHeader.empty() || authHeader.substr(0, 7) != "Bearer ") {
        Logger::warning("[AdminFilter] No token provided", {{"path", req->getPath()}});
        completion->respond(filterError(401, "未提供认证令牌"));
        return;
    }

    std::string token = authHeader.substr(7);
    auto payload = Security::decodeToken(token);

    if (!payload.has_value()) {
        completion->respond(filterError(401, "无效的认证令牌"));
        return;
    }

    // Check if token is access type
    if (payload->type != "access") {
        completion->respond(filterError(401, "无效的令牌类型"));
        return;
    }

    std::string userId = payload->sub;
    int64_t numericUserId = 0;
    if (!parseAdminUserId(userId, numericUserId)) {
        completion->respond(filterError(401, "无效的认证令牌"));
        return;
    }

    // Check if user is admin
    try {
        auto dbClient = Database::getClient();
        completion->armTimeout();
        dbClient->execSqlAsync(
            "SELECT role FROM users WHERE userid = ?",
            [req, completion, userId](const orm::Result& result) {
                if (result.empty()) {
                    completion->respond(filterError(401, "用户不存在"));
                    return;
                }

                const std::string role = result[0]["role"].as<std::string>();
                if (role != "admin") {
                    Logger::warning("[AdminFilter] Access denied: not admin",
                                    {{"userid", userId}, {"role", role}});
                    completion->respond(filterError(403, "需要管理员权限"));
                    return;
                }

                completion->continueChain([req, userId]() {
                    req->getAttributes()->insert("user_id", userId);
                    req->getAttributes()->insert("is_admin", true);
                    Logger::info("[AdminFilter] Admin access granted", {{"userid", userId}});
                });
            },
            [completion](const orm::DrogonDbException& error) {
                Logger::error("Admin check failed: " + std::string(error.base().what()));
                completion->respond(filterError(503, "认证服务暂时不可用"));
            },
            numericUserId);
    } catch (const std::exception& error) {
        Logger::error("Admin check could not start: " + std::string(error.what()));
        completion->respond(filterError(503, "认证服务暂时不可用"));
    }
}

} // namespace woniunote
