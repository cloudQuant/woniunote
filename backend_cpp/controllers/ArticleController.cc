/**
 * @file ArticleController.cc
 * @brief Article API Controller Implementation
 */

#include "ArticleController.h"
#include "core/database.h"
#include "core/logger.h"
#include "models/Article.h"
#include <drogon/HttpResponse.h>
#include <sstream>

using namespace drogon;

namespace woniunote {
namespace controllers {

// Article type configuration (matching Python backend)
static const std::map<int, std::string> ARTICLE_TYPES = {
    {1, "交易策略"}, {101, "CTA策略"}, {102, "统计套利"}, {103, "高频交易"},
    {104, "因子策略"}, {105, "选股与择时"}, {106, "机器学习"}, {107, "深度学习"},
    {2, "量化框架"}, {201, "backtrader"}, {202, "vnpy"}, {203, "wtpy"},
    {3, "数据处理"}, {301, "数据获取"}, {302, "数据存储"}, {303, "数据清洗"},
    {4, "交易接口"}, {401, "CTP"}, {402, "IB"}, {403, "掘金"},
    {5, "系统运维"}, {501, "Linux"}, {502, "Docker"}, {503, "监控"},
    {6, "交流讨论"}, {601, "策略交流"}, {602, "问题求助"}, {603, "资源分享"},
    {7, "公告通知"}, {701, "网站公告"}, {702, "更新日志"},
    {8, "读书笔记"}, {801, "金融"}, {802, "投资"}, {803, "经济"},
    {9, "教程"}, {901, "woniunote入门教程"}, {902, "backtrader基础教程"}
};

void ArticleController::list(const HttpRequestPtr& req,
                             std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::debug("[Article] List request", {{"path", req->getPath()}});
    
    int page = 1, pageSize = 10;
    int type = 0;
    std::string keyword;

    if (req->getParameter("page").length() > 0) {
        page = std::stoi(req->getParameter("page"));
    }
    if (req->getParameter("page_size").length() > 0) {
        pageSize = std::stoi(req->getParameter("page_size"));
    }
    if (req->getParameter("type").length() > 0) {
        type = std::stoi(req->getParameter("type"));
    }
    keyword = req->getParameter("keyword");

    pageSize = (std::min)(pageSize, 100);
    int offset = (page - 1) * pageSize;

    auto dbClient = Database::getClient();

    // Build query
    std::string countSql = "SELECT COUNT(*) as total FROM article WHERE hidden = 0 AND drafted = 0";
    std::string dataSql = "SELECT * FROM article WHERE hidden = 0 AND drafted = 0";
    
    if (type > 0) {
        countSql += " AND type = " + std::to_string(type);
        dataSql += " AND type = " + std::to_string(type);
    }
    if (!keyword.empty()) {
        countSql += " AND headline LIKE '%" + keyword + "%'";
        dataSql += " AND headline LIKE '%" + keyword + "%'";
    }
    
    dataSql += " ORDER BY createtime DESC LIMIT " + std::to_string(pageSize) + 
               " OFFSET " + std::to_string(offset);

    Logger::debug("[Article] Executing list query", {{"page", std::to_string(page)}, {"pageSize", std::to_string(pageSize)}, {"type", std::to_string(type)}});
    
    dbClient->execSqlAsync(
        countSql,
        [callback, dataSql, page, pageSize, dbClient](const orm::Result& countResult) {
            int total = countResult[0]["total"].as<int>();
            int totalPages = (total + pageSize - 1) / pageSize;

            dbClient->execSqlAsync(
                dataSql,
                [callback, total, page, pageSize, totalPages](const orm::Result& dataResult) {
                    Json::Value articles(Json::arrayValue);
                    for (const auto& row : dataResult) {
                        models::Article article(row);
                        articles.append(article.toJsonBrief());
                    }

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
                    Json::Value ret;
                    ret["code"] = 500;
                    ret["message"] = "数据库错误";
                    callback(HttpResponse::newHttpJsonResponse(ret));
                }
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Count error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            callback(HttpResponse::newHttpJsonResponse(ret));
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

    Json::Value ret;
    ret["code"] = 200;
    ret["message"] = "success";
    ret["data"] = types;
    callback(HttpResponse::newHttpJsonResponse(ret));
}

void ArticleController::getHot(const HttpRequestPtr& req,
                               std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::debug("[Article] GetHot request");
    auto dbClient = Database::getClient();

    // Get latest, most read, and recommended articles
    dbClient->execSqlAsync(
        "SELECT * FROM article WHERE hidden = 0 AND drafted = 0 ORDER BY createtime DESC LIMIT 10",
        [callback, dbClient](const orm::Result& latestResult) {
            Json::Value latest(Json::arrayValue);
            for (const auto& row : latestResult) {
                models::Article article(row);
                latest.append(article.toJsonBrief());
            }

            dbClient->execSqlAsync(
                "SELECT * FROM article WHERE hidden = 0 AND drafted = 0 ORDER BY readcount DESC LIMIT 10",
                [callback, dbClient, latest](const orm::Result& mostResult) {
                    Json::Value most(Json::arrayValue);
                    for (const auto& row : mostResult) {
                        models::Article article(row);
                        most.append(article.toJsonBrief());
                    }

                    dbClient->execSqlAsync(
                        "SELECT * FROM article WHERE hidden = 0 AND drafted = 0 AND recommended = 1 ORDER BY createtime DESC LIMIT 10",
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
                            Json::Value ret;
                            ret["code"] = 200;
                            ret["message"] = "success";
                            ret["data"] = data;
                            callback(HttpResponse::newHttpJsonResponse(ret));
                        },
                        [callback](const orm::DrogonDbException& e) {
                            Logger::error("Query error: " + std::string(e.base().what()));
                        }
                    );
                },
                [callback](const orm::DrogonDbException& e) {
                    Logger::error("Query error: " + std::string(e.base().what()));
                }
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Query error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            callback(HttpResponse::newHttpJsonResponse(ret));
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
        "SELECT * FROM article WHERE articleid = ?",
        [callback, id, dbClient](const orm::Result& result) {
            if (result.size() == 0) {
                Logger::debug("[Article] Not found", {{"articleid", std::to_string(id)}});
                Json::Value ret;
                ret["code"] = 404;
                ret["message"] = "文章不存在";
                auto resp = HttpResponse::newHttpJsonResponse(ret);
                resp->setStatusCode(k404NotFound);
                callback(resp);
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

            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "success";
            ret["data"] = article.toJson();
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            callback(HttpResponse::newHttpJsonResponse(ret));
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
        "SELECT * FROM article WHERE userid = ? ORDER BY createtime DESC",
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

void ArticleController::create(const HttpRequestPtr& req,
                               std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::info("[Article] Create request", {{"userid", userId}});
    auto json = req->getJsonObject();

    if (!json || !json->isMember("headline") || !json->isMember("type")) {
        Logger::warning("[Article] Create failed: missing fields");
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "标题和类型不能为空";
        callback(HttpResponse::newHttpJsonResponse(ret));
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
                "SELECT * FROM article WHERE articleid = ?",
                [callback, articleId](const orm::Result& articleResult) {
                    if (articleResult.size() > 0) {
                        models::Article article(articleResult[0]);
                        Json::Value ret;
                        ret["code"] = 200;
                        ret["message"] = "创建成功";
                        ret["data"] = article.toJson();
                        callback(HttpResponse::newHttpJsonResponse(ret));
                    }
                },
                [callback](const orm::DrogonDbException&) {},
                articleId
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Insert error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "创建失败";
            callback(HttpResponse::newHttpJsonResponse(ret));
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
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "请求格式错误";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }

    auto dbClient = Database::getClient();

    // Check ownership
    dbClient->execSqlAsync(
        "SELECT userid FROM article WHERE articleid = ?",
        [callback, id, userId, json, dbClient](const orm::Result& result) {
            if (result.size() == 0) {
                Json::Value ret;
                ret["code"] = 404;
                ret["message"] = "文章不存在";
                callback(HttpResponse::newHttpJsonResponse(ret));
                return;
            }

            int64_t ownerId = result[0]["userid"].as<int64_t>();
            if (ownerId != std::stoll(userId)) {
                Json::Value ret;
                ret["code"] = 403;
                ret["message"] = "没有权限修改此文章";
                callback(HttpResponse::newHttpJsonResponse(ret));
                return;
            }

            std::string headline = json->get("headline", "").asString();
            std::string content = json->get("content", "").asString();
            int type = json->get("type", 0).asInt();

            dbClient->execSqlAsync(
                "UPDATE article SET headline = ?, content = ?, type = ?, updatetime = NOW() WHERE articleid = ?",
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
                headline, content, type, id
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            callback(HttpResponse::newHttpJsonResponse(ret));
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
                Json::Value ret;
                ret["code"] = 404;
                ret["message"] = "文章不存在";
                callback(HttpResponse::newHttpJsonResponse(ret));
                return;
            }

            int64_t ownerId = result[0]["userid"].as<int64_t>();
            if (ownerId != std::stoll(userId)) {
                Json::Value ret;
                ret["code"] = 403;
                ret["message"] = "没有权限删除此文章";
                callback(HttpResponse::newHttpJsonResponse(ret));
                return;
            }

            dbClient->execSqlAsync(
                "DELETE FROM article WHERE articleid = ?",
                [callback, id](const orm::Result&) {
                    Logger::info("[Article] Deleted successfully", {{"articleid", std::to_string(id)}});
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
                id
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        id
    );
}

void ArticleController::toggleRecommend(const HttpRequestPtr& req,
                                        std::function<void(const HttpResponsePtr&)>&& callback,
                                        int64_t id)
{
    Logger::info("[Article] Toggle recommend", {{"articleid", std::to_string(id)}});
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "UPDATE article SET recommended = 1 - recommended WHERE articleid = ?",
        [callback, id, dbClient](const orm::Result&) {
            dbClient->execSqlAsync(
                "SELECT recommended FROM article WHERE articleid = ?",
                [callback, id](const orm::Result& result) {
                    int recommended = result[0]["recommended"].as<int>();
                    Logger::info("[Article] Recommend toggled", {{"articleid", std::to_string(id)}, {"recommended", std::to_string(recommended)}});
                    Json::Value ret;
                    ret["code"] = 200;
                    ret["message"] = recommended ? "已推荐" : "已取消推荐";
                    ret["data"]["recommended"] = recommended;
                    callback(HttpResponse::newHttpJsonResponse(ret));
                },
                [callback](const orm::DrogonDbException&) {},
                id
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Update error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "操作失败";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        id
    );
}

void ArticleController::toggleHide(const HttpRequestPtr& req,
                                   std::function<void(const HttpResponsePtr&)>&& callback,
                                   int64_t id)
{
    Logger::info("[Article] Toggle hide", {{"articleid", std::to_string(id)}});
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "UPDATE article SET hidden = 1 - hidden WHERE articleid = ?",
        [callback, id, dbClient](const orm::Result&) {
            dbClient->execSqlAsync(
                "SELECT hidden FROM article WHERE articleid = ?",
                [callback, id](const orm::Result& result) {
                    int hidden = result[0]["hidden"].as<int>();
                    Logger::info("[Article] Hide toggled", {{"articleid", std::to_string(id)}, {"hidden", std::to_string(hidden)}});
                    Json::Value ret;
                    ret["code"] = 200;
                    ret["message"] = hidden ? "已隐藏" : "已显示";
                    ret["data"]["hidden"] = hidden;
                    callback(HttpResponse::newHttpJsonResponse(ret));
                },
                [callback](const orm::DrogonDbException&) {},
                id
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Update error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "操作失败";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        id
    );
}

} // namespace controllers
} // namespace woniunote
