/**
 * @file FavoriteController.cc
 * @brief Favorite API Controller Implementation
 */

#include "FavoriteController.h"
#include "core/database.h"
#include "core/logger.h"
#include "core/response.h"
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
    Logger::debug("[Favorite] List request", {{"userid", userId}});
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT a.*, u.nickname FROM favorite f "
        "JOIN article a ON f.articleid = a.articleid "
        "LEFT JOIN users u ON a.userid = u.userid "
        "WHERE f.userid = ? AND f.canceled = 0 "
        "ORDER BY f.createtime DESC",
        [callback](const orm::Result& result) {
            Json::Value articles(Json::arrayValue);
            for (const auto& row : result) {
                models::Article article(row);
                articles.append(article.toJsonBrief());
            }
            Logger::debug("[Favorite] List returned", {{"count", std::to_string(static_cast<int>(result.size()))}});
            callback(Response::success(articles));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[Favorite] Database error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        std::stoll(userId)
    );
}

void FavoriteController::add(const HttpRequestPtr& req,
                             std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::info("[Favorite] Add request", {{"userid", userId}});
    auto json = req->getJsonObject();

    if (!json || !json->isMember("articleid")) {
        Logger::warning("[Favorite] Add failed: missing articleid");
        callback(Response::badRequest("文章ID不能为空"));
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
                    callback(Response::badRequest("已经收藏过了"));
                    return;
                }

                // Re-activate canceled favorite
                int64_t favId = result[0]["favoriteid"].as<int64_t>();
                Logger::debug("[Favorite] Reactivating", {{"favoriteid", std::to_string(favId)}});
                dbClient->execSqlAsync(
                    "UPDATE favorite SET canceled = 0, updatetime = NOW() WHERE favoriteid = ?",
                    [callback, favId, userId, articleId](const orm::Result&) {
                        Logger::info("[Favorite] Reactivated", {{"userid", userId}, {"articleid", std::to_string(articleId)}});
                        callback(Response::ok("收藏成功"));
                    },
                    [callback](const orm::DrogonDbException& e) {
                        Logger::error("Update error: " + std::string(e.base().what()));
                        callback(Response::serverError("收藏失败"));
                    },
                    favId
                );
                return;
            }

            // Create new favorite
            Logger::debug("[Favorite] Creating new", {{"userid", userId}, {"articleid", std::to_string(articleId)}});
            dbClient->execSqlAsync(
                "INSERT INTO favorite (userid, articleid, createtime, updatetime) VALUES (?, ?, NOW(), NOW())",
                [callback, userId, articleId](const orm::Result&) {
                    Logger::info("[Favorite] Created", {{"userid", userId}, {"articleid", std::to_string(articleId)}});
                    callback(Response::ok("收藏成功"));
                },
                [callback](const orm::DrogonDbException& e) {
                    Logger::error("Insert error: " + std::string(e.base().what()));
                    callback(Response::serverError("收藏失败"));
                },
                std::stoll(userId), articleId
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        std::stoll(userId), articleId
    );
}

void FavoriteController::remove(const HttpRequestPtr& req,
                                std::function<void(const HttpResponsePtr&)>&& callback,
                                int64_t articleId)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::info("[Favorite] Remove request", {{"userid", userId}, {"articleid", std::to_string(articleId)}});
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "UPDATE favorite SET canceled = 1, updatetime = NOW() WHERE userid = ? AND articleid = ?",
        [callback, userId, articleId](const orm::Result&) {
            Logger::info("[Favorite] Removed", {{"userid", userId}, {"articleid", std::to_string(articleId)}});
            callback(Response::ok("取消收藏成功"));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Update error: " + std::string(e.base().what()));
            callback(Response::serverError("操作失败"));
        },
        std::stoll(userId), articleId
    );
}

void FavoriteController::check(const HttpRequestPtr& req,
                               std::function<void(const HttpResponsePtr&)>&& callback,
                               int64_t articleId)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::debug("[Favorite] Check request", {{"userid", userId}, {"articleid", std::to_string(articleId)}});
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT favoriteid FROM favorite WHERE userid = ? AND articleid = ? AND canceled = 0",
        [callback](const orm::Result& result) {
            Json::Value data;
            data["favorited"] = result.size() > 0;
            callback(Response::success(data));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        std::stoll(userId), articleId
    );
}

} // namespace controllers
} // namespace woniunote
