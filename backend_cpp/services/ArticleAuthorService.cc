/**
 * @file ArticleAuthorService.cc
 * @brief Own-article management service implementation.
 */

#include "ArticleAuthorService.h"
#include "core/database.h"
#include "core/logger.h"
#include "core/response.h"
#include "models/Article.h"
#include "models/ArticleCategory.h"
#include <drogon/HttpResponse.h>
#include <algorithm>

using namespace drogon;

namespace woniunote {
namespace services {

namespace {

bool legacyCategoryExists(int type) {
    const auto categories = models::legacyArticleCategories();
    return std::any_of(categories.begin(), categories.end(), [type](const auto& category) {
        return category.id == type && category.visible;
    });
}

} // namespace

void ArticleAuthorService::listMyArticles(const std::string& userId,
                                          int page,
                                          int pageSize,
                                          int type,
                                          ArticleAuthorService::ResponseCallback callback)
{
    int offset = (page - 1) * pageSize;
    int64_t ownerId = std::stoll(userId);

    auto dbClient = Database::getClient();

    std::string countSql = "SELECT COUNT(*) AS total FROM article a WHERE a.userid = ?";
    std::string dataSql = "SELECT a.*, u.nickname FROM article a LEFT JOIN users u ON a.userid = u.userid "
                          "WHERE a.userid = ?";
    if (type > 0) {
        countSql += " AND a.type = ?";
        dataSql += " AND a.type = ?";
    }
    dataSql += " ORDER BY a.createtime DESC LIMIT " + std::to_string(pageSize) +
               " OFFSET " + std::to_string(offset);

    auto onData = [callback, page, pageSize](const orm::Result& result, int total) {
        int totalPages = (total + pageSize - 1) / pageSize;
        Json::Value ret;
        ret["code"] = 200;
        ret["message"] = "success";
        ret["data"] = Json::arrayValue;
        ret["total"] = total;
        ret["page"] = page;
        ret["page_size"] = pageSize;
        ret["total_pages"] = totalPages;

        Json::Value articles(Json::arrayValue);
        for (const auto& row : result) {
            models::Article article(row);
            articles.append(article.toJsonBrief());
        }
        ret["data"] = articles;

        Logger::debug("[Article] MyArticles returned",
                      {{"total", std::to_string(total)},
                       {"count", std::to_string(static_cast<int>(result.size()))}});
        callback(HttpResponse::newHttpJsonResponse(ret));
    };

    auto onError = [callback](const orm::DrogonDbException& e) {
        Logger::error("Database error: " + std::string(e.base().what()));
        callback(Response::serverError("数据库错误"));
    };

    auto runData = [dbClient, dataSql, ownerId, type, onData, onError](int total) {
        if (type > 0) {
            dbClient->execSqlAsync(
                dataSql,
                [onData, total](const orm::Result& result) {
                    onData(result, total);
                },
                onError,
                ownerId, type
            );
            return;
        }

        dbClient->execSqlAsync(
            dataSql,
            [onData, total](const orm::Result& result) {
                onData(result, total);
            },
            onError,
            ownerId
        );
    };

    if (type > 0) {
        dbClient->execSqlAsync(
            countSql,
            [runData](const orm::Result& result) {
                runData(result[0]["total"].as<int>());
            },
            onError,
            ownerId, type
        );
        return;
    }

    dbClient->execSqlAsync(
        countSql,
        [runData](const orm::Result& result) {
            runData(result[0]["total"].as<int>());
        },
        onError,
        ownerId
    );
}

void ArticleAuthorService::listMyDrafts(const std::string& userId,
                                        ArticleAuthorService::ResponseCallback callback)
{
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT a.*, u.nickname FROM article a LEFT JOIN users u ON a.userid = u.userid "
        "WHERE a.userid = ? AND a.drafted = 1 ORDER BY a.updatetime DESC",
        [callback](const orm::Result& result) {
            Json::Value articles(Json::arrayValue);
            for (const auto& row : result) {
                models::Article article(row);
                articles.append(article.toJsonBrief());
            }
            callback(Response::success(articles));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        std::stoll(userId)
    );
}

void ArticleAuthorService::createArticle(const std::string& userId,
                                         const Json::Value& json,
                                         ArticleAuthorService::ResponseCallback callback)
{
    std::string headline = json["headline"].asString();
    int type = json["type"].asInt();
    std::string content = json.get("content", "").asString();
    std::string thumbnail = json.get("thumbnail", "").asString();
    int credit = json.get("credit", 0).asInt();
    int drafted = json.get("drafted", 0).asInt();

    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "INSERT INTO article (userid, type, headline, content, thumbnail, credit, drafted, createtime, updatetime) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), NOW())",
        [callback, dbClient](const orm::Result& result) {
            int64_t articleId = result.insertId();
            Logger::info("[Article] Created", {{"articleid", std::to_string(articleId)}});

            dbClient->execSqlAsync(
                "SELECT a.*, u.nickname FROM article a LEFT JOIN users u ON a.userid = u.userid "
                "WHERE a.articleid = ?",
                [callback](const orm::Result& articleResult) {
                    if (articleResult.size() > 0) {
                        models::Article article(articleResult[0]);
                        callback(Response::ok("创建成功", article.toJson()));
                    } else {
                        callback(Response::ok("创建成功"));
                    }
                },
                [callback](const orm::DrogonDbException&) {
                    // Article was created; fetching it back failed but that is non-fatal.
                    callback(Response::ok("创建成功"));
                },
                articleId
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Insert error: " + std::string(e.base().what()));
            callback(Response::serverError("创建失败"));
        },
        std::stoll(userId), type, headline, content, thumbnail, credit, drafted
    );
}

void ArticleAuthorService::updateArticle(const std::string& userId,
                                         int64_t id,
                                         const Json::Value& json,
                                         ArticleAuthorService::ResponseCallback callback)
{
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT userid FROM article WHERE articleid = ?",
        [callback, id, userId, json, dbClient](const orm::Result& result) {
            if (result.size() == 0) {
                callback(Response::notFound("文章不存在"));
                return;
            }

            int64_t ownerId = result[0]["userid"].as<int64_t>();
            if (ownerId != std::stoll(userId)) {
                callback(Response::forbidden("没有权限修改此文章"));
                return;
            }

            std::string headline = json.get("headline", "").asString();
            std::string content = json.get("content", "").asString();
            int type = json.get("type", 0).asInt();

            dbClient->execSqlAsync(
                "UPDATE article SET headline = ?, content = ?, type = ?, updatetime = NOW() WHERE articleid = ?",
                [callback](const orm::Result&) {
                    callback(Response::ok("更新成功"));
                },
                [callback](const orm::DrogonDbException& e) {
                    Logger::error("Update error: " + std::string(e.base().what()));
                    callback(Response::serverError("更新失败"));
                },
                headline, content, type, id
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        id
    );
}

void ArticleAuthorService::updateArticleType(const std::string& userId,
                                             int64_t id,
                                             int type,
                                             ArticleAuthorService::ResponseCallback callback)
{
    auto dbClient = Database::getClient();
    dbClient->execSqlAsync(
        "SELECT userid FROM article WHERE articleid = ?",
        [callback, id, userId, type, dbClient](const orm::Result& articleResult) {
            if (articleResult.size() == 0) {
                callback(Response::notFound("文章不存在"));
                return;
            }

            int64_t ownerId = articleResult[0]["userid"].as<int64_t>();
            if (ownerId != std::stoll(userId)) {
                callback(Response::forbidden("没有权限修改此文章"));
                return;
            }

            auto applyUpdate = [callback, id, type, dbClient]() {
                dbClient->execSqlAsync(
                    "UPDATE article SET type = ?, updatetime = NOW() WHERE articleid = ?",
                    [callback, type](const orm::Result&) {
                        Json::Value data;
                        data["type"] = type;
                        callback(Response::ok("分类已更新", data));
                    },
                    [callback](const orm::DrogonDbException& e) {
                        Logger::error("[Article] Update type failed: " + std::string(e.base().what()));
                        callback(Response::serverError("分类更新失败"));
                    },
                    type, id
                );
            };

            dbClient->execSqlAsync(
                "SELECT id FROM article_category WHERE id = ? AND visible = 1",
                [callback, applyUpdate](const orm::Result& categoryResult) {
                    if (categoryResult.size() == 0) {
                        callback(Response::badRequest("分类不存在或不可用"));
                        return;
                    }
                    applyUpdate();
                },
                [callback, type, applyUpdate](const orm::DrogonDbException& e) {
                    Logger::warning("[Article] Category validation fell back to legacy map: " + std::string(e.base().what()));
                    if (!legacyCategoryExists(type)) {
                        callback(Response::badRequest("分类不存在或不可用"));
                        return;
                    }
                    applyUpdate();
                },
                type
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[Article] Update type owner check failed: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        id
    );
}

void ArticleAuthorService::removeArticle(const std::string& userId,
                                         int64_t id,
                                         ArticleAuthorService::ResponseCallback callback)
{
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT userid FROM article WHERE articleid = ?",
        [callback, id, userId, dbClient](const orm::Result& result) {
            if (result.size() == 0) {
                callback(Response::notFound("文章不存在"));
                return;
            }

            int64_t ownerId = result[0]["userid"].as<int64_t>();
            if (ownerId != std::stoll(userId)) {
                callback(Response::forbidden("没有权限删除此文章"));
                return;
            }

            dbClient->execSqlAsync(
                "DELETE FROM article WHERE articleid = ?",
                [callback, id](const orm::Result&) {
                    Logger::info("[Article] Deleted successfully", {{"articleid", std::to_string(id)}});
                    callback(Response::ok("删除成功"));
                },
                [callback](const orm::DrogonDbException& e) {
                    Logger::error("Delete error: " + std::string(e.base().what()));
                    callback(Response::serverError("删除失败"));
                },
                id
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        id
    );
}

} // namespace services
} // namespace woniunote
