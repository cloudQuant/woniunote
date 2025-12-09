/**
 * @file CardController.cc
 * @brief Card API Controller Implementation
 */

#include "CardController.h"
#include "core/database.h"
#include "core/logger.h"
#include "models/Card.h"
#include <drogon/HttpResponse.h>

using namespace drogon;

namespace woniunote {
namespace controllers {

void CardController::listCategories(const HttpRequestPtr& req,
                                    std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT * FROM card_category WHERE userid = ? ORDER BY sort_order, id",
        [callback](const orm::Result& result) {
            Json::Value categories(Json::arrayValue);
            for (const auto& row : result) {
                models::CardCategory cat(row);
                categories.append(cat.toJson());
            }
            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "success";
            ret["data"] = categories;
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("DB error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        std::stoll(userId)
    );
}

void CardController::createCategory(const HttpRequestPtr& req,
                                    std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto json = req->getJsonObject();
    if (!json || !json->isMember("name")) {
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "分类名称不能为空";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }

    std::string name = (*json)["name"].asString();
    int type = json->get("type", 0).asInt();
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "INSERT INTO card_category (userid, name, type, createtime, updatetime) VALUES (?, ?, ?, NOW(), NOW())",
        [callback](const orm::Result& result) {
            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "创建成功";
            ret["data"]["id"] = static_cast<Json::Int64>(result.insertId());
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Insert error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "创建失败";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        std::stoll(userId), name, type
    );
}

void CardController::deleteCategory(const HttpRequestPtr& req,
                                    std::function<void(const HttpResponsePtr&)>&& callback,
                                    int64_t id)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "DELETE FROM card_category WHERE id = ? AND userid = ?",
        [callback](const orm::Result&) {
            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "删除成功";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Delete error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "删除失败";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        id, std::stoll(userId)
    );
}

void CardController::listCards(const HttpRequestPtr& req,
                               std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    std::string categoryId = req->getParameter("category_id");
    auto dbClient = Database::getClient();

    std::string sql = "SELECT * FROM card WHERE userid = ?";
    if (!categoryId.empty()) {
        sql += " AND category_id = " + categoryId;
    }
    sql += " ORDER BY type, createtime DESC";

    dbClient->execSqlAsync(
        sql,
        [callback](const orm::Result& result) {
            Json::Value cards(Json::arrayValue);
            for (const auto& row : result) {
                models::Card card(row);
                cards.append(card.toJson());
            }
            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "success";
            ret["data"] = cards;
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("DB error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        std::stoll(userId)
    );
}

void CardController::createCard(const HttpRequestPtr& req,
                                std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto json = req->getJsonObject();
    if (!json || !json->isMember("headline") || !json->isMember("category_id")) {
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "标题和分类不能为空";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }

    std::string headline = (*json)["headline"].asString();
    int64_t categoryId = (*json)["category_id"].asInt64();
    std::string content = json->get("content", "").asString();
    int type = json->get("type", 1).asInt();
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "INSERT INTO card (userid, category_id, headline, content, type, createtime, updatetime) "
        "VALUES (?, ?, ?, ?, ?, NOW(), NOW())",
        [callback](const orm::Result& result) {
            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "创建成功";
            ret["data"]["id"] = static_cast<Json::Int64>(result.insertId());
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Insert error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "创建失败";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        std::stoll(userId), categoryId, headline, content, type
    );
}

void CardController::updateCard(const HttpRequestPtr& req,
                                std::function<void(const HttpResponsePtr&)>&& callback,
                                int64_t id)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto json = req->getJsonObject();
    if (!json) {
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "请求格式错误";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }

    std::string headline = json->get("headline", "").asString();
    std::string content = json->get("content", "").asString();
    int type = json->get("type", 1).asInt();
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "UPDATE card SET headline = ?, content = ?, type = ?, updatetime = NOW() WHERE id = ? AND userid = ?",
        [callback](const orm::Result&) {
            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "更新成功";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Update error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "更新失败";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        headline, content, type, id, std::stoll(userId)
    );
}

void CardController::deleteCard(const HttpRequestPtr& req,
                                std::function<void(const HttpResponsePtr&)>&& callback,
                                int64_t id)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "DELETE FROM card WHERE id = ? AND userid = ?",
        [callback](const orm::Result&) {
            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "删除成功";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Delete error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "删除失败";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        id, std::stoll(userId)
    );
}

void CardController::startTimer(const HttpRequestPtr& req,
                                std::function<void(const HttpResponsePtr&)>&& callback,
                                int64_t id)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "UPDATE card SET begintime = NOW(), updatetime = NOW() WHERE id = ? AND userid = ?",
        [callback](const orm::Result&) {
            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "计时开始";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Update error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "操作失败";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        id, std::stoll(userId)
    );
}

void CardController::stopTimer(const HttpRequestPtr& req,
                               std::function<void(const HttpResponsePtr&)>&& callback,
                               int64_t id)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto dbClient = Database::getClient();

    // Calculate elapsed time and add to usedtime
    dbClient->execSqlAsync(
        "UPDATE card SET "
        "usedtime = usedtime + TIMESTAMPDIFF(SECOND, begintime, NOW()), "
        "endtime = NOW(), begintime = NULL, updatetime = NOW() "
        "WHERE id = ? AND userid = ? AND begintime IS NOT NULL",
        [callback](const orm::Result&) {
            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "计时结束";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Update error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "操作失败";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        id, std::stoll(userId)
    );
}

} // namespace controllers
} // namespace woniunote
