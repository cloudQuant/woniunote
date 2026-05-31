/**
 * @file CreditController.cc
 * @brief Credit API Controller Implementation
 */

#include "CreditController.h"
#include "core/database.h"
#include "core/logger.h"
#include "core/response.h"
#include "models/Credit.h"
#include <drogon/HttpResponse.h>

using namespace drogon;

namespace woniunote {
namespace controllers {

void CreditController::getBalance(const HttpRequestPtr& req,
                                  std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::debug("[Credit] Get balance", {{"userid", userId}});
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT credit FROM users WHERE userid = ?",
        [callback, userId](const orm::Result& result) {
            if (result.size() == 0) {
                callback(Response::notFound("用户不存在"));
                return;
            }

            int credit = result[0]["credit"].as<int>();
            Logger::debug("[Credit] Balance retrieved", {{"userid", userId}, {"balance", std::to_string(credit)}});
            Json::Value data;
            data["balance"] = credit;
            callback(Response::success(data));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[Credit] Database error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        std::stoll(userId)
    );
}

void CreditController::getHistory(const HttpRequestPtr& req,
                                  std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::debug("[Credit] Get history", {{"userid", userId}});

    // Safe pagination parsing (avoid std::stoi throwing on bad input).
    int page = 1, pageSize = 20;
    auto parseIntParam = [&req](const std::string& name, int fallback) -> int {
        const std::string raw = req->getParameter(name);
        if (raw.empty()) return fallback;
        try { return std::stoi(raw); } catch (const std::exception&) { return fallback; }
    };
    page = parseIntParam("page", 1);
    pageSize = parseIntParam("page_size", 20);
    if (page < 1) page = 1;
    if (pageSize < 1) pageSize = 20;
    if (pageSize > 100) pageSize = 100;

    int offset = (page - 1) * pageSize;
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT * FROM credit WHERE userid = ? ORDER BY createtime DESC LIMIT ? OFFSET ?",
        [callback](const orm::Result& result) {
            Json::Value history(Json::arrayValue);
            for (const auto& row : result) {
                models::Credit credit(row);
                history.append(credit.toJson());
            }
            Logger::debug("[Credit] History returned", {{"count", std::to_string(static_cast<int>(result.size()))}});
            callback(Response::success(history));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[Credit] Database error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        std::stoll(userId), pageSize, offset
    );
}

void CreditController::checkArticle(const HttpRequestPtr& req,
                                    std::function<void(const HttpResponsePtr&)>&& callback,
                                    int64_t id)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::debug("[Credit] Check article payment", {{"userid", userId}, {"articleid", std::to_string(id)}});
    auto dbClient = Database::getClient();

    // A payment record exists when category='付费阅读' and target=articleid.
    dbClient->execSqlAsync(
        "SELECT creditid FROM credit WHERE userid = ? AND category = '付费阅读' AND target = ? LIMIT 1",
        [callback](const orm::Result& result) {
            Json::Value data;
            data["paid"] = result.size() > 0;
            callback(Response::success(data));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[Credit] Database error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        std::stoll(userId), id
    );
}

void CreditController::payArticle(const HttpRequestPtr& req,
                                  std::function<void(const HttpResponsePtr&)>&& callback,
                                  int64_t id)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    int64_t uid = std::stoll(userId);
    Logger::info("[Credit] Pay article request", {{"userid", userId}, {"articleid", std::to_string(id)}});

    // Use a transaction so balance check, deduction and payment record are atomic.
    Database::beginTransaction(
        [callback, uid, id](const std::shared_ptr<Transaction>& trans) {
            if (!trans) {
                callback(Response::serverError("无法开启事务"));
                return;
            }

            // 1) Already paid?
            trans->execSqlAsync(
                "SELECT creditid FROM credit WHERE userid = ? AND category = '付费阅读' AND target = ? LIMIT 1",
                [callback, uid, id, trans](const orm::Result& paidResult) {
                    if (paidResult.size() > 0) {
                        Json::Value data;
                        data["paid"] = true;
                        callback(Response::ok("已支付，无需重复支付", data));
                        return;
                    }

                    // 2) Look up article credit cost
                    trans->execSqlAsync(
                        "SELECT credit FROM article WHERE articleid = ?",
                        [callback, uid, id, trans](const orm::Result& artResult) {
                            if (artResult.size() == 0) {
                                callback(Response::notFound("文章不存在"));
                                return;
                            }
                            int cost = artResult[0]["credit"].as<int>();

                            // 3) Check user balance
                            trans->execSqlAsync(
                                "SELECT credit FROM users WHERE userid = ?",
                                [callback, uid, id, trans, cost](const orm::Result& userResult) {
                                    if (userResult.size() == 0) {
                                        callback(Response::notFound("用户不存在"));
                                        return;
                                    }
                                    int balance = userResult[0]["credit"].as<int>();
                                    if (balance < cost) {
                                        Json::Value data;
                                        data["balance"] = balance;
                                        data["cost"] = cost;
                                        callback(Response::make(400, "积分不足", data, k400BadRequest));
                                        return;
                                    }

                                    // 4) Deduct balance
                                    trans->execSqlAsync(
                                        "UPDATE users SET credit = credit - ?, updatetime = NOW() WHERE userid = ?",
                                        [callback, uid, id, trans, cost, balance](const orm::Result&) {
                                            // 5) Insert payment record
                                            trans->execSqlAsync(
                                                "INSERT INTO credit (userid, category, target, credit, createtime, updatetime) "
                                                "VALUES (?, '付费阅读', ?, ?, NOW(), NOW())",
                                                [callback, cost, balance](const orm::Result&) {
                                                    Logger::info("[Credit] Article paid successfully");
                                                    Json::Value data;
                                                    data["paid"] = true;
                                                    data["balance"] = balance - cost;
                                                    callback(Response::ok("支付成功", data));
                                                },
                                                [callback](const orm::DrogonDbException& e) {
                                                    Logger::error("[Credit] Insert payment failed: " + std::string(e.base().what()));
                                                    callback(Response::serverError("支付失败"));
                                                },
                                                uid, id, cost
                                            );
                                        },
                                        [callback](const orm::DrogonDbException& e) {
                                            Logger::error("[Credit] Deduct failed: " + std::string(e.base().what()));
                                            callback(Response::serverError("支付失败"));
                                        },
                                        cost, uid
                                    );
                                },
                                [callback](const orm::DrogonDbException& e) {
                                    Logger::error("[Credit] Balance query failed: " + std::string(e.base().what()));
                                    callback(Response::serverError("数据库错误"));
                                },
                                uid
                            );
                        },
                        [callback](const orm::DrogonDbException& e) {
                            Logger::error("[Credit] Article query failed: " + std::string(e.base().what()));
                            callback(Response::serverError("数据库错误"));
                        },
                        id
                    );
                },
                [callback](const orm::DrogonDbException& e) {
                    Logger::error("[Credit] Paid-check query failed: " + std::string(e.base().what()));
                    callback(Response::serverError("数据库错误"));
                },
                uid, id
            );
        }
    );
}

} // namespace controllers
} // namespace woniunote
