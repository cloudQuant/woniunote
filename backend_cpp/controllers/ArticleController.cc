/**
 * @file ArticleController.cc
 * @brief Article API Controller Implementation
 */

#include "ArticleController.h"
#include "core/database.h"
#include "core/logger.h"
#include "core/response.h"
#include "models/Article.h"
#include <drogon/HttpResponse.h>
#include <sstream>
#include <vector>

using namespace drogon;

namespace woniunote {
namespace controllers {

// Article type configuration (matching Python backend)
static const std::map<int, std::string> ARTICLE_TYPES = {
    {1, "交易策略"}, {101, "CTA策略"}, {102, "统计套利"}, {103, "高频交易"},
    {104, "因子策略"}, {105, "选股与择时"}, {106, "机器学习"}, {107, "深度学习"},
    {2, "量化框架"}, {201, "backtrader"}, {202, "wondertrader"}, {203, "wtpy"},
    {204, "pyfolio"}, {205, "alphalens"},
    {3, "投资"}, {301, "股票"}, {302, "期货"}, {303, "期权"},
    {304, "外汇"}, {305, "crypto"}, {306, "黄金"}, {307, "债券"},
    {4, "理财"}, {401, "基金"}, {402, "保险"}, {403, "信托"},
    {404, "银行理财"}, {405, "存款"},
    {5, "区块链与defi"}, {501, "去中心化交易所"}, {502, "去中心化金融"}, {503, "去中心化借贷"},
    {504, "去中心化治理"}, {505, "其他defi"}, {506, "区块链"}, {507, "比特币"}, {508, "以太坊"},
    {6, "机器学习"}, {601, "tensorflow"}, {602, "pytorch"}, {603, "keras"},
    {604, "scikit-learn"}, {605, "机器学习与交易"}, {606, "深度学习与交易"},
    {7, "编程"}, {701, "python"}, {702, "c++"}, {703, "cython"},
    {704, "java"}, {705, "javascript"}, {706, "swing"}, {707, "pybind11"},
    {8, "笔记"}, {801, "幸福"}, {802, "金融"}, {803, "经济"},
    {804, "哲学"}, {805, "历史"}, {806, "科技"}, {807, "读书笔记"},
    {808, "其他笔记"}, {809, "个人知识库"},
    {9, "教程"}, {901, "woniunote入门教程"}, {902, "backtrader基础教程"},
    {903, "airflow入门教程"}, {904, "arrow入门教程"}, {905, "量化交易入门教程"},
    {906, "机器学习入门教程"}, {907, "ib_tws_api入门教程"}
};

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
    Json::Value types(Json::objectValue);
    for (const auto& [id, name] : ARTICLE_TYPES) {
        types[std::to_string(id)] = name;
    }

    Json::Value data;
    data["types"] = types;
    callback(Response::success(data));
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
