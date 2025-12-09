/**
 * @file CommentController.cc
 * @brief Comment API Controller Implementation
 */

#include "CommentController.h"
#include "core/database.h"
#include "core/logger.h"
#include "models/Comment.h"
#include <drogon/HttpResponse.h>

using namespace drogon;

namespace woniunote {
namespace controllers {

void CommentController::listByArticle(const HttpRequestPtr& req,
                                      std::function<void(const HttpResponsePtr&)>&& callback,
                                      int64_t articleId)
{
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT c.*, u.nickname, u.avatar FROM comment c "
        "LEFT JOIN users u ON c.userid = u.userid "
        "WHERE c.articleid = ? AND c.hidden = 0 ORDER BY c.createtime DESC",
        [callback](const orm::Result& result) {
            Json::Value comments(Json::arrayValue);
            for (const auto& row : result) {
                models::Comment comment(row);
                Json::Value item = comment.toJson();
                if (!row["nickname"].isNull()) {
                    item["nickname"] = row["nickname"].as<std::string>();
                }
                if (!row["avatar"].isNull()) {
                    item["avatar"] = row["avatar"].as<std::string>();
                }
                comments.append(item);
            }

            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "success";
            ret["data"] = comments;
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        articleId
    );
}

void CommentController::create(const HttpRequestPtr& req,
                               std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto json = req->getJsonObject();

    if (!json || !json->isMember("articleid") || !json->isMember("content")) {
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "文章ID和内容不能为空";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }

    int64_t articleId = (*json)["articleid"].asInt64();
    std::string content = (*json)["content"].asString();
    int64_t replyId = json->get("replyid", 0).asInt64();
    std::string ipaddr = req->getPeerAddr().toIp();

    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "INSERT INTO comment (userid, articleid, content, ipaddr, replyid, createtime, updatetime) "
        "VALUES (?, ?, ?, ?, ?, NOW(), NOW())",
        [callback, articleId, dbClient](const orm::Result& result) {
            // Update reply count
            dbClient->execSqlAsync(
                "UPDATE article SET replycount = replycount + 1 WHERE articleid = ?",
                [](const orm::Result&) {},
                [](const orm::DrogonDbException&) {},
                articleId
            );

            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "评论成功";
            ret["data"]["commentid"] = static_cast<Json::Int64>(result.insertId());
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Insert error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "评论失败";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        std::stoll(userId), articleId, content, ipaddr, replyId
    );
}

void CommentController::remove(const HttpRequestPtr& req,
                               std::function<void(const HttpResponsePtr&)>&& callback,
                               int64_t id)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT userid, articleid FROM comment WHERE commentid = ?",
        [callback, id, userId, dbClient](const orm::Result& result) {
            if (result.size() == 0) {
                Json::Value ret;
                ret["code"] = 404;
                ret["message"] = "评论不存在";
                callback(HttpResponse::newHttpJsonResponse(ret));
                return;
            }

            int64_t ownerId = result[0]["userid"].as<int64_t>();
            int64_t articleId = result[0]["articleid"].as<int64_t>();
            
            if (ownerId != std::stoll(userId)) {
                Json::Value ret;
                ret["code"] = 403;
                ret["message"] = "没有权限删除此评论";
                callback(HttpResponse::newHttpJsonResponse(ret));
                return;
            }

            dbClient->execSqlAsync(
                "DELETE FROM comment WHERE commentid = ?",
                [callback, articleId, dbClient](const orm::Result&) {
                    // Update reply count
                    dbClient->execSqlAsync(
                        "UPDATE article SET replycount = replycount - 1 WHERE articleid = ? AND replycount > 0",
                        [](const orm::Result&) {},
                        [](const orm::DrogonDbException&) {},
                        articleId
                    );

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

void CommentController::vote(const HttpRequestPtr& req,
                             std::function<void(const HttpResponsePtr&)>&& callback,
                             int64_t id)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto json = req->getJsonObject();

    if (!json || !json->isMember("vote_type")) {
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "请指定投票类型";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }

    int voteType = (*json)["vote_type"].asInt();  // 1: agree, -1: oppose

    auto dbClient = Database::getClient();

    // Check if already voted
    dbClient->execSqlAsync(
        "SELECT id FROM comment_vote WHERE userid = ? AND commentid = ?",
        [callback, id, userId, voteType, dbClient](const orm::Result& result) {
            if (result.size() > 0) {
                Json::Value ret;
                ret["code"] = 400;
                ret["message"] = "您已经投过票了";
                callback(HttpResponse::newHttpJsonResponse(ret));
                return;
            }

            // Insert vote record
            dbClient->execSqlAsync(
                "INSERT INTO comment_vote (userid, commentid, vote_type, createtime) VALUES (?, ?, ?, NOW())",
                [callback, id, voteType, dbClient](const orm::Result&) {
                    // Update comment vote count
                    std::string field = voteType > 0 ? "agreecount" : "opposecount";
                    std::string sql = "UPDATE comment SET " + field + " = " + field + " + 1 WHERE commentid = ?";
                    
                    dbClient->execSqlAsync(
                        sql,
                        [callback, voteType](const orm::Result&) {
                            Json::Value ret;
                            ret["code"] = 200;
                            ret["message"] = voteType > 0 ? "点赞成功" : "踩成功";
                            callback(HttpResponse::newHttpJsonResponse(ret));
                        },
                        [callback](const orm::DrogonDbException&) {},
                        id
                    );
                },
                [callback](const orm::DrogonDbException& e) {
                    Logger::error("Vote error: " + std::string(e.base().what()));
                    Json::Value ret;
                    ret["code"] = 500;
                    ret["message"] = "投票失败";
                    callback(HttpResponse::newHttpJsonResponse(ret));
                },
                std::stoll(userId), id, voteType
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Database error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        std::stoll(userId), id
    );
}

} // namespace controllers
} // namespace woniunote
