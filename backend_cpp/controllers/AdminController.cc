/**
 * @file AdminController.cc
 * @brief Admin API Controller Implementation
 */

#include "AdminController.h"
#include "core/database.h"
#include "core/logger.h"
#include "core/response.h"
#include "models/User.h"
#include "models/Article.h"
#include "models/Comment.h"
#include "services/ArticleCategoryService.h"
#include <drogon/HttpResponse.h>

using namespace drogon;

namespace woniunote {
namespace controllers {

namespace {
// Safe pagination parsing shared by the admin list endpoints.
void parsePaging(const HttpRequestPtr& req, int& page, int& pageSize) {
    auto parse = [&req](const std::string& name, int fallback) -> int {
        const std::string raw = req->getParameter(name);
        if (raw.empty()) return fallback;
        try { return std::stoi(raw); } catch (const std::exception&) { return fallback; }
    };
    page = parse("page", 1);
    pageSize = parse("page_size", 20);
    if (page < 1) page = 1;
    if (pageSize < 1) pageSize = 20;
    if (pageSize > 100) pageSize = 100;
}

// Extracts the article-category delete options from the move_articles_to
// query parameter or JSON body. See ArticleCategoryService::deleteCategory.
services::ArticleCategoryService::DeleteOptions parseCategoryDeleteOptions(
    const HttpRequestPtr& req) {
    services::ArticleCategoryService::DeleteOptions options;
    const std::string moveParam = req->getParameter("move_articles_to");
    if (!moveParam.empty()) {
        try {
            options.moveArticlesTo = std::stoi(moveParam);
        } catch (const std::exception&) {
            options.moveTargetInvalid = true;
        }
        return options;
    }
    if (auto json = req->getJsonObject(); json && json->isMember("move_articles_to")) {
        options.moveArticlesTo = (*json)["move_articles_to"].asInt();
    }
    return options;
}
} // namespace

void AdminController::getStats(const HttpRequestPtr& req,
                               std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::debug("[Admin] Get stats request");
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT "
        "(SELECT COUNT(*) FROM users) as user_count, "
        "(SELECT COUNT(*) FROM article) as article_count, "
        "(SELECT COUNT(*) FROM comment) as comment_count, "
        "(SELECT COUNT(*) FROM article WHERE createtime > DATE_SUB(NOW(), INTERVAL 7 DAY)) as articles_week, "
        "(SELECT COUNT(*) FROM users WHERE createtime > DATE_SUB(NOW(), INTERVAL 7 DAY)) as users_week",
        [callback](const orm::Result& result) {
            Json::Value data;
            data["user_count"] = result[0]["user_count"].as<int>();
            data["article_count"] = result[0]["article_count"].as<int>();
            data["comment_count"] = result[0]["comment_count"].as<int>();
            data["articles_week"] = result[0]["articles_week"].as<int>();
            data["users_week"] = result[0]["users_week"].as<int>();
            callback(Response::success(data));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("DB error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        }
    );
}

void AdminController::listUsers(const HttpRequestPtr& req,
                                std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::debug("[Admin] List users request");
    int page = 1, pageSize = 20;
    parsePaging(req, page, pageSize);
    int offset = (page - 1) * pageSize;

    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT * FROM users ORDER BY createtime DESC LIMIT ? OFFSET ?",
        [callback](const orm::Result& result) {
            Json::Value users(Json::arrayValue);
            for (const auto& row : result) {
                models::User user(row);
                users.append(user.toJsonWithoutPassword());
            }
            callback(Response::success(users));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("DB error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        pageSize, offset
    );
}

void AdminController::updateUser(const HttpRequestPtr& req,
                                 std::function<void(const HttpResponsePtr&)>&& callback,
                                 int64_t id)
{
    Logger::info("[Admin] Update user", {{"userid", std::to_string(id)}});
    auto json = req->getJsonObject();
    if (!json) {
        Logger::warning("[Admin] Update user failed: invalid JSON");
        callback(Response::badRequest("请求格式错误"));
        return;
    }

    std::string role = json->get("role", "user").asString();
    int credit = json->get("credit", 0).asInt();

    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "UPDATE users SET role = ?, credit = ?, updatetime = NOW() WHERE userid = ?",
        [callback](const orm::Result&) {
            callback(Response::ok("更新成功"));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Update error: " + std::string(e.base().what()));
            callback(Response::serverError("更新失败"));
        },
        role, credit, id
    );
}

void AdminController::deleteUser(const HttpRequestPtr& req,
                                 std::function<void(const HttpResponsePtr&)>&& callback,
                                 int64_t id)
{
    Logger::warning("[Admin] Delete user", {{"userid", std::to_string(id)}});
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "DELETE FROM users WHERE userid = ?",
        [callback, id](const orm::Result&) {
            Logger::info("[Admin] User deleted", {{"userid", std::to_string(id)}});
            callback(Response::ok("删除成功"));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Delete error: " + std::string(e.base().what()));
            callback(Response::serverError("删除失败"));
        },
        id
    );
}

void AdminController::listArticles(const HttpRequestPtr& req,
                                   std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::debug("[Admin] List articles request");
    int page = 1, pageSize = 20;
    parsePaging(req, page, pageSize);
    int offset = (page - 1) * pageSize;

    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT a.*, u.nickname FROM article a LEFT JOIN users u ON a.userid = u.userid "
        "ORDER BY a.createtime DESC LIMIT ? OFFSET ?",
        [callback](const orm::Result& result) {
            Json::Value articles(Json::arrayValue);
            for (const auto& row : result) {
                models::Article article(row);
                articles.append(article.toJsonBrief());
            }
            callback(Response::success(articles));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("DB error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        pageSize, offset
    );
}

void AdminController::updateArticleType(const HttpRequestPtr& req,
                                        std::function<void(const HttpResponsePtr&)>&& callback,
                                        int64_t id)
{
    Logger::info("[Admin] Update article type", {{"articleid", std::to_string(id)}});
    auto json = req->getJsonObject();
    if (!json || !json->isMember("type") || (*json)["type"].asInt() <= 0) {
        callback(Response::badRequest("请选择有效分类"));
        return;
    }

    int type = (*json)["type"].asInt();
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT id FROM article_category WHERE id = ? LIMIT 1",
        [callback, dbClient, id, type](const orm::Result& categoryResult) {
            if (categoryResult.size() == 0) {
                callback(Response::badRequest("分类不存在"));
                return;
            }

            dbClient->execSqlAsync(
                "SELECT articleid FROM article WHERE articleid = ? LIMIT 1",
                [callback, dbClient, id, type](const orm::Result& articleResult) {
                    if (articleResult.size() == 0) {
                        callback(Response::notFound("文章不存在"));
                        return;
                    }

                    dbClient->execSqlAsync(
                        "UPDATE article SET type = ?, updatetime = NOW() WHERE articleid = ?",
                        [callback, id, type](const orm::Result&) {
                            Json::Value data;
                            data["articleid"] = static_cast<Json::Int64>(id);
                            data["type"] = type;
                            callback(Response::ok("分类已更新", data));
                        },
                        [callback](const orm::DrogonDbException& e) {
                            Logger::error("[Admin] Update article type failed: " + std::string(e.base().what()));
                            callback(Response::serverError("更新失败"));
                        },
                        type, id
                    );
                },
                [callback](const orm::DrogonDbException& e) {
                    Logger::error("[Admin] Article lookup failed: " + std::string(e.base().what()));
                    callback(Response::serverError("数据库错误"));
                },
                id
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[Admin] Category lookup failed: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        type
    );
}

void AdminController::listArticleCategories(const HttpRequestPtr& req,
                                            std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::debug("[Admin] List article categories request");
    services::ArticleCategoryService::listCategories(std::move(callback));
}

void AdminController::createArticleCategory(const HttpRequestPtr& req,
                                            std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::info("[Admin] Create article category");
    auto json = req->getJsonObject();
    if (!json || !json->isMember("name")) {
        callback(Response::badRequest("分类名称不能为空"));
        return;
    }

    services::ArticleCategoryService::createCategory(*json, std::move(callback));
}

void AdminController::updateArticleCategory(const HttpRequestPtr& req,
                                            std::function<void(const HttpResponsePtr&)>&& callback,
                                            int64_t id)
{
    Logger::info("[Admin] Update article category", {{"categoryid", std::to_string(id)}});
    auto json = req->getJsonObject();
    if (!json) {
        callback(Response::badRequest("请求格式错误"));
        return;
    }

    services::ArticleCategoryService::updateCategory(id, *json, std::move(callback));
}

void AdminController::deleteArticleCategory(const HttpRequestPtr& req,
                                            std::function<void(const HttpResponsePtr&)>&& callback,
                                            int64_t id)
{
    Logger::warning("[Admin] Delete article category", {{"categoryid", std::to_string(id)}});
    services::ArticleCategoryService::deleteCategory(
        id, parseCategoryDeleteOptions(req), std::move(callback));
}

void AdminController::deleteArticle(const HttpRequestPtr& req,
                                    std::function<void(const HttpResponsePtr&)>&& callback,
                                    int64_t id)
{
    Logger::warning("[Admin] Delete article", {{"articleid", std::to_string(id)}});
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "DELETE FROM article WHERE articleid = ?",
        [callback, id](const orm::Result&) {
            Logger::info("[Admin] Article deleted", {{"articleid", std::to_string(id)}});
            callback(Response::ok("删除成功"));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Delete error: " + std::string(e.base().what()));
            callback(Response::serverError("删除失败"));
        },
        id
    );
}

void AdminController::listComments(const HttpRequestPtr& req,
                                   std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::debug("[Admin] List comments request");
    int page = 1, pageSize = 20;
    parsePaging(req, page, pageSize);
    int offset = (page - 1) * pageSize;

    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT * FROM comment ORDER BY createtime DESC LIMIT ? OFFSET ?",
        [callback](const orm::Result& result) {
            Json::Value comments(Json::arrayValue);
            for (const auto& row : result) {
                models::Comment comment(row);
                comments.append(comment.toJson());
            }
            callback(Response::success(comments));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("DB error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        pageSize, offset
    );
}

void AdminController::deleteComment(const HttpRequestPtr& req,
                                    std::function<void(const HttpResponsePtr&)>&& callback,
                                    int64_t id)
{
    Logger::warning("[Admin] Delete comment", {{"commentid", std::to_string(id)}});
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "DELETE FROM comment WHERE commentid = ?",
        [callback, id](const orm::Result&) {
            Logger::info("[Admin] Comment deleted", {{"commentid", std::to_string(id)}});
            callback(Response::ok("删除成功"));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Delete error: " + std::string(e.base().what()));
            callback(Response::serverError("删除失败"));
        },
        id
    );
}

} // namespace controllers
} // namespace woniunote
