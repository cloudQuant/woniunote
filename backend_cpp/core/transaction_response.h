/**
 * @file transaction_response.h
 * @brief One-shot response state for asynchronous transactional writes.
 *
 * The state may be captured by SQL and transaction callbacks, but it must not
 * own a transaction. A deadline reports an unknown result once; late database
 * callbacks are ignored.
 */

#ifndef WONIUNOTE_CORE_TRANSACTION_RESPONSE_H
#define WONIUNOTE_CORE_TRANSACTION_RESPONSE_H

#include "core/security.h"

#include <drogon/HttpResponse.h>
#include <drogon/drogon.h>
#include <drogon/orm/Exception.h>
#include <trantor/net/EventLoop.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <functional>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <string_view>
#include <utility>

namespace woniunote {

enum class TransactionOutcome {
    committed,
    aborted,
    unavailable,
    unknown
};

class TransactionResponse final
    : public std::enable_shared_from_this<TransactionResponse> {
public:
    using Completion =
        std::function<void(TransactionOutcome, const std::string& requestId)>;

    static std::shared_ptr<TransactionResponse> create(
        std::chrono::milliseconds timeout,
        Completion completion,
        TransactionOutcome timeoutOutcome = TransactionOutcome::unknown)
    {
        auto state = std::shared_ptr<TransactionResponse>(
            new TransactionResponse(std::move(completion), timeoutOutcome));
        state->armDeadline(timeout);
        return state;
    }

    TransactionResponse(const TransactionResponse&) = delete;
    TransactionResponse& operator=(const TransactionResponse&) = delete;

    const std::string& requestId() const noexcept
    {
        return requestId_;
    }

    void setTimeoutOutcome(TransactionOutcome outcome)
    {
        std::lock_guard<std::mutex> lock(mutex_);
        timeoutOutcome_ = outcome;
    }

    bool completed() const noexcept
    {
        return completed_.load(std::memory_order_acquire);
    }

    bool writingStarted() const noexcept
    {
        return writingStarted_.load(std::memory_order_acquire);
    }

    // Atomically marks the first write boundary and changes timeout reporting
    // from dependency failure to an unconfirmed write result.
    bool beginWriting()
    {
        bool deadlineElapsed = false;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (completed_.load(std::memory_order_acquire)) {
                return false;
            }
            deadlineElapsed = deadline_.has_value() &&
                std::chrono::steady_clock::now() >= *deadline_;
            if (!deadlineElapsed) {
                timeoutOutcome_ = TransactionOutcome::unknown;
                writingStarted_.store(true, std::memory_order_release);
                return true;
            }
        }
        completeTimeout();
        return false;
    }

    bool complete(TransactionOutcome outcome)
    {
        Completion completion;
        trantor::EventLoop* loop = nullptr;
        trantor::TimerId timerId = trantor::InvalidTimerId;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (completed_.exchange(true, std::memory_order_acq_rel)) {
                return false;
            }
            if (deadline_.has_value() &&
                std::chrono::steady_clock::now() >= *deadline_) {
                outcome = timeoutOutcome_;
            }
            completion = std::move(completion_);
            loop = loop_;
            timerId = timerId_;
            timerId_ = trantor::InvalidTimerId;
        }

        if (loop != nullptr && timerId != trantor::InvalidTimerId) {
            loop->runInLoop([loop, timerId]() { loop->invalidateTimer(timerId); });
        }
        if (completion) {
            completion(outcome, requestId_);
        }
        return true;
    }

    static TransactionOutcome sqlFailureOutcome(
        const drogon::orm::DrogonDbException& error) noexcept
    {
        if (isSqlTransportFailure(error)) {
            return TransactionOutcome::unknown;
        }
        const auto& base = error.base();
        if (dynamic_cast<const drogon::orm::BrokenConnection*>(&base) != nullptr ||
            dynamic_cast<const drogon::orm::InDoubtError*>(&base) != nullptr ||
            dynamic_cast<const drogon::orm::StatementCompletionUnknown*>(&base) != nullptr) {
            return TransactionOutcome::unknown;
        }
        if (dynamic_cast<const drogon::orm::SqlError*>(&base) != nullptr ||
            dynamic_cast<const drogon::orm::TransactionRollback*>(&base) != nullptr) {
            // Drogon requests a rollback before delivering ordinary SQL errors,
            // but its public Transaction API does not expose the rollback ACK.
            return TransactionOutcome::aborted;
        }
        return TransactionOutcome::unknown;
    }

    TransactionOutcome failureOutcome(
        const drogon::orm::DrogonDbException& error) const noexcept
    {
        const auto outcome = sqlFailureOutcome(error);
        if (!writingStarted() && outcome == TransactionOutcome::unknown) {
            // Transport loss before the first business write cannot have
            // changed application data, even if the database connection is
            // no longer usable.
            return TransactionOutcome::unavailable;
        }
        return outcome;
    }

    static bool isSqlTransportFailure(
        const drogon::orm::DrogonDbException& error) noexcept
    {
        const auto* sqlError =
            dynamic_cast<const drogon::orm::SqlError*>(&error.base());
        if (sqlError == nullptr) {
            return false;
        }
        constexpr int kServerGoneError = 2006;
        constexpr int kServerLostError = 2013;
        constexpr int kServerLostExtendedError = 2055;
        const auto isConnectionErrorCode = [=](int code) {
            return code == kServerGoneError || code == kServerLostError ||
                   code == kServerLostExtendedError;
        };
        if (isConnectionErrorCode(sqlError->errcode()) ||
            isConnectionErrorCode(sqlError->extendedErrcode())) {
            return true;
        }

        // Drogon 1.9.11's MySQL adapter can leave SqlError's numeric error
        // codes unset for client-side transport failures.
        const std::string_view message(sqlError->what());
        return message.find("Lost connection to server during query") !=
                   std::string_view::npos ||
               message.find("MySQL server has gone away") != std::string_view::npos;
    }

    static drogon::HttpResponsePtr unknownResponse(
        const std::string& requestId,
        const std::string& message = "写入结果暂未确认")
    {
        Json::Value body;
        body["code"] = 503;
        body["message"] = message;
        body["error_code"] = "WRITE_OUTCOME_UNKNOWN";
        body["request_id"] = requestId;
        auto response = drogon::HttpResponse::newHttpJsonResponse(body);
        response->setStatusCode(drogon::k503ServiceUnavailable);
        return response;
    }

private:
    explicit TransactionResponse(Completion completion,
                                 TransactionOutcome timeoutOutcome)
        : completion_(std::move(completion)),
          requestId_(makeRequestId()),
          timeoutOutcome_(timeoutOutcome)
    {
    }

    static std::string makeRequestId()
    {
        std::string id = Security::generateJti();
        if (!id.empty()) {
            return id;
        }

        static std::atomic<std::uint64_t> sequence{0};
        const auto ticks = std::chrono::steady_clock::now().time_since_epoch().count();
        return "req-" + std::to_string(ticks) + "-" +
               std::to_string(sequence.fetch_add(1, std::memory_order_relaxed));
    }

    void armDeadline(std::chrono::milliseconds timeout)
    {
        const auto delay = std::max(timeout, std::chrono::milliseconds{1});
        {
            std::lock_guard<std::mutex> lock(mutex_);
            deadline_ = std::chrono::steady_clock::now() + delay;
        }

        auto* loop = drogon::app().getLoop();
        if (loop == nullptr) {
            complete(timeoutOutcome());
            return;
        }

        auto self = shared_from_this();
        const auto timerId = loop->runAfter(
            std::chrono::duration<double>(delay).count(),
            [self]() { self->completeTimeout(); });

        bool cancelTimer = false;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            loop_ = loop;
            if (completed_.load(std::memory_order_acquire)) {
                cancelTimer = true;
            } else {
                timerId_ = timerId;
            }
        }
        if (cancelTimer && timerId != trantor::InvalidTimerId) {
            loop->runInLoop([loop, timerId]() { loop->invalidateTimer(timerId); });
        }
    }

    TransactionOutcome timeoutOutcome() const
    {
        std::lock_guard<std::mutex> lock(mutex_);
        return timeoutOutcome_;
    }

    bool completeTimeout()
    {
        Completion completion;
        trantor::EventLoop* loop = nullptr;
        trantor::TimerId timerId = trantor::InvalidTimerId;
        TransactionOutcome outcome = TransactionOutcome::unknown;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (completed_.exchange(true, std::memory_order_acq_rel)) {
                return false;
            }
            outcome = timeoutOutcome_;
            completion = std::move(completion_);
            loop = loop_;
            timerId = timerId_;
            timerId_ = trantor::InvalidTimerId;
        }
        if (loop != nullptr && timerId != trantor::InvalidTimerId) {
            loop->runInLoop([loop, timerId]() { loop->invalidateTimer(timerId); });
        }
        if (completion) {
            completion(outcome, requestId_);
        }
        return true;
    }

    mutable std::mutex mutex_;
    Completion completion_;
    const std::string requestId_;
    std::atomic_bool completed_{false};
    std::atomic_bool writingStarted_{false};
    trantor::EventLoop* loop_{nullptr};
    trantor::TimerId timerId_{trantor::InvalidTimerId};
    TransactionOutcome timeoutOutcome_{TransactionOutcome::unknown};
    std::optional<std::chrono::steady_clock::time_point> deadline_;
};

}  // namespace woniunote

#endif  // WONIUNOTE_CORE_TRANSACTION_RESPONSE_H
