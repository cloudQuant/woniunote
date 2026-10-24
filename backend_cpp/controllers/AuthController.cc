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
#include "core/transaction_response.h"
#include "core/auth_redis_config.h"
#include "models/User.h"
#include <drogon/HttpResponse.h>
#include <drogon/drogon.h>
#include <algorithm>
#include <atomic>
#include <cctype>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <memory>
#include <mutex>
#include <optional>
#include <vector>

using namespace drogon;

namespace woniunote {
namespace controllers {

namespace {
using ResponseCallback = std::function<void(const HttpResponsePtr&)>;

struct AuthRedisOperation {
    std::uint64_t id;
    std::chrono::steady_clock::time_point submittedAt;
};

AuthRedisOperation beginAuthRedisOperation()
{
    static std::atomic<std::uint64_t> nextId{0};
    return {nextId.fetch_add(1, std::memory_order_relaxed) + 1,
            std::chrono::steady_clock::now()};
}

void recordAuthRedisCompletion(const AuthRedisOperation& operation,
                               const char* name,
                               const char* outcome) noexcept
{
#ifdef WONIUNOTE_ENABLE_TEST_AUTH_FAULTS
    const double elapsedMilliseconds =
        std::chrono::duration<double, std::milli>(
            std::chrono::steady_clock::now() - operation.submittedAt).count();
    // Keep this marker off Logger: its stdout and file sinks can point at the
    // same file. The isolated harness captures this single stderr stream.
    std::fprintf(stderr,
                 "[AUTH_REDIS_COMPLETION] id=%llu operation=%s "
                 "elapsed_ms=%.3f outcome=%s\n",
                 static_cast<unsigned long long>(operation.id), name,
                 elapsedMilliseconds, outcome);
    std::fflush(stderr);
#else
    static_cast<void>(operation);
    static_cast<void>(name);
    static_cast<void>(outcome);
#endif
}

// Owns only the HTTP callback and timer. The guard does not hold a database or
// Redis operation; late dependency callbacks can safely arrive after timeout.
class ResponseOnce final : public std::enable_shared_from_this<ResponseOnce> {
public:
    static std::shared_ptr<ResponseOnce> create(ResponseCallback callback)
    {
        return std::shared_ptr<ResponseOnce>(
            new ResponseOnce(std::move(callback)));
    }

    void armDeadline(std::chrono::milliseconds timeout,
                     HttpResponsePtr timeoutResponse)
    {
        auto* loop = drogon::app().getLoop();
        if (loop == nullptr) {
            reply(std::move(timeoutResponse));
            return;
        }

        const auto delay = std::max(timeout, std::chrono::milliseconds{1});
        const auto candidateDeadline = std::chrono::steady_clock::now() + delay;
        trantor::TimerId oldTimerId;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (completed_.load(std::memory_order_acquire)) {
                return;
            }
            if (deadline_.has_value() && candidateDeadline >= *deadline_) {
                return;
            }
            deadline_ = candidateDeadline;
            timeoutResponse_ = timeoutResponse;
            oldTimerId = timerId_;
            timerId_ = trantor::InvalidTimerId;
        }
        if (oldTimerId != trantor::InvalidTimerId) {
            loop->runInLoop([loop, oldTimerId]() {
                loop->invalidateTimer(oldTimerId);
            });
        }

        auto self = shared_from_this();
        const auto remaining = std::max(
            candidateDeadline - std::chrono::steady_clock::now(),
            std::chrono::steady_clock::duration{std::chrono::milliseconds{1}});
        const auto newTimerId = loop->runAfter(
            std::chrono::duration<double>(remaining).count(),
            [self, timeoutResponse = std::move(timeoutResponse)]() mutable {
                self->reply(std::move(timeoutResponse));
            });

        bool cancelNewTimer = false;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            loop_ = loop;
            if (completed_.load(std::memory_order_acquire) ||
                !deadline_.has_value() || *deadline_ != candidateDeadline) {
                cancelNewTimer = true;
            } else {
                timerId_ = newTimerId;
            }
        }
        if (cancelNewTimer && newTimerId != trantor::InvalidTimerId) {
            loop->runInLoop([loop, newTimerId]() {
                loop->invalidateTimer(newTimerId);
            });
        }
    }

    bool reply(HttpResponsePtr response)
    {
        ResponseCallback callback;
        trantor::EventLoop* loop = nullptr;
        trantor::TimerId timerId;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (completed_.exchange(true, std::memory_order_acq_rel)) {
                return false;
            }
            callback = std::move(callback_);
            loop = loop_;
            timerId = timerId_;
            timerId_ = trantor::InvalidTimerId;
        }
        if (loop != nullptr && timerId != trantor::InvalidTimerId) {
            loop->runInLoop([loop, timerId]() {
                loop->invalidateTimer(timerId);
            });
        }
        if (callback) {
            callback(response);
        }
        return true;
    }

    // Reserves the right to initiate the next dependency operation. If the
    // deadline already completed the request, the late callback must not
    // enqueue a fresh Redis write.
    bool beginOperation()
    {
        HttpResponsePtr expiredResponse;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (completed_.load(std::memory_order_acquire)) {
                return false;
            }
            if (!deadline_.has_value() ||
                std::chrono::steady_clock::now() < *deadline_) {
                return true;
            }
            expiredResponse = timeoutResponse_;
        }
        reply(std::move(expiredResponse));
        return false;
    }

    bool completed() const noexcept
    {
        return completed_.load(std::memory_order_acquire);
    }

private:
    explicit ResponseOnce(ResponseCallback callback)
        : callback_(std::move(callback))
    {
    }

    mutable std::mutex mutex_;
    ResponseCallback callback_;
    std::atomic_bool completed_{false};
    trantor::EventLoop* loop_{nullptr};
    trantor::TimerId timerId_{trantor::InvalidTimerId};
    std::optional<std::chrono::steady_clock::time_point> deadline_;
    HttpResponsePtr timeoutResponse_;
};

// Parse a user id string to int64 defensively. A JWT may carry a validly
// signed but non-numeric "sub"; std::stoll would otherwise throw.
std::optional<int64_t> parseUserId(const std::string& s)
{
    if (s.empty()) return std::nullopt;
    if (std::any_of(s.begin(), s.end(), [](unsigned char c) {
            return !std::isdigit(c);
        })) {
        return std::nullopt;
    }
    try {
        return std::stoll(s);
    } catch (const std::exception&) {
        return std::nullopt;
    }
}

// Redis key holding the single active login session for a user. The value is
// <sid>:<jti>; both identifiers are generated as hex, so ':' is unambiguous.
std::string refreshJtiKey(const std::string& userId)
{
    return "refresh_jti:" + userId;
}

std::string sessionValue(const std::string& sid, const std::string& jti)
{
    return sid + ":" + jti;
}

nosql::RedisClientPtr authSessionRedisClient()
{
    try {
        return drogon::app().getRedisClient(
            woniunote::kAuthSessionRedisClientName);
    } catch (...) {
        return {};
    }
}

std::optional<long long> refreshTtlSeconds(const std::string& token)
{
    const auto payload = Security::decodeToken(token);
    if (!payload.has_value() || payload->type != "refresh") {
        return std::nullopt;
    }
    const auto remaining = std::chrono::duration_cast<std::chrono::seconds>(
        payload->exp - std::chrono::system_clock::now()).count();
    if (remaining <= 0) {
        return std::nullopt;
    }
    return remaining;
}

bool isDuplicateUsername(const orm::DrogonDbException& error)
{
    const auto* sqlError =
        dynamic_cast<const orm::SqlError*>(&error.base());
    if (sqlError == nullptr) {
        return false;
    }

    // This predicate is used only for the users INSERT below. That statement
    // omits the generated primary key, and uk_username is the users table's
    // only remaining unique index, so duplicate-key errno means username.
    if (sqlError->errcode() == 1062 || sqlError->extendedErrcode() == 1062) {
        return true;
    }

    // Drogon's MySQL backend in the pinned 1.9.11 build creates SqlError from
    // mysql_error() and the query only, dropping mysql_errno(). For that path,
    // identify only the username unique index; do not turn other SQL failures
    // or duplicate constraints into a client conflict.
    if (sqlError->errcode() != 0 || sqlError->extendedErrcode() != 0) {
        return false;
    }
    const std::string message = sqlError->what();
    constexpr char kDuplicatePrefix[] = "Duplicate entry ";
    constexpr char kKeyMarker[] = " for key ";
    constexpr char kUsernameIndex[] = "uk_username";
    if (message.rfind(kDuplicatePrefix, 0) != 0) {
        return false;
    }
    const auto keyStart = message.rfind(kKeyMarker);
    if (keyStart == std::string::npos) {
        return false;
    }
    const std::string quotedKey = message.substr(
        keyStart + sizeof(kKeyMarker) - 1);
    if (quotedKey.size() < 2 ||
        (quotedKey.front() != '\'' && quotedKey.front() != '`') ||
        quotedKey.back() != quotedKey.front()) {
        return false;
    }
    const std::string key = quotedKey.substr(1, quotedKey.size() - 2);
    const auto qualifier = key.rfind('.');
    const std::string index = qualifier == std::string::npos
        ? key
        : key.substr(qualifier + 1);
    return index == kUsernameIndex;
}

constexpr char kRotateSessionScript[] =
    "local current=redis.call('GET',KEYS[1]); "
    "if not current then return 0 end; "
    "if current ~= ARGV[1] then return -1 end; "
    "redis.call('SET',KEYS[1],ARGV[2],'EX',ARGV[3]); return 1";

constexpr char kLogoutSessionScript[] =
    "local current=redis.call('GET',KEYS[1]); "
    "if not current then return 0 end; "
    "local separator=string.find(current,':',1,true); "
    "if not separator then return 0 end; "
    "if string.sub(current,1,separator-1) ~= ARGV[1] then return 0 end; "
    "return redis.call('DEL',KEYS[1])";

#ifdef WONIUNOTE_ENABLE_TEST_AUTH_FAULTS
bool isAuthorizedAuthTestRequest(const HttpRequestPtr& req)
{
    const char* expectedRunId = std::getenv("WONIUNOTE_TEST_RUN_ID");
    const std::string peerAddress = req->getPeerAddr().toIp();
    const bool loopback = peerAddress == "127.0.0.1" || peerAddress == "::1" ||
                          peerAddress == "::ffff:127.0.0.1";
    return expectedRunId != nullptr && *expectedRunId != '\0' &&
           req->getHeader("X-Woniunote-Test-Run") == expectedRunId && loopback;
}

std::string authTestFaultMode(const HttpRequestPtr& req)
{
    if (!isAuthorizedAuthTestRequest(req)) {
        return {};
    }
    return req->getHeader("X-Woniunote-Test-Auth-Fault");
}
#endif
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
    if (!json->isObject() || !json->isMember("username") ||
        !json->isMember("password") || !(*json)["username"].isString() ||
        !(*json)["password"].isString() ||
        (json->isMember("nickname") && !(*json)["nickname"].isString()) ||
        (json->isMember("qq") && !(*json)["qq"].isString())) {
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

    auto callbackState = std::make_shared<ResponseCallback>(std::move(callback));
    auto responseSent = std::make_shared<std::atomic_bool>(false);
    auto sendOnce = [callbackState, responseSent](HttpResponsePtr response) {
        if (!responseSent->exchange(true, std::memory_order_acq_rel)) {
            (*callbackState)(response);
        }
    };
    struct RegistrationResult {
        std::mutex mutex;
        Json::Value user;
        int64_t userId{0};
        bool ready{false};
    };
    auto registrationResult = std::make_shared<RegistrationResult>();

    auto completion = TransactionResponse::create(
        std::chrono::seconds{3},
        [this, sendOnce, registrationResult]
        (TransactionOutcome outcome, const std::string& requestId) {
            if (outcome == TransactionOutcome::committed) {
                Json::Value user;
                int64_t userId = 0;
                bool ready = false;
                {
                    std::lock_guard<std::mutex> lock(registrationResult->mutex);
                    user = registrationResult->user;
                    userId = registrationResult->userId;
                    ready = registrationResult->ready;
                }
                if (!ready) {
                    Logger::error("[Auth] Registration commit callback lacked response data",
                                  {{"request_id", requestId}});
                    sendOnce(TransactionResponse::unknownResponse(requestId));
                    return;
                }
                Logger::info("[Auth] Registration committed",
                             {{"userid", std::to_string(userId)},
                              {"request_id", requestId}});
                sendOnce(makeJsonResponse(200, "注册成功", user));
                return;
            }

            if (outcome == TransactionOutcome::unknown) {
                Logger::error("[Auth] Registration commit outcome unknown",
                              {{"request_id", requestId}});
                sendOnce(TransactionResponse::unknownResponse(requestId));
                return;
            }

            if (outcome == TransactionOutcome::unavailable) {
                Logger::warning("[Auth] Registration dependency unavailable before write",
                                {{"request_id", requestId}});
                sendOnce(makeErrorResponse(503, "数据库暂时不可用"));
                return;
            }
            Logger::warning("[Auth] Registration failed; rollback requested",
                            {{"request_id", requestId}});
            sendOnce(makeErrorResponse(500, "注册失败"));
        },
        TransactionOutcome::unavailable);

    auto handleSqlFailure = [completion](
        const std::shared_ptr<orm::Transaction>& trans,
        const std::string& phase, const orm::DrogonDbException& error) {
        if (trans) {
            trans->rollback();
        }
        const auto outcome = completion->failureOutcome(error);
        const std::string requestId = completion->requestId();
        if (outcome == TransactionOutcome::unknown) {
            Logger::error("[Auth] Registration SQL outcome unknown",
                          {{"phase", phase}, {"request_id", requestId}});
        } else {
            Logger::warning("[Auth] Registration SQL failed; rollback requested",
                            {{"phase", phase}, {"request_id", requestId}});
        }
        completion->complete(outcome);
    };

#ifdef WONIUNOTE_ENABLE_TEST_AUTH_FAULTS
    const std::string testFault = authTestFaultMode(req);
#else
    const std::string testFault;
#endif

    try {
        Database::beginTransaction(
            [this, username, password, nickname, qq, completion, sendOnce,
             registrationResult, handleSqlFailure, testFault]
            (const std::shared_ptr<orm::Transaction>& trans) {
                if (!trans) {
                    completion->complete(TransactionOutcome::unavailable);
                    return;
                }
                if (completion->completed()) {
                    trans->rollback();
                    return;
                }
                trans->setCommitCallback(
                    [completion, testFault](bool committed) {
                        static_cast<void>(testFault);
#ifdef WONIUNOTE_ENABLE_TEST_AUTH_FAULTS
                        if (committed && testFault == "drop_commit_callback") {
                            Logger::warning(
                                "[Auth] Test fault discarded confirmed commit callback",
                                {{"request_id", completion->requestId()}});
                            return;
                        }
#endif
                        completion->complete(committed
                            ? TransactionOutcome::committed
                            : TransactionOutcome::unknown);
                    });

                trans->execSqlAsync(
                    "SELECT userid FROM users WHERE username = ?",
                    [this, username, password, nickname, qq, trans, completion,
                     sendOnce, registrationResult, handleSqlFailure, testFault]
                    (const orm::Result& result) {
                        if (completion->completed()) {
                            trans->rollback();
                            return;
                        }
                        if (!result.empty()) {
                            trans->rollback();
                            sendOnce(makeErrorResponse(400, "用户名已存在"));
                            completion->complete(TransactionOutcome::aborted);
                            return;
                        }

                        const std::string hashedPassword = Security::hashPassword(password);
                        if (hashedPassword.empty()) {
                            trans->rollback();
                            sendOnce(makeErrorResponse(503, "暂时无法安全处理注册请求"));
                            completion->complete(TransactionOutcome::aborted);
                            return;
                        }

                        if (!completion->beginWriting()) {
                            trans->rollback();
                            return;
                        }
                        trans->execSqlAsync(
                            "INSERT INTO users (username, password, nickname, qq, role, credit, createtime, updatetime) "
                            "VALUES (?, ?, ?, ?, 'user', 50, NOW(), NOW())",
                            [this, username, trans, completion, sendOnce,
                             registrationResult, handleSqlFailure, testFault]
                            (const orm::Result& insertResult) {
                                static_cast<void>(testFault);
                                if (completion->completed()) {
                                    trans->rollback();
                                    return;
                                }
                                const int64_t userId = insertResult.insertId();
                                if (userId <= 0) {
                                    Logger::error("[Auth] Registration insert returned no user id",
                                                  {{"request_id", completion->requestId()}});
                                    trans->rollback();
                                    completion->complete(TransactionOutcome::unknown);
                                    return;
                                }
                                Logger::info(
                                    "[Auth] Registration user row inserted within transaction",
                                    {{"userid", std::to_string(userId)},
                                     {"request_id", completion->requestId()}});

#ifdef WONIUNOTE_ENABLE_TEST_AUTH_FAULTS
                                if (testFault == "sql_fail_after_user_insert") {
                                    trans->execSqlAsync(
                                        "INSERT INTO woniunote_test_missing_table (userid) VALUES (?)",
                                        [](const orm::Result&) {},
                                        [trans, handleSqlFailure](
                                            const orm::DrogonDbException& error) {
                                            handleSqlFailure(
                                                trans, "test_sql_failure_after_user_insert", error);
                                        },
                                        userId);
                                    return;
                                }
#endif

                                if (!completion->beginWriting()) {
                                    trans->rollback();
                                    return;
                                }
                                trans->execSqlAsync(
                                    "INSERT INTO credit (userid, category, target, credit, createtime, updatetime) "
                                    "VALUES (?, '用户注册', ?, 50, NOW(), NOW())",
                                    [this, username, userId, trans, completion,
                                     registrationResult, handleSqlFailure]
                                    (const orm::Result&) {
                                        if (completion->completed()) {
                                            trans->rollback();
                                            return;
                                        }
                                        trans->execSqlAsync(
                                            "SELECT * FROM users WHERE userid = ?",
                                            [this, userId, trans, completion,
                                             registrationResult]
                                            (const orm::Result& userResult) {
                                                if (completion->completed()) {
                                                    trans->rollback();
                                                    return;
                                                }
                                                if (userResult.empty()) {
                                                    Logger::error(
                                                        "[Auth] Registration response row missing before commit",
                                                        {{"request_id", completion->requestId()}});
                                                    trans->rollback();
                                                    completion->complete(TransactionOutcome::aborted);
                                                    return;
                                                }
                                                models::User user(userResult[0]);
                                                {
                                                    std::lock_guard<std::mutex> lock(
                                                        registrationResult->mutex);
                                                    registrationResult->user = user.toJsonWithoutPassword();
                                                    registrationResult->userId = user.getUserid();
                                                    registrationResult->ready = true;
                                                }
                                            },
                                            [handleSqlFailure, trans](
                                                const orm::DrogonDbException& error) {
                                                handleSqlFailure(
                                                    trans, "select_registered_user", error);
                                            },
                                            userId);
                                    },
                                    [this, username, userId, completion, handleSqlFailure, trans]
                                    (const orm::DrogonDbException& error) {
                                        Logger::warning("[Auth] Initial credit insert failed",
                                                        {{"request_id", completion->requestId()}});
                                        handleSqlFailure(
                                            trans, "insert_initial_credit", error);
                                    },
                                    userId, userId);
                            },
                            [this, completion, sendOnce, handleSqlFailure, trans]
                            (const orm::DrogonDbException& error) {
                                if (isDuplicateUsername(error)) {
                                    Logger::warning("[Auth] Registration unique conflict",
                                                    {{"request_id", completion->requestId()}});
                                    trans->rollback();
                                    sendOnce(makeErrorResponse(400, "用户名已存在"));
                                    completion->complete(TransactionOutcome::aborted);
                                    return;
                                }
                                handleSqlFailure(trans, "insert_user", error);
                            },
                            username, hashedPassword, nickname, qq);
                    },
                    [handleSqlFailure, trans](const orm::DrogonDbException& error) {
                        handleSqlFailure(trans, "check_username", error);
                    },
                    username);
            });
    } catch (const std::exception&) {
        Logger::error("[Auth] Failed to start registration transaction",
                      {{"request_id", completion->requestId()}});
        completion->complete(TransactionOutcome::unavailable);
    }
}

#ifdef WONIUNOTE_ENABLE_TEST_AUTH_FAULTS
void AuthController::testEmptyTransaction(
    const HttpRequestPtr& req,
    std::function<void(const HttpResponsePtr&)>&& callback)
{
    if (!isAuthorizedAuthTestRequest(req)) {
        callback(makeErrorResponse(404, "Not found"));
        return;
    }

    auto completion = TransactionResponse::create(
        std::chrono::seconds{3},
        [callback = std::move(callback)](
            TransactionOutcome outcome, const std::string& requestId) mutable {
            if (outcome == TransactionOutcome::committed) {
                Json::Value data;
                data["committed"] = true;
                callback(Response::success(data));
            } else if (outcome == TransactionOutcome::unknown) {
                callback(TransactionResponse::unknownResponse(requestId));
            } else {
                callback(Response::error(503, "数据库暂时不可用", k503ServiceUnavailable));
            }
        });

    try {
        Database::beginTransaction(
            [completion](const std::shared_ptr<orm::Transaction>& trans) {
                if (!trans) {
                    completion->complete(TransactionOutcome::aborted);
                    return;
                }
                if (completion->completed()) {
                    trans->rollback();
                    return;
                }
                trans->setCommitCallback(
                    [completion](bool committed) {
                        completion->complete(committed
                            ? TransactionOutcome::committed
                            : TransactionOutcome::unknown);
                    });
            });
    } catch (const std::exception&) {
        completion->complete(TransactionOutcome::aborted);
    }
}
#endif

void AuthController::login(const HttpRequestPtr& req,
                           std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::info("[Auth] Login request received", {{"ip", req->getPeerAddr().toIp()}});
    
    auto json = req->getJsonObject();
    if (!json || !json->isObject()) {
        Logger::warning("[Auth] Login failed: invalid JSON");
        callback(makeErrorResponse(400, "请求格式错误"));
        return;
    }

    if (!json->isMember("username") || !json->isMember("password") ||
        !(*json)["username"].isString() || !(*json)["password"].isString() ||
        (json->isMember("captcha_id") && !(*json)["captcha_id"].isString()) ||
        (json->isMember("captcha_code") && !(*json)["captcha_code"].isString())) {
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
    
    // Validate captcha. The frontend always sends captcha_id/captcha_code;
    // reject the login if they are missing or incorrect.
    std::string captchaId = json->get("captcha_id", "").asString();
    std::string captchaCode = json->get("captcha_code", "").asString();
    if (!CaptchaController::validateCaptcha(captchaId, captchaCode)) {
        Logger::warning("[Auth] Login failed: invalid captcha");
        callback(makeErrorResponse(400, "验证码错误或已过期"));
        return;
    }

#ifdef WONIUNOTE_ENABLE_TEST_AUTH_FAULTS
    const std::string testFault = authTestFaultMode(req);
#else
    const std::string testFault;
#endif

    auto response = ResponseOnce::create(std::move(callback));
    response->armDeadline(std::chrono::seconds{3},
                          makeErrorResponse(503, "认证服务暂时不可用"));

    DbClientPtr dbClient;
    try {
        dbClient = Database::getClient();
    } catch (const std::exception&) {
        response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
        return;
    }

    try {
        dbClient->execSqlAsync(
            "SELECT * FROM users WHERE username = ?",
            [this, response, password, username, testFault](const orm::Result& result) {
                static_cast<void>(testFault);
                if (response->completed()) {
                    return;
                }
                if (result.empty()) {
                    response->reply(makeErrorResponse(401, "用户名或密码错误"));
                    return;
                }

                models::User user(result[0]);
                if (!Security::verifyPassword(password, user.getPassword())) {
                    response->reply(makeErrorResponse(401, "用户名或密码错误"));
                    return;
                }

                const std::string userId = std::to_string(user.getUserid());
                const std::string sid = Security::generateSessionId();
                const std::string jti = Security::generateJti();
                if (sid.empty() || jti.empty()) {
                    Logger::error("[Auth] Secure randomness unavailable during login",
                                  {{"userid", userId}});
                    response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
                    return;
                }

#ifdef WONIUNOTE_ENABLE_TEST_AUTH_FAULTS
                const int accessExpiryMinutes = testFault == "expired_access" ? -1 : 0;
#else
                const int accessExpiryMinutes = 0;
#endif
                const std::string accessToken =
                    Security::createAccessToken(userId, accessExpiryMinutes, sid);
                const std::string refreshToken =
                    Security::createRefreshToken(userId, 0, jti, sid);
                const auto ttlSeconds = refreshTtlSeconds(refreshToken);
                if (accessToken.empty() || refreshToken.empty() || !ttlSeconds.has_value()) {
                    response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
                    return;
                }

                auto redis = authSessionRedisClient();
                if (!redis) {
                    Logger::warning("[Auth] Redis unavailable during login",
                                    {{"userid", userId}});
                    response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
                    return;
                }

                Json::Value data;
                data["access_token"] = accessToken;
                data["refresh_token"] = refreshToken;
                data["token_type"] = "bearer";
                data["user"] = user.toJsonWithoutPassword();
                const std::string key = refreshJtiKey(userId);
                const std::string value = sessionValue(sid, jti);

                response->armDeadline(std::chrono::seconds{2},
                                      makeErrorResponse(503, "认证服务暂时不可用"));
                if (!response->beginOperation()) {
                    return;
                }
                const auto redisOperation = beginAuthRedisOperation();
                try {
                    redis->execCommandAsync(
                        [this, response, data, userId, redisOperation]
                        (const nosql::RedisResult& result) {
                            recordAuthRedisCompletion(
                                redisOperation, "login", "success");
                            if (result.type() != nosql::RedisResultType::kStatus ||
                                result.asString() != "OK") {
                                Logger::warning("[Auth] Redis did not confirm login session",
                                                {{"userid", userId}});
                                response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
                                return;
                            }
                            Logger::info("[Auth] Login session stored",
                                         {{"userid", userId}});
                            response->reply(makeJsonResponse(200, "登录成功", data));
                        },
                        [response, userId, redisOperation]
                        (const nosql::RedisException&) {
                            recordAuthRedisCompletion(
                                redisOperation, "login", "exception");
                            Logger::warning("[Auth] Redis login session write failed",
                                            {{"userid", userId}});
                            response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
                        },
                        "SET %s %s EX %lld", key.c_str(), value.c_str(), *ttlSeconds);
                } catch (const std::exception&) {
                    recordAuthRedisCompletion(
                        redisOperation, "login", "synchronous_error");
                    response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
                }
            },
            [response](const orm::DrogonDbException&) {
                response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
            },
            username);
    } catch (const std::exception&) {
        response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
    }
}

void AuthController::refresh(const HttpRequestPtr& req,
                             std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::debug("[Auth] Token refresh request");
    auto json = req->getJsonObject();
    if (!json || !json->isObject() || !json->isMember("refresh_token")) {
        Logger::warning("[Auth] Refresh failed: missing token");
        callback(makeErrorResponse(400, "刷新令牌缺失"));
        return;
    }

    if (!(*json)["refresh_token"].isString()) {
        callback(makeErrorResponse(400, "刷新令牌格式错误"));
        return;
    }
    std::string refreshToken = (*json)["refresh_token"].asString();
    auto payload = Security::decodeToken(refreshToken);

    if (!payload.has_value() || payload->type != "refresh" ||
        payload->sid.empty() || payload->jti.empty()) {
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

    const std::string presentedSid = payload->sid;
    const std::string presentedJti = payload->jti;
    auto response = ResponseOnce::create(std::move(callback));
    response->armDeadline(std::chrono::seconds{3},
                          makeErrorResponse(503, "认证服务暂时不可用"));

    DbClientPtr dbClient;
    try {
        dbClient = Database::getClient();
    } catch (const std::exception&) {
        response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
        return;
    }

    try {
        dbClient->execSqlAsync(
            "SELECT * FROM users WHERE userid = ?",
            [this, response, userId, parsedId, presentedSid, presentedJti]
            (const orm::Result& result) {
                if (response->completed()) {
                    return;
                }
                if (result.empty()) {
                    response->reply(makeErrorResponse(401, "用户不存在"));
                    return;
                }

                const std::string newJti = Security::generateJti();
                if (newJti.empty()) {
                    Logger::error("[Auth] Secure randomness unavailable during refresh",
                                  {{"userid", userId}});
                    response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
                    return;
                }
                const std::string newAccessToken =
                    Security::createAccessToken(userId, 0, presentedSid);
                const std::string newRefreshToken =
                    Security::createRefreshToken(userId, 0, newJti, presentedSid);
                const auto ttlSeconds = refreshTtlSeconds(newRefreshToken);
                if (newAccessToken.empty() || newRefreshToken.empty() ||
                    !ttlSeconds.has_value()) {
                    response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
                    return;
                }

                auto redis = authSessionRedisClient();
                if (!redis) {
                    Logger::warning("[Auth] Redis unavailable during refresh",
                                    {{"userid", userId}});
                    response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
                    return;
                }

                Json::Value data;
                data["access_token"] = newAccessToken;
                data["refresh_token"] = newRefreshToken;
                data["token_type"] = "bearer";
                const std::string key = refreshJtiKey(userId);
                const std::string oldValue = sessionValue(presentedSid, presentedJti);
                const std::string newValue = sessionValue(presentedSid, newJti);

                response->armDeadline(std::chrono::seconds{2},
                                      makeErrorResponse(503, "认证服务暂时不可用"));
                if (!response->beginOperation()) {
                    return;
                }
                const auto redisOperation = beginAuthRedisOperation();
                try {
                    redis->execCommandAsync(
                        [this, response, data, userId, redisOperation]
                        (const nosql::RedisResult& result) {
                            recordAuthRedisCompletion(
                                redisOperation, "refresh", "success");
                            if (result.type() != nosql::RedisResultType::kInteger) {
                                Logger::warning("[Auth] Redis returned invalid refresh status",
                                                {{"userid", userId}});
                                response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
                                return;
                            }
                            const long long status = result.asInteger();
                            if (status != 1) {
                                Logger::warning("[Auth] Refresh session compare failed",
                                                {{"userid", userId}});
                                response->reply(makeErrorResponse(
                                    401, "刷新令牌已失效，请重新登录"));
                                return;
                            }
                            Logger::info("[Auth] Refresh session rotated",
                                         {{"userid", userId}});
                            response->reply(makeJsonResponse(200, "刷新成功", data));
                        },
                        [response, userId, redisOperation]
                        (const nosql::RedisException&) {
                            recordAuthRedisCompletion(
                                redisOperation, "refresh", "exception");
                            Logger::warning("[Auth] Redis refresh rotation failed",
                                            {{"userid", userId}});
                            response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
                        },
                        "EVAL %s 1 %s %s %s %lld", kRotateSessionScript,
                        key.c_str(), oldValue.c_str(), newValue.c_str(), *ttlSeconds);
                } catch (const std::exception&) {
                    recordAuthRedisCompletion(
                        redisOperation, "refresh", "synchronous_error");
                    response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
                }
            },
            [response](const orm::DrogonDbException&) {
                response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
            },
            parsedId.value());
    } catch (const std::exception&) {
        response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
    }
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
    const std::string authHeader = req->getHeader("Authorization");
    std::string headerToken;
    const std::string bearerPrefix = "Bearer ";
    if (authHeader.rfind(bearerPrefix, 0) == 0) {
        headerToken = authHeader.substr(bearerPrefix.size());
    }

    std::string bodyRefreshToken;
    const auto json = req->getJsonObject();
    if (json && !json->isObject()) {
        callback(makeErrorResponse(400, "请求格式错误"));
        return;
    }
    if (json && json->isMember("refresh_token")) {
        if (!(*json)["refresh_token"].isString()) {
            callback(makeErrorResponse(400, "刷新令牌格式错误"));
            return;
        }
        bodyRefreshToken = (*json)["refresh_token"].asString();
    }

    std::vector<TokenPayload> credentials;
    const auto addCredential = [&credentials](const std::string& token) {
        if (token.empty()) {
            return;
        }
        const auto payload = Security::decodeToken(token);
        if (!payload.has_value() ||
            (payload->type != "access" && payload->type != "refresh") ||
            payload->sid.empty() || !parseUserId(payload->sub).has_value() ||
            (payload->type == "refresh" && payload->jti.empty())) {
            return;
        }
        credentials.push_back(*payload);
    };
    addCredential(headerToken);
    addCredential(bodyRefreshToken);

    if (credentials.empty()) {
        callback(makeErrorResponse(401, "有效的登录凭据缺失或已过期"));
        return;
    }

    const TokenPayload& identity = credentials.front();
    const bool conflictingIdentity = std::any_of(
        credentials.begin() + 1, credentials.end(),
        [&identity](const TokenPayload& credential) {
            return credential.sub != identity.sub || credential.sid != identity.sid;
        });
    if (conflictingIdentity) {
        callback(makeErrorResponse(401, "退出凭据身份不一致"));
        return;
    }

    const std::string userId = identity.sub;
    const std::string sid = identity.sid;
    auto response = ResponseOnce::create(std::move(callback));
    response->armDeadline(std::chrono::seconds{3},
                          makeErrorResponse(503, "认证服务暂时不可用"));
    auto redis = authSessionRedisClient();
    if (!redis) {
        Logger::warning("[Auth] Redis unavailable during logout",
                        {{"userid", userId}});
        response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
        return;
    }

    const std::string key = refreshJtiKey(userId);
    response->armDeadline(std::chrono::seconds{2},
                          makeErrorResponse(503, "认证服务暂时不可用"));
    if (!response->beginOperation()) {
        return;
    }
    const auto redisOperation = beginAuthRedisOperation();
    try {
        redis->execCommandAsync(
            [this, response, userId, redisOperation]
            (const nosql::RedisResult& result) {
                recordAuthRedisCompletion(
                    redisOperation, "logout", "success");
                if (result.type() != nosql::RedisResultType::kInteger) {
                    Logger::warning("[Auth] Redis returned invalid logout status",
                                    {{"userid", userId}});
                    response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
                    return;
                }
                Logger::info("[Auth] Logout session compare completed",
                             {{"userid", userId}});
                response->reply(makeJsonResponse(200, "登出成功"));
            },
            [response, userId, redisOperation]
            (const nosql::RedisException&) {
                recordAuthRedisCompletion(
                    redisOperation, "logout", "exception");
                Logger::warning("[Auth] Redis logout revoke failed",
                                {{"userid", userId}});
                response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
            },
            "EVAL %s 1 %s %s", kLogoutSessionScript, key.c_str(), sid.c_str());
    } catch (const std::exception&) {
        recordAuthRedisCompletion(
            redisOperation, "logout", "synchronous_error");
        response->reply(makeErrorResponse(503, "认证服务暂时不可用"));
    }
}

} // namespace controllers
} // namespace woniunote
