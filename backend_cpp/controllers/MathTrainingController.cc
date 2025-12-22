/**
 * @file MathTrainingController.cc
 * @brief Math Training API Controller Implementation
 */

#include "MathTrainingController.h"
#include "core/database.h"
#include "core/logger.h"
#include "models/MathTraining.h"
#include <drogon/HttpResponse.h>
#include <string>
#include <algorithm>
#include <ctime>

using namespace drogon;

namespace woniunote {
namespace controllers {

// Convert ISO 8601 datetime (e.g., "2025-12-14T11:57:38.713Z") to MySQL format
static std::string isoToMysqlDatetime(const std::string& isoTime) {
    if (isoTime.empty()) return "";
    std::string result = isoTime;
    // Replace 'T' with space
    size_t tPos = result.find('T');
    if (tPos != std::string::npos) {
        result[tPos] = ' ';
    }
    // Remove 'Z' suffix and milliseconds
    size_t zPos = result.find('Z');
    if (zPos != std::string::npos) {
        result = result.substr(0, zPos);
    }
    // Remove milliseconds if present (after the dot)
    size_t dotPos = result.find('.');
    if (dotPos != std::string::npos) {
        result = result.substr(0, dotPos);
    }
    return result;
}

void MathTrainingController::createRecord(const HttpRequestPtr& req,
                                          std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::info("[MathTraining] Create record", {{"userid", userId}});

    auto json = req->getJsonObject();
    if (!json) {
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "无效的请求数据";
        callback(HttpResponse::newHttpJsonResponse(ret));
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

    // Insert training record
    dbClient->execSqlAsync(
        "INSERT INTO math_training_records (user_id, difficulty, total_questions, correct_count, "
        "wrong_count, accuracy, start_time, end_time, duration_seconds, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NOW())",
        [callback, json, userId, dbClient](const orm::Result& result) {
            int64_t recordId = result.insertId();
            Logger::info("[MathTraining] Record created", {{"record_id", std::to_string(recordId)}});

            // Insert wrong answers if any
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

            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "success";
            ret["data"]["id"] = static_cast<Json::Int64>(recordId);
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[MathTraining] Database error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            callback(HttpResponse::newHttpJsonResponse(ret));
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

    std::string difficultyFilter = req->getParameter("difficulty");
    int offset = (page - 1) * pageSize;

    auto dbClient = Database::getClient();

    // Build query based on difficulty filter
    std::string countSql = "SELECT COUNT(*) as total FROM math_training_records WHERE user_id = ?";
    std::string dataSql = "SELECT * FROM math_training_records WHERE user_id = ?";

    if (!difficultyFilter.empty()) {
        countSql += " AND difficulty = " + difficultyFilter;
        dataSql += " AND difficulty = " + difficultyFilter;
    }
    dataSql += " ORDER BY created_at DESC LIMIT ? OFFSET ?";

    int64_t userIdInt = std::stoll(userId);
    
    // First get total count
    dbClient->execSqlAsync(
        countSql,
        [callback, dataSql, dbClient, page, pageSize, offset, userIdInt](const orm::Result& countResult) {
            int total = countResult[0]["total"].as<int>();

            dbClient->execSqlAsync(
                dataSql,
                [callback, total, page, pageSize](const orm::Result& result) {
                    Json::Value items(Json::arrayValue);
                    for (const auto& row : result) {
                        models::MathTrainingRecord record(row);
                        items.append(record.toJsonBrief());
                    }

                    Json::Value ret;
                    ret["code"] = 200;
                    ret["message"] = "success";
                    ret["data"] = items;
                    ret["total"] = total;
                    ret["page"] = page;
                    ret["page_size"] = pageSize;
                    callback(HttpResponse::newHttpJsonResponse(ret));
                },
                [callback](const orm::DrogonDbException& e) {
                    Logger::error("[MathTraining] Database error: " + std::string(e.base().what()));
                    Json::Value ret;
                    ret["code"] = 500;
                    ret["message"] = "数据库错误";
                    callback(HttpResponse::newHttpJsonResponse(ret));
                },
                userIdInt, pageSize, offset
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[MathTraining] Database error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        userIdInt
    );
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
                Json::Value ret;
                ret["code"] = 404;
                ret["message"] = "训练记录不存在";
                callback(HttpResponse::newHttpJsonResponse(ret));
                return;
            }

            models::MathTrainingRecord record(result[0]);

            // Get wrong answers
            dbClient->execSqlAsync(
                "SELECT * FROM math_training_wrong_answers WHERE record_id = ? ORDER BY id",
                [callback, record](const orm::Result& waResult) mutable {
                    for (const auto& row : waResult) {
                        record.wrong_answers_.emplace_back(row);
                    }

                    Json::Value ret;
                    ret["code"] = 200;
                    ret["message"] = "success";
                    ret["data"] = record.toJson();
                    callback(HttpResponse::newHttpJsonResponse(ret));
                },
                [callback](const orm::DrogonDbException& e) {
                    Logger::error("[MathTraining] Database error: " + std::string(e.base().what()));
                    Json::Value ret;
                    ret["code"] = 500;
                    ret["message"] = "数据库错误";
                    callback(HttpResponse::newHttpJsonResponse(ret));
                },
                record_id
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[MathTraining] Database error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            callback(HttpResponse::newHttpJsonResponse(ret));
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

    std::string difficultyFilter = req->getParameter("difficulty");
    std::string operationFilter = req->getParameter("operation");
    int offset = (page - 1) * pageSize;

    auto dbClient = Database::getClient();

    std::string countSql = "SELECT COUNT(*) as total FROM math_training_wrong_answers WHERE user_id = ?";
    std::string dataSql = "SELECT * FROM math_training_wrong_answers WHERE user_id = ?";

    if (!difficultyFilter.empty()) {
        countSql += " AND difficulty = " + difficultyFilter;
        dataSql += " AND difficulty = " + difficultyFilter;
    }
    if (!operationFilter.empty()) {
        countSql += " AND operation = '" + operationFilter + "'";
        dataSql += " AND operation = '" + operationFilter + "'";
    }
    dataSql += " ORDER BY created_at DESC LIMIT ? OFFSET ?";

    dbClient->execSqlAsync(
        countSql,
        [callback, dataSql, dbClient, page, pageSize, offset](const orm::Result& countResult) {
            int total = countResult[0]["total"].as<int>();

            dbClient->execSqlAsync(
                dataSql,
                [callback, total, page, pageSize](const orm::Result& result) {
                    Json::Value items(Json::arrayValue);
                    for (const auto& row : result) {
                        models::MathTrainingWrongAnswer wa(row);
                        items.append(wa.toJson());
                    }

                    Json::Value ret;
                    ret["code"] = 200;
                    ret["message"] = "success";
                    ret["data"] = items;
                    ret["total"] = total;
                    ret["page"] = page;
                    ret["page_size"] = pageSize;
                    callback(HttpResponse::newHttpJsonResponse(ret));
                },
                [callback](const orm::DrogonDbException& e) {
                    Logger::error("[MathTraining] Database error: " + std::string(e.base().what()));
                    Json::Value ret;
                    ret["code"] = 500;
                    ret["message"] = "数据库错误";
                    callback(HttpResponse::newHttpJsonResponse(ret));
                },
                pageSize, offset
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[MathTraining] Database error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        std::stoll(userId)
    );
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

            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "success";
            ret["data"]["total_sessions"] = totalSessions;
            ret["data"]["total_questions"] = totalQuestions;
            ret["data"]["total_correct"] = totalCorrect;
            ret["data"]["total_wrong"] = totalWrong;
            ret["data"]["average_accuracy"] = std::round(averageAccuracy * 100) / 100;
            ret["data"]["total_duration_seconds"] = totalDuration;
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[MathTraining] Database error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        std::stoll(userId)
    );
}

} // namespace controllers
} // namespace woniunote
