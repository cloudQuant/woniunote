/**
 * @file MathTrainingController.cc
 * @brief Math Training API Controller Implementation
 */

#include "MathTrainingController.h"
#include "core/database.h"
#include "core/logger.h"
#include "core/response.h"
#include "core/transaction_response.h"
#include "models/MathTraining.h"
#include <drogon/HttpResponse.h>
#include <array>
#include <algorithm>
#include <atomic>
#include <charconv>
#include <cctype>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <limits>
#include <memory>
#include <optional>
#include <string>
#include <vector>

using namespace drogon;

namespace woniunote {
namespace controllers {

namespace {

constexpr std::int64_t kMaxPageOffset = 1'000'000;
constexpr std::int64_t kMaxUserAnswer = 2'147'483'647;
constexpr auto kWriteTimeout = std::chrono::seconds{10};

struct ParsedUtcTime {
    std::string mysqlValue;
    std::int64_t epochMilliseconds{0};
};

struct WrongAnswerInput {
    std::string question;
    int correctAnswer{0};
    std::optional<double> userAnswer;
    std::string operation;
};

struct TrainingInput {
    int difficulty{0};
    int totalQuestions{0};
    int correctCount{0};
    int wrongCount{0};
    double accuracy{0.0};
    std::string startTime;
    std::string endTime;
    int durationSeconds{0};
    std::vector<WrongAnswerInput> wrongAnswers;
};

bool parseUnsignedDecimal(const std::string& raw, std::uint64_t& value)
{
    if (raw.empty()) {
        return false;
    }
    const auto result = std::from_chars(raw.data(), raw.data() + raw.size(), value, 10);
    return result.ec == std::errc{} && result.ptr == raw.data() + raw.size();
}

bool isStrictJsonInt(const Json::Value& value)
{
    const auto type = value.type();
    return (type == Json::intValue || type == Json::uintValue) && value.isInt();
}

std::optional<std::string> queryParameter(const HttpRequestPtr& req,
                                          const std::string& name)
{
    const auto& params = req->getParameters();
    const auto it = params.find(name);
    if (it == params.end()) {
        return std::nullopt;
    }
    return it->second;
}

bool parsePageQuery(const HttpRequestPtr& req,
                    std::uint64_t defaultPageSize,
                    std::uint64_t& page,
                    std::uint64_t& pageSize,
                    std::int64_t& offset)
{
    page = 1;
    pageSize = defaultPageSize;
    if (const auto rawPage = queryParameter(req, "page")) {
        if (!parseUnsignedDecimal(*rawPage, page) || page == 0) {
            return false;
        }
    }
    if (const auto rawPageSize = queryParameter(req, "page_size")) {
        if (!parseUnsignedDecimal(*rawPageSize, pageSize) || pageSize == 0 || pageSize > 100) {
            return false;
        }
    }

    const auto pageIndex = page - 1;
    if (pageIndex > static_cast<std::uint64_t>(kMaxPageOffset) / pageSize) {
        return false;
    }
    const auto offsetValue = pageIndex * pageSize;
    if (offsetValue > static_cast<std::uint64_t>(kMaxPageOffset)) {
        return false;
    }
    offset = static_cast<std::int64_t>(offsetValue);
    return true;
}

struct DifficultyFilter {
    bool supplied{false};
    int value{0};
};

bool parseDifficultyFilter(const HttpRequestPtr& req, DifficultyFilter& filter)
{
    const auto raw = queryParameter(req, "difficulty");
    if (!raw) {
        return true;
    }
    std::uint64_t parsed = 0;
    if (!parseUnsignedDecimal(*raw, parsed) || parsed < 1 || parsed > 3) {
        return false;
    }
    filter.supplied = true;
    filter.value = static_cast<int>(parsed);
    return true;
}

struct OperationFilter {
    bool supplied{false};
    std::string value;
};

bool parseOperationFilter(const HttpRequestPtr& req, OperationFilter& filter)
{
    const auto raw = queryParameter(req, "operation");
    if (!raw) {
        return true;
    }
    if (*raw != "+" && *raw != "-" && *raw != "*" && *raw != "/") {
        return false;
    }
    filter.supplied = true;
    filter.value = *raw;
    return true;
}

std::optional<std::size_t> utf8Length(const std::string& text)
{
    std::size_t count = 0;
    for (std::size_t index = 0; index < text.size(); ++count) {
        const auto lead = static_cast<unsigned char>(text[index]);
        std::size_t width = 0;
        std::uint32_t codePoint = 0;
        if (lead <= 0x7f) {
            width = 1;
            codePoint = lead;
        } else if ((lead & 0xe0) == 0xc0) {
            width = 2;
            codePoint = lead & 0x1f;
        } else if ((lead & 0xf0) == 0xe0) {
            width = 3;
            codePoint = lead & 0x0f;
        } else if ((lead & 0xf8) == 0xf0) {
            width = 4;
            codePoint = lead & 0x07;
        } else {
            return std::nullopt;
        }
        if (index + width > text.size()) {
            return std::nullopt;
        }
        for (std::size_t offset = 1; offset < width; ++offset) {
            const auto byte = static_cast<unsigned char>(text[index + offset]);
            if ((byte & 0xc0) != 0x80) {
                return std::nullopt;
            }
            codePoint = (codePoint << 6) | (byte & 0x3f);
        }
        if ((width == 2 && codePoint < 0x80) ||
            (width == 3 && codePoint < 0x800) ||
            (width == 4 && codePoint < 0x10000) ||
            codePoint > 0x10ffff ||
            (codePoint >= 0xd800 && codePoint <= 0xdfff)) {
            return std::nullopt;
        }
        index += width;
    }
    return count;
}

bool parseDigits(const std::string& value,
                 std::size_t offset,
                 std::size_t length,
                 int& parsed)
{
    if (offset + length > value.size()) {
        return false;
    }
    parsed = 0;
    for (std::size_t index = offset; index < offset + length; ++index) {
        const auto character = static_cast<unsigned char>(value[index]);
        if (!std::isdigit(character)) {
            return false;
        }
        parsed = parsed * 10 + (character - '0');
    }
    return true;
}

std::int64_t daysFromCivil(int year, unsigned month, unsigned day)
{
    year -= month <= 2;
    const int era = (year >= 0 ? year : year - 399) / 400;
    const auto yearOfEra = static_cast<unsigned>(year - era * 400);
    const auto adjustedMonth = month > 2 ? month - 3 : month + 9;
    const auto dayOfYear = (153 * adjustedMonth + 2) / 5 + day - 1;
    const auto dayOfEra = yearOfEra * 365 + yearOfEra / 4 - yearOfEra / 100 + dayOfYear;
    return static_cast<std::int64_t>(era) * 146097 + dayOfEra - 719468;
}

bool parseIsoUtcTime(const std::string& value, ParsedUtcTime& parsed)
{
    if (value.size() < 20 || value[4] != '-' || value[7] != '-' || value[10] != 'T' ||
        value[13] != ':' || value[16] != ':') {
        return false;
    }

    int year = 0;
    int month = 0;
    int day = 0;
    int hour = 0;
    int minute = 0;
    int second = 0;
    if (!parseDigits(value, 0, 4, year) || !parseDigits(value, 5, 2, month) ||
        !parseDigits(value, 8, 2, day) || !parseDigits(value, 11, 2, hour) ||
        !parseDigits(value, 14, 2, minute) || !parseDigits(value, 17, 2, second)) {
        return false;
    }
    if (year < 1000 || month < 1 || month > 12 || hour > 23 || minute > 59 || second > 59) {
        return false;
    }

    static constexpr std::array<int, 12> daysInMonth{31, 28, 31, 30, 31, 30,
                                                     31, 31, 30, 31, 30, 31};
    const bool leapYear = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
    const int maxDay = daysInMonth[static_cast<std::size_t>(month - 1)] +
                       (month == 2 && leapYear ? 1 : 0);
    if (day < 1 || day > maxDay) {
        return false;
    }

    int milliseconds = 0;
    if (value.size() == 20 && value[19] == 'Z') {
        // Whole-second ISO timestamp.
    } else {
        if (value.size() < 22 || value[19] != '.' || value.back() != 'Z') {
            return false;
        }
        const auto fractionLength = value.size() - 21;
        if (fractionLength > 3 || !parseDigits(value, 20, fractionLength, milliseconds)) {
            return false;
        }
        if (fractionLength == 1) {
            milliseconds *= 100;
        } else if (fractionLength == 2) {
            milliseconds *= 10;
        }
    }

    const auto days = daysFromCivil(year, static_cast<unsigned>(month),
                                    static_cast<unsigned>(day));
    const auto secondsSinceEpoch = days * 86400 + hour * 3600 + minute * 60 + second;
    parsed.epochMilliseconds = secondsSinceEpoch * 1000 + milliseconds;
    parsed.mysqlValue = value.substr(0, 19);
    parsed.mysqlValue[10] = ' ';
    if (value.size() != 20) {
        parsed.mysqlValue += value.substr(19, value.size() - 20);
    }
    return true;
}

bool parseTrainingInput(const Json::Value& json, TrainingInput& input)
{
    if (!json.isObject()) {
        return false;
    }
    static constexpr std::array<const char*, 9> requiredFields{
        "difficulty", "total_questions", "correct_count", "wrong_count", "accuracy",
        "start_time", "end_time", "duration_seconds", "wrong_answers"};
    for (const auto* field : requiredFields) {
        if (!json.isMember(field)) {
            return false;
        }
    }

    if (!isStrictJsonInt(json["difficulty"]) || !isStrictJsonInt(json["total_questions"]) ||
        !isStrictJsonInt(json["correct_count"]) || !isStrictJsonInt(json["wrong_count"]) ||
        !isStrictJsonInt(json["duration_seconds"]) || !json["accuracy"].isNumeric() ||
        !std::isfinite(json["accuracy"].asDouble()) || !json["start_time"].isString() ||
        !json["end_time"].isString() || !json["wrong_answers"].isArray()) {
        return false;
    }

    input.difficulty = json["difficulty"].asInt();
    input.totalQuestions = json["total_questions"].asInt();
    input.correctCount = json["correct_count"].asInt();
    input.wrongCount = json["wrong_count"].asInt();
    input.durationSeconds = json["duration_seconds"].asInt();
    if (input.difficulty < 1 || input.difficulty > 3 || input.totalQuestions < 0 ||
        input.totalQuestions > 1000 || input.correctCount < 0 || input.wrongCount < 0 ||
        input.correctCount > 1000 || input.wrongCount > 1000 ||
        static_cast<std::int64_t>(input.correctCount) + input.wrongCount != input.totalQuestions ||
        input.durationSeconds < 0 ||
        json["wrong_answers"].size() != static_cast<Json::ArrayIndex>(input.wrongCount)) {
        return false;
    }

    ParsedUtcTime startTime;
    ParsedUtcTime endTime;
    if (!parseIsoUtcTime(json["start_time"].asString(), startTime) ||
        !parseIsoUtcTime(json["end_time"].asString(), endTime) ||
        endTime.epochMilliseconds < startTime.epochMilliseconds) {
        return false;
    }
    const auto elapsedMilliseconds = endTime.epochMilliseconds - startTime.epochMilliseconds;
    const auto roundedElapsedSeconds = (elapsedMilliseconds + 500) / 1000;
    if (std::llabs(static_cast<std::int64_t>(input.durationSeconds) -
                   roundedElapsedSeconds) > 1) {
        return false;
    }
    input.startTime = std::move(startTime.mysqlValue);
    input.endTime = std::move(endTime.mysqlValue);
    input.accuracy = input.totalQuestions == 0
        ? 0.0
        : std::round(static_cast<double>(input.correctCount) * 10000.0 /
                     static_cast<double>(input.totalQuestions)) / 100.0;

    input.wrongAnswers.reserve(json["wrong_answers"].size());
    for (const auto& answer : json["wrong_answers"]) {
        if (!answer.isObject() || !answer.isMember("question") ||
            !answer.isMember("correct_answer") || !answer.isMember("user_answer") ||
            !answer.isMember("operation") || !answer["question"].isString() ||
            !isStrictJsonInt(answer["correct_answer"]) || !answer["operation"].isString()) {
            return false;
        }
        const auto question = answer["question"].asString();
        const auto questionLength = utf8Length(question);
        if (question.empty() || !questionLength || *questionLength > 100) {
            return false;
        }
        const auto operation = answer["operation"].asString();
        if (operation != "+" && operation != "-" && operation != "*" && operation != "/") {
            return false;
        }

        std::optional<double> userAnswer;
        const auto& userAnswerJson = answer["user_answer"];
        if (!userAnswerJson.isNull()) {
            if (!userAnswerJson.isNumeric()) {
                return false;
            }
            const double value = userAnswerJson.asDouble();
            if (!std::isfinite(value) || std::abs(value) > static_cast<double>(kMaxUserAnswer)) {
                return false;
            }
            userAnswer = value;
        }
        input.wrongAnswers.push_back({question, answer["correct_answer"].asInt(),
                                      userAnswer, operation});
    }
    return true;
}

bool parseAuthenticatedUserId(const std::string& raw, std::int64_t& userId)
{
    const auto result = std::from_chars(raw.data(), raw.data() + raw.size(), userId, 10);
    return !raw.empty() && result.ec == std::errc{} && result.ptr == raw.data() + raw.size() &&
           userId > 0 && userId <= std::numeric_limits<std::int32_t>::max();
}

void failTrainingWrite(const std::shared_ptr<orm::Transaction>& trans,
                       const std::shared_ptr<TransactionResponse>& completion,
                       const orm::DrogonDbException& error)
{
    Logger::error("[MathTraining] Database write error: " + std::string(error.base().what()));
    trans->rollback();
    completion->complete(TransactionResponse::sqlFailureOutcome(error));
}

void commitTrainingWrite(const std::shared_ptr<orm::Transaction>& trans,
                         const std::shared_ptr<TransactionResponse>& completion,
                         const std::shared_ptr<std::atomic_bool>& responseFinished)
{
    if (completion->completed() || responseFinished->load(std::memory_order_acquire)) {
        trans->rollback();
        return;
    }
    trans->setCommitCallback([completion](bool committed) {
        completion->complete(committed ? TransactionOutcome::committed
                                       : TransactionOutcome::unknown);
    });
}

void insertWrongAnswer(const std::shared_ptr<orm::Transaction>& trans,
                       const std::shared_ptr<TransactionResponse>& completion,
                       const std::shared_ptr<std::atomic_bool>& responseFinished,
                       const std::shared_ptr<const std::vector<WrongAnswerInput>>& answers,
                       std::size_t index,
                       std::int64_t recordId,
                       std::int64_t userId,
                       int difficulty)
{
    if (completion->completed() || responseFinished->load(std::memory_order_acquire)) {
        trans->rollback();
        return;
    }
    if (index >= answers->size()) {
        commitTrainingWrite(trans, completion, responseFinished);
        return;
    }

    const auto& answer = (*answers)[index];
    trans->execSqlAsync(
        "INSERT INTO math_training_wrong_answers (record_id, user_id, question, "
        "correct_answer, user_answer, operation, difficulty, created_at) "
        "VALUES (?, ?, ?, ?, IF(? = 1, ?, NULL), ?, ?, NOW())",
        [trans, completion, responseFinished, answers, index, recordId, userId, difficulty]
        (const orm::Result&) {
            insertWrongAnswer(trans, completion, responseFinished, answers, index + 1,
                              recordId, userId, difficulty);
        },
        [trans, completion](const orm::DrogonDbException& error) {
            failTrainingWrite(trans, completion, error);
        },
        recordId, userId, answer.question, answer.correctAnswer,
        answer.userAnswer.has_value() ? 1 : 0, answer.userAnswer.value_or(0.0),
        answer.operation, difficulty);
}

}  // namespace

void MathTrainingController::createRecord(const HttpRequestPtr& req,
                                          std::function<void(const HttpResponsePtr&)>&& callback)
{
    const auto userId = req->getAttributes()->get<std::string>("user_id");
    std::int64_t userIdValue = 0;
    if (!parseAuthenticatedUserId(userId, userIdValue)) {
        callback(Response::unauthorized("身份无效"));
        return;
    }

    const auto json = req->getJsonObject();
    TrainingInput input;
    if (!json || !parseTrainingInput(*json, input)) {
        callback(Response::badRequest("训练记录格式或字段值无效"));
        return;
    }

    Logger::info("[MathTraining] Create record", {{"userid", userId}});
    const auto answers = std::make_shared<const std::vector<WrongAnswerInput>>(
        std::move(input.wrongAnswers));
    const auto recordId = std::make_shared<std::atomic<std::int64_t>>(0);
    const auto responseFinished = std::make_shared<std::atomic_bool>(false);
    // Until a transaction is acquired and beginWriting() succeeds, a deadline
    // is a dependency timeout with a known non-write outcome.
    const auto unavailable = std::make_shared<std::atomic_bool>(true);
    auto completion = TransactionResponse::create(
        std::chrono::duration_cast<std::chrono::milliseconds>(kWriteTimeout),
        [callback = std::move(callback), recordId, responseFinished, unavailable, userId]
        (TransactionOutcome outcome, const std::string& requestId) mutable {
            responseFinished->store(true, std::memory_order_release);
            if (outcome == TransactionOutcome::committed) {
                const auto id = recordId->load(std::memory_order_acquire);
                Logger::info("[MathTraining] Record transaction committed",
                             {{"record_id", std::to_string(id)}, {"request_id", requestId}});
                Json::Value data;
                data["id"] = static_cast<Json::Int64>(id);
                callback(Response::success(data));
            } else if (outcome == TransactionOutcome::unknown) {
                const auto id = recordId->load(std::memory_order_acquire);
                Logger::warning("[MathTraining] Write outcome unknown",
                                {{"userid", userId}, {"record_id", std::to_string(id)},
                                 {"request_id", requestId}});
                callback(TransactionResponse::unknownResponse(requestId));
            } else if (unavailable->load(std::memory_order_acquire)) {
                callback(Response::make(503, "数据库暂不可用", Json::Value(),
                                         drogon::k503ServiceUnavailable));
            } else {
                callback(Response::serverError("训练记录保存失败"));
            }
        },
        TransactionOutcome::aborted);

    if (responseFinished->load(std::memory_order_acquire)) {
        return;
    }

    try {
        Database::beginTransaction(
            [completion, answers, recordId, responseFinished, unavailable, userIdValue,
             difficulty = input.difficulty, totalQuestions = input.totalQuestions,
             correctCount = input.correctCount, wrongCount = input.wrongCount,
             accuracy = input.accuracy, startTime = std::move(input.startTime),
             endTime = std::move(input.endTime), durationSeconds = input.durationSeconds]
            (const std::shared_ptr<orm::Transaction>& trans) {
                if (!trans) {
                    unavailable->store(true, std::memory_order_release);
                    completion->complete(TransactionOutcome::aborted);
                    return;
                }
                if (completion->completed() ||
                    responseFinished->load(std::memory_order_acquire)) {
                    trans->rollback();
                    return;
                }
                if (!completion->beginWriting()) {
                    trans->rollback();
                    return;
                }
                unavailable->store(false, std::memory_order_release);

                trans->execSqlAsync(
                    "INSERT INTO math_training_records (user_id, difficulty, total_questions, "
                    "correct_count, wrong_count, accuracy, start_time, end_time, duration_seconds, "
                    "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NOW())",
                    [trans, completion, answers, recordId, responseFinished, userIdValue,
                     difficulty](const orm::Result& result) {
                        if (completion->completed() ||
                            responseFinished->load(std::memory_order_acquire)) {
                            trans->rollback();
                            return;
                        }
                        const auto newRecordId = static_cast<std::int64_t>(result.insertId());
                        recordId->store(newRecordId, std::memory_order_release);
                        if (answers->empty()) {
                            commitTrainingWrite(trans, completion, responseFinished);
                        } else {
                            insertWrongAnswer(trans, completion, responseFinished, answers, 0,
                                              newRecordId, userIdValue, difficulty);
                        }
                    },
                    [trans, completion](const orm::DrogonDbException& error) {
                        failTrainingWrite(trans, completion, error);
                    },
                    userIdValue, difficulty, totalQuestions, correctCount, wrongCount,
                    accuracy, startTime, endTime, durationSeconds);
            });
    } catch (const std::exception& error) {
        unavailable->store(true, std::memory_order_release);
        Logger::error("[MathTraining] Failed to begin transaction: " + std::string(error.what()));
        completion->complete(TransactionOutcome::aborted);
    }
}

void MathTrainingController::getRecords(const HttpRequestPtr& req,
                                        std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::debug("[MathTraining] Get records", {{"userid", userId}});

    std::uint64_t page = 1;
    std::uint64_t pageSize = 10;
    std::int64_t offset = 0;
    DifficultyFilter difficulty;
    if (!parsePageQuery(req, 10, page, pageSize, offset) ||
        !parseDifficultyFilter(req, difficulty)) {
        callback(Response::badRequest("分页或难度参数无效"));
        return;
    }

    std::int64_t userIdInt = 0;
    if (!parseAuthenticatedUserId(userId, userIdInt)) {
        callback(Response::unauthorized("身份无效"));
        return;
    }

    auto dbClient = Database::getClient();

    // Difficulty is bound as a parameter (or omitted) — never concatenated.
    std::string countSql = "SELECT COUNT(*) as total FROM math_training_records WHERE user_id = ?";
    std::string dataSql = "SELECT * FROM math_training_records WHERE user_id = ?";
    if (difficulty.supplied) {
        countSql += " AND difficulty = ?";
        dataSql += " AND difficulty = ?";
    }
    dataSql += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?";

    auto onData = [callback, page, pageSize](const orm::Result& result, std::int64_t total) {
        Json::Value items(Json::arrayValue);
        for (const auto& row : result) {
            models::MathTrainingRecord record(row);
            items.append(record.toJsonBrief());
        }
        Json::Value body;
        body["code"] = 200;
        body["message"] = "success";
        body["data"] = items;
        body["total"] = total;
        body["page"] = page;
        body["page_size"] = pageSize;
        callback(HttpResponse::newHttpJsonResponse(body));
    };
    auto onErr = [callback](const orm::DrogonDbException& e) {
        Logger::error("[MathTraining] Database error: " + std::string(e.base().what()));
        callback(Response::serverError("数据库错误"));
    };

    // Run COUNT first (bind difficulty only when present), then the page query.
    auto runData = [dbClient, dataSql, difficulty, userIdInt, pageSize, offset, onData, onErr]
        (std::int64_t total) {
        auto onOk = [onData, total](const orm::Result& result) { onData(result, total); };
        const auto pageSizeValue = static_cast<std::int64_t>(pageSize);
        if (difficulty.supplied) {
            dbClient->execSqlAsync(dataSql, onOk, onErr, userIdInt, difficulty.value,
                                   pageSizeValue, offset);
        } else {
            dbClient->execSqlAsync(dataSql, onOk, onErr, userIdInt, pageSizeValue, offset);
        }
    };

    auto onCount = [runData](const orm::Result& countResult) {
        runData(countResult[0]["total"].as<std::int64_t>());
    };

    if (difficulty.supplied) {
        dbClient->execSqlAsync(countSql, onCount, onErr, userIdInt, difficulty.value);
    } else {
        dbClient->execSqlAsync(countSql, onCount, onErr, userIdInt);
    }
}

void MathTrainingController::getRecordDetail(const HttpRequestPtr& req,
                                             std::function<void(const HttpResponsePtr&)>&& callback,
                                             int64_t record_id)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::debug("[MathTraining] Get record detail", {{"userid", userId}, {"record_id", std::to_string(record_id)}});

    std::int64_t userIdValue = 0;
    if (!parseAuthenticatedUserId(userId, userIdValue)) {
        callback(Response::unauthorized("身份无效"));
        return;
    }

    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT * FROM math_training_records WHERE id = ? AND user_id = ?",
        [callback, record_id, dbClient](const orm::Result& result) {
            if (result.size() == 0) {
                callback(Response::notFound("训练记录不存在"));
                return;
            }

            models::MathTrainingRecord record(result[0]);

            dbClient->execSqlAsync(
                "SELECT * FROM math_training_wrong_answers WHERE record_id = ? ORDER BY id",
                [callback, record](const orm::Result& waResult) mutable {
                    for (const auto& row : waResult) {
                        record.wrong_answers_.emplace_back(row);
                    }
                    callback(Response::success(record.toJson()));
                },
                [callback](const orm::DrogonDbException& e) {
                    Logger::error("[MathTraining] Database error: " + std::string(e.base().what()));
                    callback(Response::serverError("数据库错误"));
                },
                record_id
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[MathTraining] Database error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        record_id, userIdValue
    );
}

void MathTrainingController::getWrongAnswers(const HttpRequestPtr& req,
                                             std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::debug("[MathTraining] Get wrong answers", {{"userid", userId}});

    std::uint64_t page = 1;
    std::uint64_t pageSize = 20;
    std::int64_t offset = 0;
    DifficultyFilter difficulty;
    OperationFilter operation;
    if (!parsePageQuery(req, 20, page, pageSize, offset) ||
        !parseDifficultyFilter(req, difficulty) || !parseOperationFilter(req, operation)) {
        callback(Response::badRequest("分页或筛选参数无效"));
        return;
    }

    // All filters are bound as parameters, including the literal arithmetic sign.
    std::string dataSql = "SELECT * FROM math_training_wrong_answers WHERE user_id = ?";
    if (difficulty.supplied) dataSql += " AND difficulty = ?";
    if (operation.supplied) dataSql += " AND operation = ?";
    dataSql += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?";

    std::int64_t userIdInt = 0;
    if (!parseAuthenticatedUserId(userId, userIdInt)) {
        callback(Response::unauthorized("身份无效"));
        return;
    }

    auto dbClient = Database::getClient();

    auto onOk = [callback, page, pageSize](const orm::Result& result) {
        Json::Value items(Json::arrayValue);
        for (const auto& row : result) {
            models::MathTrainingWrongAnswer wa(row);
            items.append(wa.toJson());
        }
        Json::Value body;
        body["code"] = 200;
        body["message"] = "success";
        body["data"] = items;
        body["page"] = page;
        body["page_size"] = pageSize;
        callback(HttpResponse::newHttpJsonResponse(body));
    };
    auto onErr = [callback](const orm::DrogonDbException& e) {
        Logger::error("[MathTraining] Database error: " + std::string(e.base().what()));
        callback(Response::serverError("数据库错误"));
    };

    const auto pageSizeValue = static_cast<std::int64_t>(pageSize);
    if (difficulty.supplied && operation.supplied) {
        dbClient->execSqlAsync(dataSql, onOk, onErr, userIdInt, difficulty.value,
                               operation.value, pageSizeValue, offset);
    } else if (difficulty.supplied) {
        dbClient->execSqlAsync(dataSql, onOk, onErr, userIdInt, difficulty.value,
                               pageSizeValue, offset);
    } else if (operation.supplied) {
        dbClient->execSqlAsync(dataSql, onOk, onErr, userIdInt, operation.value,
                               pageSizeValue, offset);
    } else {
        dbClient->execSqlAsync(dataSql, onOk, onErr, userIdInt, pageSizeValue, offset);
    }
}

void MathTrainingController::getSummary(const HttpRequestPtr& req,
                                        std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::debug("[MathTraining] Get summary", {{"userid", userId}});

    std::int64_t userIdValue = 0;
    if (!parseAuthenticatedUserId(userId, userIdValue)) {
        callback(Response::unauthorized("身份无效"));
        return;
    }

    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT COUNT(*) as total_sessions, "
        "COALESCE(SUM(total_questions), 0) as total_questions, "
        "COALESCE(SUM(correct_count), 0) as total_correct, "
        "COALESCE(SUM(wrong_count), 0) as total_wrong, "
        "COALESCE(SUM(duration_seconds), 0) as total_duration "
        "FROM math_training_records WHERE user_id = ?",
        [callback](const orm::Result& result) {
            int totalSessions = result[0]["total_sessions"].as<int>();
            int totalQuestions = result[0]["total_questions"].as<int>();
            int totalCorrect = result[0]["total_correct"].as<int>();
            int totalWrong = result[0]["total_wrong"].as<int>();
            int totalDuration = result[0]["total_duration"].as<int>();

            double averageAccuracy = totalQuestions > 0
                ? (static_cast<double>(totalCorrect) / totalQuestions * 100.0)
                : 0.0;

            Json::Value data;
            data["total_sessions"] = totalSessions;
            data["total_questions"] = totalQuestions;
            data["total_correct"] = totalCorrect;
            data["total_wrong"] = totalWrong;
            data["average_accuracy"] = std::round(averageAccuracy * 100) / 100;
            data["total_duration_seconds"] = totalDuration;
            callback(Response::success(data));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[MathTraining] Database error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        userIdValue
    );
}

} // namespace controllers
} // namespace woniunote
