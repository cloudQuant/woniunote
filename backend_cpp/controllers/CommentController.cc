/**
 * @file CommentController.cc
 * @brief Comment API Controller Implementation
 */

#include "CommentController.h"
#include "core/database.h"
#include "core/logger.h"
#include "core/response.h"
#include "models/Comment.h"
#include <drogon/HttpResponse.h>
#include <algorithm>
#include <map>
#include <vector>

using namespace drogon;

namespace woniunote {
namespace controllers {

void CommentController::listByArticle(const HttpRequestPtr& req,
                                      std::function<void(const HttpResponsePtr&)>&& callback,
                                      int64_t articleId)
{
    Logger::debug("[Comment] List by article", {{"articleid", std::to_string(articleId)}});
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT c.*, u.nickname, u.avatar FROM comment c "
        "LEFT JOIN users u ON c.userid = u.userid "
        "WHERE c.articleid = ? AND c.hidden = 0 ORDER BY c.createtime ASC",
        [callback](const orm::Result& result) {
            // Build a flat map of commentid -> json (with nickname/avatar),
            // then assemble a one-level reply tree based on replyid.
            // Top-level comments keep newest-first ordering; replies stay
            // oldest-first (natural reading order within a thread).
            std::map<int64_t, Json::Value> byId;
            std::vector<int64_t> order;  // insertion order (oldest-first)

            for (const auto& row : result) {
                models::Comment comment(row);
                Json::Value item = comment.toJson();
                if (!row["nickname"].isNull()) {
                    item["nickname"] = row["nickname"].as<std::string>();
                }
                if (!row["avatar"].isNull()) {
                    item["avatar"] = row["avatar"].as<std::string>();
                }
                item["replies"] = Json::Value(Json::arrayValue);
                int64_t cid = comment.getCommentid();
                byId[cid] = item;
                order.push_back(cid);
            }

            // Attach replies to their parent when the parent exists.
            Json::Value topLevel(Json::arrayValue);
            std::vector<int64_t> topOrder;
            for (int64_t cid : order) {
                Json::Value& node = byId[cid];
                int64_t replyId = node["replyid"].asInt64();
                auto parentIt = (replyId > 0) ? byId.find(replyId) : byId.end();
                if (replyId > 0 && parentIt != byId.end()) {
                    parentIt->second["replies"].append(node);
                } else {
                    topOrder.push_back(cid);
                }
            }

            // Emit top-level comments newest-first.
            for (auto it = topOrder.rbegin(); it != topOrder.rend(); ++it) {
                topLevel.append(byId[*it]);
            }

            Logger::debug("[Comment] List returned", {{"count", std::to_string(static_cast<int>(result.size()))}, {"top", std::to_string(static_cast<int>(topLevel.size()))}});
            callback(Response::success(topLevel));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[Comment] Database error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        articleId
    );
}

void CommentController::myComments(const HttpRequestPtr& req,
                                   std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::debug("[Comment] My comments", {{"userid", userId}});

    // Safe pagination parsing
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
    pageSize = std::min(pageSize, 100);
    int offset = (page - 1) * pageSize;

    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT c.*, a.headline FROM comment c "
        "LEFT JOIN article a ON c.articleid = a.articleid "
        "WHERE c.userid = ? ORDER BY c.createtime DESC LIMIT ? OFFSET ?",
        [callback](const orm::Result& result) {
            Json::Value comments(Json::arrayValue);
            for (const auto& row : result) {
                models::Comment comment(row);
                Json::Value item = comment.toJson();
                if (!row["headline"].isNull()) {
                    item["headline"] = row["headline"].as<std::string>();
                }
                comments.append(item);
            }
            callback(Response::success(comments));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[Comment] Database error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        std::stoll(userId), pageSize, offset
    );
}

void CommentController::create(const HttpRequestPtr& req,
                               std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::info("[Comment] Create request", {{"userid", userId}});
    auto json = req->getJsonObject();

    if (!json || !json->isMember("articleid") || !json->isMember("content")) {
        Logger::warning("[Comment] Create failed: missing fields");
        callback(Response::badRequest("文章ID和内容不能为空"));
        return;
    }

    int64_t articleId = (*json)["articleid"].asInt64();
    std::string content = (*json)["content"].asString();
    int64_t replyId = json->get("replyid", 0).asInt64();
    std::string ipaddr = req->getPeerAddr().toIp();

    if (content.empty()) {
        callback(Response::badRequest("评论内容不能为空"));
        return;
    }

    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "INSERT INTO comment (userid, articleid, content, ipaddr, replyid, createtime, updatetime) "
        "VALUES (?, ?, ?, ?, ?, NOW(), NOW())",
        [callback, articleId, dbClient, userId](const orm::Result& result) {
            int64_t commentId = result.insertId();
            Logger::info("[Comment] Created", {{"commentid", std::to_string(commentId)}, {"articleid", std::to_string(articleId)}, {"userid", userId}});
            dbClient->execSqlAsync(
                "UPDATE article SET replycount = replycount + 1 WHERE articleid = ?",
                [](const orm::Result&) {},
                [](const orm::DrogonDbException&) {},
                articleId
            );

            Json::Value data;
            data["commentid"] = static_cast<Json::Int64>(commentId);
            callback(Response::ok("评论成功", data));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[Comment] Insert error: " + std::string(e.base().what()));
            callback(Response::serverError("评论失败"));
        },
        std::stoll(userId), articleId, content, ipaddr, replyId
    );
}

void CommentController::remove(const HttpRequestPtr& req,
                               std::function<void(const HttpResponsePtr&)>&& callback,
                               int64_t id)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::info("[Comment] Delete request", {{"userid", userId}, {"commentid", std::to_string(id)}});
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT userid, articleid FROM comment WHERE commentid = ?",
        [callback, id, userId, dbClient](const orm::Result& result) {
            if (result.size() == 0) {
                Logger::debug("[Comment] Not found", {{"commentid", std::to_string(id)}});
                callback(Response::notFound("评论不存在"));
                return;
            }

            int64_t ownerId = result[0]["userid"].as<int64_t>();
            int64_t articleId = result[0]["articleid"].as<int64_t>();

            if (ownerId != std::stoll(userId)) {
                Logger::warning("[Comment] Delete denied: not owner", {{"commentid", std::to_string(id)}, {"userid", userId}});
                callback(Response::forbidden("没有权限删除此评论"));
                return;
            }

            dbClient->execSqlAsync(
                "DELETE FROM comment WHERE commentid = ?",
                [callback, articleId, dbClient, id](const orm::Result&) {
                    Logger::info("[Comment] Deleted", {{"commentid", std::to_string(id)}, {"articleid", std::to_string(articleId)}});
                    dbClient->execSqlAsync(
                        "UPDATE article SET replycount = replycount - 1 WHERE articleid = ? AND replycount > 0",
                        [](const orm::Result&) {},
                        [](const orm::DrogonDbException&) {},
                        articleId
                    );
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

void CommentController::vote(const HttpRequestPtr& req,
                             std::function<void(const HttpResponsePtr&)>&& callback,
                             int64_t id)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    Logger::debug("[Comment] Vote request", {{"userid", userId}, {"commentid", std::to_string(id)}});
    auto json = req->getJsonObject();

    if (!json || !json->isMember("vote_type")) {
        Logger::warning("[Comment] Vote failed: missing vote_type");
        callback(Response::badRequest("请指定投票类型"));
        return;
    }

    int voteType = (*json)["vote_type"].asInt();  // 1: agree, -1: oppose
    if (voteType != 1 && voteType != -1) {
        callback(Response::badRequest("无效的投票类型"));
        return;
    }

    auto dbClient = Database::getClient();

    // Check if already voted
    dbClient->execSqlAsync(
        "SELECT id FROM comment_vote WHERE userid = ? AND commentid = ?",
        [callback, id, userId, voteType, dbClient](const orm::Result& result) {
            if (result.size() > 0) {
                Logger::debug("[Comment] Vote failed: already voted", {{"userid", userId}, {"commentid", std::to_string(id)}});
                callback(Response::badRequest("您已经投过票了"));
                return;
            }

            // Insert vote record
            dbClient->execSqlAsync(
                "INSERT INTO comment_vote (userid, commentid, vote_type, createtime) VALUES (?, ?, ?, NOW())",
                [callback, id, voteType, dbClient, userId](const orm::Result&) {
                    // Update comment vote count. Column name is from a fixed
                    // allow-list (not user input), so interpolation is safe.
                    std::string field = voteType > 0 ? "agreecount" : "opposecount";
                    std::string sql = "UPDATE comment SET " + field + " = " + field + " + 1 WHERE commentid = ?";

                    dbClient->execSqlAsync(
                        sql,
                        [callback, voteType, id, userId](const orm::Result&) {
                            Logger::info("[Comment] Voted", {{"commentid", std::to_string(id)}, {"userid", userId}, {"type", voteType > 0 ? "agree" : "oppose"}});
                            callback(Response::ok(voteType > 0 ? "点赞成功" : "踩成功"));
                        },
                        [callback](const orm::DrogonDbException& e) {
                            Logger::error("Vote count update error: " + std::string(e.base().what()));
                            callback(Response::serverError("投票失败"));
                        },
                        id
                    );
                },
                [callback](const orm::DrogonDbException& e) {
                    Logger::error("Vote error: " + std::string(e.base().what()));
                    callback(Response::serverError("投票失败"));
                },
                std::stoll(userId), id, voteType
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        std::stoll(userId), id
    );
}

} // namespace controllers
} // namespace woniunote
