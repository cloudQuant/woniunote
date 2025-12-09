/**
 * @file FavoriteController.cc
 * @brief Favorite API Controller Implementation
 */

#include "FavoriteController.h"
#include "core/database.h"
#include "core/logger.h"
#include "models/Favorite.h"
#include "models/Article.h"
#include <drogon/HttpResponse.h>

using namespace drogon;

namespace woniunote {
namespace controllers {

void FavoriteController::list(const HttpRequestPtr& req,
                              std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT a.* FROM favorite f "
        "JOIN article a ON f.articleid = a.articleid "
        "WHERE f.userid = ? AND f.canceled = 0 "
        "ORDER BY f.createtime DESC",
        [callback](const orm::Result& result) {
            Json::Value articles(Json::arrayValue);
            for (const auto& row : result) {
                models::Article article(row);
                articles.append(article.toJsonBrief());
            }

            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "success";
            ret["data"] = articles;
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        std::stoll(userId)
    );
}

void FavoriteController::add(const HttpRequestPtr& req,
                             std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto json = req->getJsonObject();

    if (!json || !json->isMember("articleid")) {
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "文章ID不能为空";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }

    int64_t articleId = (*json)["articleid"].asInt64();
    auto dbClient = Database::getClient();

    // Check if already favorited
    dbClient->execSqlAsync(
        "SELECT favoriteid, canceled FROM favorite WHERE userid = ? AND articleid = ?",
        [callback, userId, articleId, dbClient](const orm::Result& result) {
            if (result.size() > 0) {
                int canceled = result[0]["canceled"].as<int>();
                if (canceled == 0) {
                    Json::Value ret;
                    ret["code"] = 400;
                    ret["message"] = "已经收藏过了";
                    callback(HttpResponse::newHttpJsonResponse(ret));
                    return;
                }

                // Re-activate canceled favorite
                int64_t favId = result[0]["favoriteid"].as<int64_t>();
                dbClient->execSqlAsync(
                    "UPDATE favorite SET canceled = 0, updatetime = NOW() WHERE favoriteid = ?",
                    [callback](const orm::Result&) {
                        Json::Value ret;
                        ret["code"] = 200;
                        ret["message"] = "收藏成功";
                        callback(HttpResponse::newHttpJsonResponse(ret));
                    },
                    [callback](const orm::DrogonDbException& e) {
                        Logger::error("Update error: " + std::string(e.base().what()));
                        Json::Value ret;
                        ret["code"] = 500;
                        ret["message"] = "收藏失败";
                        callback(HttpResponse::newHttpJsonResponse(ret));
                    },
                    favId
                );
                return;
            }

            // Create new favorite
            dbClient->execSqlAsync(
                "INSERT INTO favorite (userid, articleid, createtime, updatetime) VALUES (?, ?, NOW(), NOW())",
                [callback](const orm::Result&) {
                    Json::Value ret;
                    ret["code"] = 200;
                    ret["message"] = "收藏成功";
                    callback(HttpResponse::newHttpJsonResponse(ret));
                },
                [callback](const orm::DrogonDbException& e) {
                    Logger::error("Insert error: " + std::string(e.base().what()));
                    Json::Value ret;
                    ret["code"] = 500;
                    ret["message"] = "收藏失败";
                    callback(HttpResponse::newHttpJsonResponse(ret));
                },
                std::stoll(userId), articleId
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        std::stoll(userId), articleId
    );
}

void FavoriteController::remove(const HttpRequestPtr& req,
                                std::function<void(const HttpResponsePtr&)>&& callback,
                                int64_t articleId)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "UPDATE favorite SET canceled = 1, updatetime = NOW() WHERE userid = ? AND articleid = ?",
        [callback](const orm::Result&) {
            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "取消收藏成功";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Update error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "操作失败";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        std::stoll(userId), articleId
    );
}

void FavoriteController::check(const HttpRequestPtr& req,
                               std::function<void(const HttpResponsePtr&)>&& callback,
                               int64_t articleId)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT favoriteid FROM favorite WHERE userid = ? AND articleid = ? AND canceled = 0",
        [callback](const orm::Result& result) {
            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "success";
            ret["data"]["favorited"] = result.size() > 0;
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        std::stoll(userId), articleId
    );
}

} // namespace controllers
} // namespace woniunote
