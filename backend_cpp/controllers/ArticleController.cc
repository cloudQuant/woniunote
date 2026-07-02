/**
 * @file ArticleController.cc
 * @brief Article API Controller Implementation
 */

#include "ArticleController.h"
#include "core/database.h"
#include "core/logger.h"
#include "core/response.h"
#include "models/Article.h"
#include "models/ArticleCategory.h"
#include <drogon/HttpResponse.h>
#include <sstream>
#include <vector>

using namespace drogon;

namespace woniunote {
namespace controllers {

namespace {

models::ArticleCategory categoryFromRow(const orm::Row& row) {
    models::ArticleCategory category;
    if (!row["id"].isNull()) category.id = row["id"].as<int>();
    if (!row["parent_id"].isNull()) category.parentId = row["parent_id"].as<int>();
    if (!row["name"].isNull()) category.name = row["name"].as<std::string>();
    if (!row["sort_order"].isNull()) category.sortOrder = row["sort_order"].as<int>();
    if (!row["visible"].isNull()) category.visible = row["visible"].as<int>() != 0;
    if (!row["article_count"].isNull()) category.articleCount = row["article_count"].as<int>();
    return category;
}

Json::Value categoryResponseData(const std::vector<models::ArticleCategory>& categories,
                                 bool visibleOnly,
                                 bool includeArticleCount) {
    Json::Value data;
    data["types"] = models::articleCategoryTypeMap(categories, visibleOnly);
    data["flat"] = models::articleCategoryFlatJson(categories, visibleOnly, includeArticleCount);
    data["tree"] = models::articleCategoryTreeJson(categories, visibleOnly, includeArticleCount);
    return data;
}

} // namespace

void ArticleController::list(const HttpRequestPtr& req,
                             std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::debug("[Article] List request", {{"path", req->getPath()}});

    int page = 1, pageSize = 10;
    int type = 0;
    std::string keyword;

    // Safe integer parsing: invalid input falls back to defaults instead of
    // throwing std::invalid_argument (which would otherwise crash the worker).
    auto parseIntParam = [&req](const std::string& name, int fallback) -> int {
        const std::string raw = req->getParameter(name);
        if (raw.empty()) {
            return fallback;
        }
        try {
            return std::stoi(raw);
        } catch (const std::exception&) {
            Logger::warning("[Article] Invalid integer parameter", {{"param", name}, {"value", raw}});
            return fallback;
        }
    };

    page = parseIntParam("page", 1);
    pageSize = parseIntParam("page_size", 10);
    type = parseIntParam("type", 0);
    keyword = req->getParameter("keyword");

    // Clamp to safe bounds
    if (page < 1) page = 1;
    if (pageSize < 1) pageSize = 10;
    pageSize = (std::min)(pageSize, 100);
    int offset = (page - 1) * pageSize;

    auto dbClient = Database::getClient();

    // Build query using parameter binding to prevent SQL injection.
    std::string countSql = "SELECT COUNT(*) as total FROM article WHERE hidden = 0 AND drafted = 0";
    std::string dataSql = "SELECT a.*, u.nickname FROM article a LEFT JOIN users u ON a.userid = u.userid WHERE a.hidden = 0 AND a.drafted = 0";

    // Bound parameters appended in the same order they appear in the SQL text.
    std::vector<std::string> bindParams;

    if (type > 0) {
        countSql += " AND type = ?";
        dataSql += " AND a.type = ?";
        bindParams.push_back(std::to_string(type));
    }
    if (!keyword.empty()) {
        countSql += " AND headline LIKE ?";
        dataSql += " AND a.headline LIKE ?";
        bindParams.push_back("%" + keyword + "%");
    }

    // LIMIT/OFFSET are validated, clamped integers (not user-controlled
    // strings), so they are interpolated directly. They must NOT be bound as
    // string parameters — MySQL rejects `LIMIT '10' OFFSET '0'` as a syntax
    // error (the driver quotes string-typed parameters).
    dataSql += " ORDER BY a.createtime DESC LIMIT " + std::to_string(pageSize) +
               " OFFSET " + std::to_string(offset);

    auto countArgs = bindParams;
    auto dataArgs = bindParams;

    Logger::debug("[Article] Executing list query", {{"page", std::to_string(page)}, {"pageSize", std::to_string(pageSize)}, {"type", std::to_string(type)}});

    // Helper to dispatch an async query with a runtime-sized parameter list.
    auto execWithParams = [dbClient](const std::string& sql,
                                     const std::vector<std::string>& params,
                                     std::function<void(const orm::Result&)>&& onResult,
                                     std::function<void(const orm::DrogonDbException&)>&& onError) {
        auto self = dbClient;
        switch (params.size()) {
            case 0:
                self->execSqlAsync(sql, std::move(onResult), std::move(onError));
                break;
            case 1:
                self->execSqlAsync(sql, std::move(onResult), std::move(onError), params[0]);
                break;
            case 2:
                self->execSqlAsync(sql, std::move(onResult), std::move(onError), params[0], params[1]);
                break;
            case 3:
                self->execSqlAsync(sql, std::move(onResult), std::move(onError), params[0], params[1], params[2]);
                break;
            default:
                self->execSqlAsync(sql, std::move(onResult), std::move(onError),
                                   params[0], params[1], params[2], params[3]);
                break;
        }
    };

    execWithParams(
        countSql,
        countArgs,
        [callback, dataSql, dataArgs, page, pageSize, execWithParams](const orm::Result& countResult) {
            int total = countResult[0]["total"].as<int>();
            int totalPages = (total + pageSize - 1) / pageSize;

            execWithParams(
                dataSql,
                dataArgs,
                [callback, total, page, pageSize, totalPages](const orm::Result& dataResult) {
                    Json::Value articles(Json::arrayValue);
                    for (const auto& row : dataResult) {
                        models::Article article(row);
                        articles.append(article.toJsonBrief());
                    }

                    // Preserve the existing list envelope (extra top-level
                    // pagination fields) for frontend compatibility.
                    Json::Value ret;
                    ret["code"] = 200;
                    ret["message"] = "success";
                    ret["data"] = articles;
                    ret["total"] = total;
                    ret["page"] = page;
                    ret["page_size"] = pageSize;
                    ret["total_pages"] = totalPages;

                    Logger::debug("[Article] List returned", {{"total", std::to_string(total)}, {"count", std::to_string(static_cast<int>(dataResult.size()))}});
                    callback(HttpResponse::newHttpJsonResponse(ret));
                },
                [callback](const orm::DrogonDbException& e) {
                    Logger::error("[Article] Query error: " + std::string(e.base().what()));
                    callback(Response::serverError("数据库错误"));
                }
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Count error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        }
    );
}

void ArticleController::getTypes(const HttpRequestPtr& req,
                                 std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::debug("[Article] GetTypes request");
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT c.id, c.parent_id, c.name, c.sort_order, c.visible, COUNT(a.articleid) AS article_count "
        "FROM article_category c "
        "LEFT JOIN article a ON a.type = c.id "
        "WHERE c.visible = 1 "
        "GROUP BY c.id, c.parent_id, c.name, c.sort_order, c.visible "
        "ORDER BY COALESCE(c.parent_id, 0), c.sort_order, c.id",
        [callback](const orm::Result& result) {
            std::vector<models::ArticleCategory> categories;
            categories.reserve(result.size());
            for (const auto& row : result) {
                categories.push_back(categoryFromRow(row));
            }
            callback(Response::success(categoryResponseData(categories, true, false)));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::warning("[Article] GetTypes DB fallback: " + std::string(e.base().what()));
            const auto legacy = models::legacyArticleCategories();
            callback(Response::success(categoryResponseData(legacy, true, false)));
        }
    );
}

void ArticleController::getHot(const HttpRequestPtr& req,
                               std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::debug("[Article] GetHot request");
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT a.*, u.nickname FROM article a LEFT JOIN users u ON a.userid = u.userid WHERE a.hidden = 0 AND a.drafted = 0 ORDER BY a.createtime DESC LIMIT 10",
        [callback, dbClient](const orm::Result& latestResult) {
            Json::Value latest(Json::arrayValue);
            for (const auto& row : latestResult) {
                models::Article article(row);
                latest.append(article.toJsonBrief());
            }

            dbClient->execSqlAsync(
                "SELECT a.*, u.nickname FROM article a LEFT JOIN users u ON a.userid = u.userid WHERE a.hidden = 0 AND a.drafted = 0 ORDER BY a.readcount DESC LIMIT 10",
                [callback, dbClient, latest](const orm::Result& mostResult) {
                    Json::Value most(Json::arrayValue);
                    for (const auto& row : mostResult) {
                        models::Article article(row);
                        most.append(article.toJsonBrief());
                    }

                    dbClient->execSqlAsync(
                        "SELECT a.*, u.nickname FROM article a LEFT JOIN users u ON a.userid = u.userid WHERE a.hidden = 0 AND a.drafted = 0 AND a.recommended = 1 ORDER BY a.createtime DESC LIMIT 10",
                        [callback, latest, most](const orm::Result& recResult) {
                            Json::Value recommended(Json::arrayValue);
                            for (const auto& row : recResult) {
                                models::Article article(row);
                                recommended.append(article.toJsonBrief());
                            }

                            Json::Value data;
                            data["latest"] = latest;
                            data["most"] = most;
                            data["recommended"] = recommended;

                            Logger::debug("[Article] GetHot returned", {{"latest", std::to_string(static_cast<int>(latest.size()))}, {"most", std::to_string(static_cast<int>(most.size()))}, {"recommended", std::to_string(static_cast<int>(recommended.size()))}});
                            callback(Response::success(data));
                        },
                        [callback](const orm::DrogonDbException& e) {
                            Logger::error("Query error: " + std::string(e.base().what()));
                            callback(Response::serverError("数据库错误"));
                        }
                    );
                },
                [callback](const orm::DrogonDbException& e) {
                    Logger::error("Query error: " + std::string(e.base().what()));
                    callback(Response::serverError("数据库错误"));
                }
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Query error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        }
    );
}

void ArticleController::get(const HttpRequestPtr& req,
                            std::function<void(const HttpResponsePtr&)>&& callback,
                            int64_t id)
{
    Logger::debug("[Article] Get request", {{"articleid", std::to_string(id)}});
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT a.*, u.nickname FROM article a LEFT JOIN users u ON a.userid = u.userid WHERE a.articleid = ?",
        [callback, id, dbClient](const orm::Result& result) {
            if (result.size() == 0) {
                Logger::debug("[Article] Not found", {{"articleid", std::to_string(id)}});
                callback(Response::notFound("文章不存在"));
                return;
            }

            models::Article article(result[0]);
            Logger::debug("[Article] Found", {{"articleid", std::to_string(id)}, {"headline", article.getHeadline()}});

            // Increment read count
            dbClient->execSqlAsync(
                "UPDATE article SET readcount = readcount + 1 WHERE articleid = ?",
                [](const orm::Result&) {},
                [](const orm::DrogonDbException&) {},
                id
            );

            callback(Response::success(article.toJson()));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        id
    );
}

void ArticleController::myArticles(const HttpRequestPtr& req,
                                   std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::debug("[Article] MyArticles request", {{"userid", userId}});
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT a.*, u.nickname FROM article a LEFT JOIN users u ON a.userid = u.userid "
        "WHERE a.userid = ? ORDER BY a.createtime DESC",
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

void ArticleController::myDrafts(const HttpRequestPtr& req,
                                 std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::debug("[Article] MyDrafts request", {{"userid", userId}});
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

void ArticleController::create(const HttpRequestPtr& req,
                               std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::info("[Article] Create request", {{"userid", userId}});
    auto json = req->getJsonObject();

    if (!json || !json->isMember("headline") || !json->isMember("type")) {
        Logger::warning("[Article] Create failed: missing fields");
        callback(Response::badRequest("标题和类型不能为空"));
        return;
    }

    std::string headline = (*json)["headline"].asString();
    int type = (*json)["type"].asInt();
    std::string content = json->get("content", "").asString();
    std::string thumbnail = json->get("thumbnail", "").asString();
    int credit = json->get("credit", 0).asInt();
    int drafted = json->get("drafted", 0).asInt();

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

void ArticleController::update(const HttpRequestPtr& req,
                               std::function<void(const HttpResponsePtr&)>&& callback,
                               int64_t id)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::info("[Article] Update request", {{"articleid", std::to_string(id)}, {"userid", userId}});
    auto json = req->getJsonObject();

    if (!json) {
        Logger::warning("[Article] Update failed: invalid JSON");
        callback(Response::badRequest("请求格式错误"));
        return;
    }

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

            std::string headline = json->get("headline", "").asString();
            std::string content = json->get("content", "").asString();
            int type = json->get("type", 0).asInt();

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

void ArticleController::remove(const HttpRequestPtr& req,
                               std::function<void(const HttpResponsePtr&)>&& callback,
                               int64_t id)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::info("[Article] Delete request", {{"articleid", std::to_string(id)}, {"userid", userId}});
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

// Shared helper for the admin toggle endpoints (recommend/hide/check).
// Flips a 0/1 column and returns its new value, with 404 protection.
static void toggleBoolColumn(int64_t id,
                             const std::string& column,
                             const std::string& onMsg,
                             const std::string& offMsg,
                             std::function<void(const HttpResponsePtr&)> callback)
{
    auto dbClient = Database::getClient();
    const std::string updateSql = "UPDATE article SET " + column + " = 1 - " + column + " WHERE articleid = ?";
    const std::string selectSql = "SELECT " + column + " AS val FROM article WHERE articleid = ?";

    dbClient->execSqlAsync(
        updateSql,
        [callback, id, dbClient, selectSql, column, onMsg, offMsg](const orm::Result&) {
            dbClient->execSqlAsync(
                selectSql,
                [callback, id, column, onMsg, offMsg](const orm::Result& result) {
                    if (result.size() == 0) {
                        callback(Response::notFound("文章不存在"));
                        return;
                    }
                    int val = result[0]["val"].as<int>();
                    Logger::info("[Article] Column toggled", {{"articleid", std::to_string(id)}, {"column", column}, {"value", std::to_string(val)}});
                    Json::Value data;
                    data[column] = val;
                    callback(Response::ok(val ? onMsg : offMsg, data));
                },
                [callback](const orm::DrogonDbException& e) {
                    Logger::error("Query error: " + std::string(e.base().what()));
                    callback(Response::serverError("操作失败"));
                },
                id
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Update error: " + std::string(e.base().what()));
            callback(Response::serverError("操作失败"));
        },
        id
    );
}

void ArticleController::toggleRecommend(const HttpRequestPtr& req,
                                        std::function<void(const HttpResponsePtr&)>&& callback,
                                        int64_t id)
{
    Logger::info("[Article] Toggle recommend", {{"articleid", std::to_string(id)}});
    toggleBoolColumn(id, "recommended", "已推荐", "已取消推荐", std::move(callback));
}

void ArticleController::toggleHide(const HttpRequestPtr& req,
                                   std::function<void(const HttpResponsePtr&)>&& callback,
                                   int64_t id)
{
    Logger::info("[Article] Toggle hide", {{"articleid", std::to_string(id)}});
    toggleBoolColumn(id, "hidden", "已隐藏", "已显示", std::move(callback));
}

void ArticleController::toggleCheck(const HttpRequestPtr& req,
                                    std::function<void(const HttpResponsePtr&)>&& callback,
                                    int64_t id)
{
    Logger::info("[Article] Toggle check", {{"articleid", std::to_string(id)}});
    toggleBoolColumn(id, "checked", "已通过审核", "已取消审核", std::move(callback));
}

} // namespace controllers
} // namespace woniunote
