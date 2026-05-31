/**
 * @file MathTrainingController.cc
 * @brief Math Training API Controller Implementation
 */

#include "MathTrainingController.h"
#include "core/database.h"
#include "core/logger.h"
#include "core/response.h"
#include "models/MathTraining.h"
#include <drogon/HttpResponse.h>
#include <string>
#include <algorithm>
#include <cctype>
#include <cmath>
#include <ctime>

using namespace drogon;

namespace woniunote {
namespace controllers {

namespace {

// Convert ISO 8601 datetime (e.g., "2025-12-14T11:57:38.713Z") to MySQL format
std::string isoToMysqlDatetime(const std::string& isoTime) {
    if (isoTime.empty()) return "";
    std::string result = isoTime;
    size_t tPos = result.find('T');
    if (tPos != std::string::npos) {
        result[tPos] = ' ';
    }
    size_t zPos = result.find('Z');
    if (zPos != std::string::npos) {
        result.resize(zPos);
    }
    size_t dotPos = result.find('.');
    if (dotPos != std::string::npos) {
        result.resize(dotPos);
    }
    return result;
}

// Parse a difficulty filter to a non-negative integer. Returns -1 when the
// value is absent or not a clean integer (filter is then skipped). Prevents
// SQL injection via the `difficulty` query parameter.
int parseDifficultyFilter(const std::string& raw) {
    if (raw.empty()) return -1;
    for (char c : raw) {
        if (!std::isdigit(static_cast<unsigned char>(c))) return -1;
    }
    try {
        return std::stoi(raw);
    } catch (const std::exception&) {
        return -1;
    }
}

// An operation filter is only accepted if it is a short alphabetic token.
// Anything else is rejected, closing the SQL injection vector on `operation`.
bool isValidOperation(const std::string& op) {
    if (op.empty() || op.size() > 16) return false;
    for (char c : op) {
        if (!std::isalpha(static_cast<unsigned char>(c))) return false;
    }
    return true;
}

}  // namespace

void MathTrainingController::createRecord(const HttpRequestPtr& req,
                                          std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::info("[MathTraining] Create record", {{"userid", userId}});

    auto json = req->getJsonObject();
    if (!json) {
        callback(Response::badRequest("无效的请求数据"));
        return;
    }

    int difficulty = (*json)["difficulty"].asInt();
    int totalQuestions = (*json)["total_questions"].asInt();
    int correctCount = (*json)["correct_count"].asInt();
    int wrongCount = (*json)["wrong_count"].asInt();
    double accuracy = (*json)["accuracy"].asDouble();
    std::string startTime = isoToMysqlDatetime((*json)["start_time"].asString());
    std::string endTime = isoToMysqlDatetime((*json)["end_time"].asString());
    int durationSeconds = (*json)["duration_seconds"].asInt();

    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "INSERT INTO math_training_records (user_id, difficulty, total_questions, correct_count, "
        "wrong_count, accuracy, start_time, end_time, duration_seconds, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NOW())",
        [callback, json, userId, dbClient](const orm::Result& result) {
            int64_t recordId = result.insertId();
            Logger::info("[MathTraining] Record created", {{"record_id", std::to_string(recordId)}});

            const auto& wrongAnswers = (*json)["wrong_answers"];
            if (wrongAnswers.isArray() && wrongAnswers.size() > 0) {
                int difficulty = (*json)["difficulty"].asInt();
                for (const auto& wa : wrongAnswers) {
                    std::string question = wa["question"].asString();
                    int correctAnswer = wa["correct_answer"].asInt();
                    int userAnswer = wa["user_answer"].asInt();
                    std::string operation = wa["operation"].asString();

                    dbClient->execSqlAsync(
                        "INSERT INTO math_training_wrong_answers (record_id, user_id, question, "
                        "correct_answer, user_answer, operation, difficulty, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, NOW())",
                        [](const orm::Result&) {},
                        [](const orm::DrogonDbException& e) {
                            Logger::error("[MathTraining] Insert wrong answer error: " + std::string(e.base().what()));
                        },
                        recordId, std::stoll(userId), question, correctAnswer, userAnswer, operation, difficulty
                    );
                }
            }

            Json::Value data;
            data["id"] = static_cast<Json::Int64>(recordId);
            callback(Response::success(data));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[MathTraining] Database error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        std::stoll(userId), difficulty, totalQuestions, correctCount, wrongCount,
        accuracy, startTime, endTime, durationSeconds
    );
}

void MathTrainingController::getRecords(const HttpRequestPtr& req,
                                        std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::debug("[MathTraining] Get records", {{"userid", userId}});

    int page = 1, pageSize = 10;
    if (req->getParameter("page").length() > 0) {
        page = std::stoi(req->getParameter("page"));
    }
    if (req->getParameter("page_size").length() > 0) {
        pageSize = std::stoi(req->getParameter("page_size"));
    }

    int difficulty = parseDifficultyFilter(req->getParameter("difficulty"));
    int offset = (page - 1) * pageSize;

    auto dbClient = Database::getClient();

    // Difficulty is bound as a parameter (or omitted) — never concatenated.
    std::string countSql = "SELECT COUNT(*) as total FROM math_training_records WHERE user_id = ?";
    std::string dataSql = "SELECT * FROM math_training_records WHERE user_id = ?";
    if (difficulty >= 0) {
        countSql += " AND difficulty = ?";
        dataSql += " AND difficulty = ?";
    }
    dataSql += " ORDER BY created_at DESC LIMIT ? OFFSET ?";

    int64_t userIdInt = std::stoll(userId);

    auto onData = [callback, page, pageSize](const orm::Result& result, int total) {
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
    auto runData = [dbClient, dataSql, difficulty, userIdInt, pageSize, offset, onData, onErr](int total) {
        auto onOk = [onData, total](const orm::Result& result) { onData(result, total); };
        if (difficulty >= 0) {
            dbClient->execSqlAsync(dataSql, onOk, onErr, userIdInt, difficulty, pageSize, offset);
        } else {
            dbClient->execSqlAsync(dataSql, onOk, onErr, userIdInt, pageSize, offset);
        }
    };

    auto onCount = [runData](const orm::Result& countResult) {
        runData(countResult[0]["total"].as<int>());
    };

    if (difficulty >= 0) {
        dbClient->execSqlAsync(countSql, onCount, onErr, userIdInt, difficulty);
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
        record_id, std::stoll(userId)
    );
}

void MathTrainingController::getWrongAnswers(const HttpRequestPtr& req,
                                             std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::debug("[MathTraining] Get wrong answers", {{"userid", userId}});

    int page = 1, pageSize = 20;
    if (req->getParameter("page").length() > 0) {
        page = std::stoi(req->getParameter("page"));
    }
    if (req->getParameter("page_size").length() > 0) {
        pageSize = std::stoi(req->getParameter("page_size"));
    }

    int difficulty = parseDifficultyFilter(req->getParameter("difficulty"));
    std::string operation = req->getParameter("operation");
    bool hasOperation = isValidOperation(operation);
    int offset = (page - 1) * pageSize;

    auto dbClient = Database::getClient();

    // All filters are bound as parameters (or omitted). `operation` is also
    // validated as a short alphabetic token before use.
    std::string dataSql = "SELECT * FROM math_training_wrong_answers WHERE user_id = ?";
    if (difficulty >= 0) dataSql += " AND difficulty = ?";
    if (hasOperation)    dataSql += " AND operation = ?";
    dataSql += " ORDER BY created_at DESC LIMIT ? OFFSET ?";

    int64_t userIdInt = std::stoll(userId);

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

    if (difficulty >= 0 && hasOperation) {
        dbClient->execSqlAsync(dataSql, onOk, onErr, userIdInt, difficulty, operation, pageSize, offset);
    } else if (difficulty >= 0) {
        dbClient->execSqlAsync(dataSql, onOk, onErr, userIdInt, difficulty, pageSize, offset);
    } else if (hasOperation) {
        dbClient->execSqlAsync(dataSql, onOk, onErr, userIdInt, operation, pageSize, offset);
    } else {
        dbClient->execSqlAsync(dataSql, onOk, onErr, userIdInt, pageSize, offset);
    }
}

void MathTrainingController::getSummary(const HttpRequestPtr& req,
                                        std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::debug("[MathTraining] Get summary", {{"userid", userId}});

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
        std::stoll(userId)
    );
}

} // namespace controllers
} // namespace woniunote
