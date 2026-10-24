/**
 * @file CommentController.cc
 * @brief Comment API Controller Implementation
 */

#include "CommentController.h"
#include "core/database.h"
#include "core/logger.h"
#include "core/response.h"
#include "core/transaction_response.h"
#include "models/Comment.h"
#include <drogon/HttpResponse.h>
#include <algorithm>
#include <atomic>
#include <charconv>
#include <chrono>
#include <cstdint>
#include <limits>
#include <map>
#include <memory>
#include <mutex>
#include <string_view>
#include <vector>

using namespace drogon;

namespace woniunote {
namespace controllers {

namespace {

bool parsePositiveId(const std::string& raw, int64_t& value)
{
    const auto parsed = std::from_chars(raw.data(), raw.data() + raw.size(), value, 10);
    return !raw.empty() && parsed.ec == std::errc{} && parsed.ptr == raw.data() + raw.size() &&
           value > 0 && value <= std::numeric_limits<int32_t>::max();
}

bool parseJsonInt32Id(const Json::Value& value, int64_t& parsed, bool allowZero)
{
    if (value.isInt64()) {
        parsed = value.asInt64();
    } else if (value.isUInt64()) {
        const uint64_t unsignedValue = value.asUInt64();
        if (unsignedValue > static_cast<uint64_t>(std::numeric_limits<int32_t>::max())) {
            return false;
        }
        parsed = static_cast<int64_t>(unsignedValue);
    } else {
        return false;
    }
    return (allowZero ? parsed >= 0 : parsed > 0) &&
           parsed <= std::numeric_limits<int32_t>::max();
}

bool parsePositiveJsonId(const Json::Value& value, int64_t& parsed)
{
    return parseJsonInt32Id(value, parsed, false);
}

class ResponseSlot final {
public:
    explicit ResponseSlot(HttpResponsePtr response) : response_(std::move(response)) {}

    void set(HttpResponsePtr response)
    {
        std::lock_guard<std::mutex> lock(mutex_);
        response_ = std::move(response);
    }

    HttpResponsePtr get() const
    {
        std::lock_guard<std::mutex> lock(mutex_);
        return response_;
    }

private:
    mutable std::mutex mutex_;
    HttpResponsePtr response_;
};

struct LockedComment {
    int64_t articleId = 0;
    int64_t replyId = 0;
    int hidden = 0;
};

using LockedCommentMap = std::map<int64_t, LockedComment>;

void lockVoteCommentRows(
    const std::shared_ptr<orm::Transaction>& trans,
    const std::shared_ptr<TransactionResponse>& completion,
    const std::shared_ptr<ResponseSlot>& response,
    const std::shared_ptr<LockedCommentMap>& locked,
    const std::shared_ptr<std::vector<int64_t>>& commentIds,
    size_t index,
    const std::function<void()>& onLocked)
{
    if (completion->completed()) {
        trans->rollback();
        return;
    }
    if (index >= commentIds->size()) {
        onLocked();
        return;
    }

    const int64_t commentId = (*commentIds)[index];
    trans->execSqlAsync(
        "SELECT articleid, replyid, hidden FROM comment WHERE commentid = ? FOR UPDATE",
        [trans, completion, response, locked, commentIds, index, commentId, onLocked]
        (const orm::Result& result) {
            if (completion->completed()) {
                trans->rollback();
                return;
            }
            if (result.empty()) {
                response->set(Response::notFound("评论不存在"));
                trans->rollback();
                completion->complete(TransactionOutcome::aborted);
                return;
            }

            LockedComment row;
            row.articleId = result[0]["articleid"].as<int64_t>();
            row.replyId = result[0]["replyid"].isNull()
                ? 0
                : result[0]["replyid"].as<int64_t>();
            row.hidden = result[0]["hidden"].as<int>();
            locked->emplace(commentId, row);
            lockVoteCommentRows(trans, completion, response, locked, commentIds,
                                index + 1, onLocked);
        },
        [trans, completion, response](const orm::DrogonDbException& error) {
            Logger::error("[Comment] Vote comment lock failed: " + std::string(error.base().what()));
            response->set(Response::serverError("投票失败"));
            trans->rollback();
            completion->complete(completion->failureOutcome(error));
        },
        commentId);
}

bool isDuplicateKey(const orm::DrogonDbException& error)
{
    const auto* sqlError = dynamic_cast<const orm::SqlError*>(&error.base());
    if (sqlError == nullptr ||
        (sqlError->errcode() != 0 && sqlError->errcode() != 1062) ||
        (sqlError->extendedErrcode() != 0 && sqlError->extendedErrcode() != 1062)) {
        return false;
    }

    // Drogon 1.9.11's MySQL adapter constructs SqlError(message, query),
    // which leaves both numeric error-code fields at zero. Only classify the
    // vote pair's named unique index as a duplicate; other constraints remain
    // server errors.
    const std::string_view message(error.base().what());
    constexpr std::string_view duplicatePrefix{"Duplicate entry "};
    constexpr std::string_view keyMarker{" for key "};
    if (message.compare(0, duplicatePrefix.size(), duplicatePrefix) != 0) {
        return false;
    }

    const size_t marker = message.rfind(keyMarker);
    if (marker == std::string_view::npos) {
        return false;
    }
    const size_t keyStart = marker + keyMarker.size();
    if (keyStart + 2 > message.size()) {
        return false;
    }

    const char quote = message[keyStart];
    if ((quote != '\'' && quote != '`') || message.back() != quote) {
        return false;
    }
    const std::string_view key = message.substr(keyStart + 1,
                                                message.size() - keyStart - 2);
    const size_t separator = key.rfind('.');
    const std::string_view keyName = separator == std::string_view::npos
        ? key
        : key.substr(separator + 1);
    return keyName == "uk_comment_user";
}

bool articleIsVisibleTo(const orm::Row& row, const std::string& viewerId)
{
    const bool owner = !viewerId.empty() &&
                       std::to_string(row["userid"].as<int64_t>()) == viewerId;
    return (row["hidden"].as<int>() == 0 && row["drafted"].as<int>() == 0) || owner;
}

bool articleIsVisibleTo(const orm::Row& row, const std::string& viewerId,
                        const char* ownerColumn, const char* hiddenColumn,
                        const char* draftedColumn)
{
    const bool owner = !viewerId.empty() &&
                       std::to_string(row[ownerColumn].as<int64_t>()) == viewerId;
    return (row[hiddenColumn].as<int>() == 0 && row[draftedColumn].as<int>() == 0) || owner;
}

void setVoteFailure(const std::shared_ptr<ResponseSlot>& response,
                    const orm::DrogonDbException& error)
{
    if (isDuplicateKey(error)) {
        Logger::debug("[Comment] Duplicate vote rejected");
        response->set(Response::badRequest("您已经投过票了"));
    } else {
        Logger::error("[Comment] Vote insert failed");
        response->set(Response::serverError("投票失败"));
    }
}

} // namespace

void CommentController::listByArticle(const HttpRequestPtr& req,
                                      std::function<void(const HttpResponsePtr&)>&& callback,
                                      int64_t articleId)
{
    Logger::debug("[Comment] List by article", {{"articleid", std::to_string(articleId)}});
    auto dbClient = Database::getClient();
    const auto viewerAttrs = req->getAttributes();
    const std::string viewerId = viewerAttrs->find("user_id")
        ? viewerAttrs->get<std::string>("user_id")
        : std::string();

    if (articleId <= 0) {
        callback(Response::notFound("文章不存在"));
        return;
    }

    dbClient->execSqlAsync(
        "SELECT a.userid AS article_owner_userid, a.hidden AS article_hidden, "
        "a.drafted AS article_drafted, c.*, u.nickname, u.avatar "
        "FROM article a "
        "LEFT JOIN comment c ON c.articleid = a.articleid AND c.hidden = 0 "
        "LEFT JOIN users u ON c.userid = u.userid "
        "WHERE a.articleid = ? "
        "ORDER BY c.createtime ASC, c.commentid ASC",
        [callback, viewerId](const orm::Result& result) {
            if (result.empty() ||
                !articleIsVisibleTo(result[0], viewerId, "article_owner_userid",
                                     "article_hidden", "article_drafted")) {
                callback(Response::notFound("文章不存在"));
                return;
            }

            // A LEFT JOIN returns one article row with a NULL comment for an
            // empty list. Do not feed that row to the comment model.
            std::map<int64_t, Json::Value> byId;
            std::map<int64_t, int64_t> parentIds;
            std::vector<int64_t> order;
            std::vector<int64_t> roots;
            std::map<int64_t, bool> isRoot;

            for (const auto& row : result) {
                if (row["commentid"].isNull()) {
                    continue;
                }
                models::Comment comment(row);
                Json::Value item = comment.toJson();
                if (!row["nickname"].isNull()) {
                    item["nickname"] = row["nickname"].as<std::string>();
                }
                if (!row["avatar"].isNull()) {
                    item["avatar"] = row["avatar"].as<std::string>();
                }
                item["replies"] = Json::Value(Json::arrayValue);
                const int64_t commentId = comment.getCommentid();
                const int64_t replyId = comment.getReplyid();
                byId.emplace(commentId, std::move(item));
                parentIds[commentId] = replyId;
                // The legacy schema represents roots as NULL or 0.
                // Treat negative values as malformed references rather
                // than silently promoting them to roots.
                isRoot[commentId] = replyId == 0;
                order.push_back(commentId);
            }

            // Keep only root comments and replies whose visible parent is a
            // root in this same article. Orphans, cross-article links, deep
            // replies, and cycles are omitted rather than promoted.
            Json::Value topLevel(Json::arrayValue);
            for (int64_t commentId : order) {
                const int64_t replyId = parentIds[commentId];
                if (replyId == 0) {
                    roots.push_back(commentId);
                    continue;
                }
                if (replyId < 0) {
                    continue;
                }
                const auto parent = byId.find(replyId);
                if (parent != byId.end() && isRoot[replyId]) {
                    parent->second["replies"].append(byId[commentId]);
                }
            }

            for (auto it = roots.rbegin(); it != roots.rend(); ++it) {
                topLevel.append(byId[*it]);
            }
            Logger::debug(
                "[Comment] List returned",
                {{"count", std::to_string(static_cast<int>(order.size()))},
                 {"top", std::to_string(static_cast<int>(topLevel.size()))}});
            callback(Response::success(topLevel));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[Comment] Database error: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        articleId);
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
    const bool hasUserAttr = req->getAttributes()->find("user_id");
    int64_t userId = 0;
    if (!hasUserAttr ||
        !parsePositiveId(req->getAttributes()->get<std::string>("user_id"), userId)) {
        callback(Response::unauthorized("身份无效"));
        return;
    }
    Logger::info("[Comment] Create request", {{"userid", std::to_string(userId)}});
    const auto json = req->getJsonObject();

    int64_t articleId = 0;
    if (!json || !json->isObject() || !json->isMember("articleid") || !json->isMember("content") ||
        !parsePositiveJsonId((*json)["articleid"], articleId) || !(*json)["content"].isString()) {
        callback(Response::badRequest("文章ID和内容不能为空"));
        return;
    }
    const std::string content = (*json)["content"].asString();
    if (content.empty()) {
        callback(Response::badRequest("评论内容不能为空"));
        return;
    }

    int64_t replyId = 0;
    if (json->isMember("replyid") && !(*json)["replyid"].isNull() &&
        !parseJsonInt32Id((*json)["replyid"], replyId, true)) {
        callback(Response::badRequest("回复目标无效"));
        return;
    }
    const std::string ipaddr = req->getPeerAddr().toIp();
    const auto response = std::make_shared<ResponseSlot>(Response::serverError("评论失败"));
    const auto insertedId = std::make_shared<std::atomic<int64_t>>(0);
    auto completion = TransactionResponse::create(
        std::chrono::seconds(5),
        [callback, response, insertedId, articleId](TransactionOutcome outcome,
                                                     const std::string& requestId) {
            if (outcome == TransactionOutcome::committed) {
                Json::Value data;
                data["commentid"] = static_cast<Json::Int64>(insertedId->load(std::memory_order_acquire));
                Logger::info("[Comment] Created",
                             {{"commentid", std::to_string(insertedId->load(std::memory_order_acquire))},
                              {"articleid", std::to_string(articleId)}});
                callback(Response::ok("评论成功", data));
            } else if (outcome == TransactionOutcome::unknown) {
                Logger::error("[Comment] Create outcome unknown",
                              {{"request_id", requestId}, {"articleid", std::to_string(articleId)}});
                callback(TransactionResponse::unknownResponse(requestId));
            } else if (outcome == TransactionOutcome::unavailable) {
                callback(Response::error(503, "数据库暂时不可用", k503ServiceUnavailable));
            } else {
                callback(response->get());
            }
        },
        TransactionOutcome::unavailable);

    try {
        Database::beginTransaction(
            [userId, articleId, replyId, content, ipaddr, completion, response, insertedId]
            (const std::shared_ptr<orm::Transaction>& trans) {
                if (!trans) {
                    completion->complete(TransactionOutcome::unavailable);
                    return;
                }
                if (completion->completed()) {
                    trans->rollback();
                    return;
                }
                trans->setCommitCallback([completion](bool committed) {
                    completion->complete(committed ? TransactionOutcome::committed
                                                   : TransactionOutcome::unknown);
                });

                trans->execSqlAsync(
                    "SELECT userid, hidden, drafted FROM article WHERE articleid = ? FOR UPDATE",
                    [trans, userId, articleId, replyId, content, ipaddr, completion,
                     response, insertedId](const orm::Result& articleResult) {
                        if (completion->completed()) {
                            trans->rollback();
                            return;
                        }
                        if (articleResult.empty() ||
                            !articleIsVisibleTo(articleResult[0], std::to_string(userId))) {
                            response->set(Response::notFound("文章不存在"));
                            trans->rollback();
                            completion->complete(TransactionOutcome::aborted);
                            return;
                        }

                        auto insertComment = [trans, userId, articleId, replyId, content, ipaddr,
                                              completion, response, insertedId]() {
                            if (!completion->beginWriting()) {
                                trans->rollback();
                                return;
                            }
                            trans->execSqlAsync(
                                "INSERT INTO comment (userid, articleid, content, ipaddr, replyid, createtime, updatetime) "
                                "VALUES (?, ?, ?, ?, ?, NOW(), NOW())",
                                [trans, articleId, completion, response, insertedId]
                                (const orm::Result& insertResult) {
                                    if (completion->completed()) {
                                        trans->rollback();
                                        return;
                                    }
                                    const int64_t commentId = insertResult.insertId();
                                    if (commentId <= 0) {
                                        response->set(Response::serverError("评论失败"));
                                        trans->rollback();
                                        completion->complete(TransactionOutcome::unknown);
                                        return;
                                    }
                                    insertedId->store(commentId, std::memory_order_release);
                                    trans->execSqlAsync(
                                        "UPDATE article SET replycount = replycount + 1 WHERE articleid = ?",
                                        [trans, completion, response](const orm::Result& updateResult) {
                                            if (completion->completed()) {
                                                trans->rollback();
                                                return;
                                            }
                                            if (updateResult.affectedRows() != 1) {
                                                response->set(Response::serverError("评论失败"));
                                                trans->rollback();
                                                completion->complete(TransactionOutcome::aborted);
                                                return;
                                            }
                                        },
                                        [trans, completion, response](const orm::DrogonDbException& error) {
                                            Logger::error("[Comment] Reply count update error: " +
                                                          std::string(error.base().what()));
                                            response->set(Response::serverError("评论失败"));
                                            trans->rollback();
                                            completion->complete(completion->failureOutcome(error));
                                        },
                                        articleId);
                                },
                                [trans, completion, response](const orm::DrogonDbException& error) {
                                    Logger::error("[Comment] Insert error: " + std::string(error.base().what()));
                                    response->set(Response::serverError("评论失败"));
                                    trans->rollback();
                                    completion->complete(completion->failureOutcome(error));
                                },
                                userId, articleId, content, ipaddr, replyId);
                        };

                        if (replyId <= 0) {
                            insertComment();
                            return;
                        }

                        trans->execSqlAsync(
                            "SELECT articleid, replyid, hidden FROM comment WHERE commentid = ? FOR UPDATE",
                            [trans, articleId, completion, response, insertComment]
                            (const orm::Result& parentResult) {
                                if (completion->completed()) {
                                    trans->rollback();
                                    return;
                                }
                                if (parentResult.empty() ||
                                    parentResult[0]["articleid"].as<int64_t>() != articleId ||
                                    parentResult[0]["hidden"].as<int>() != 0 ||
                                    (!parentResult[0]["replyid"].isNull() &&
                                     parentResult[0]["replyid"].as<int64_t>() != 0)) {
                                    response->set(Response::notFound("评论不存在"));
                                    trans->rollback();
                                    completion->complete(TransactionOutcome::aborted);
                                    return;
                                }
                                insertComment();
                            },
                            [trans, completion, response](const orm::DrogonDbException& error) {
                                Logger::error("[Comment] Reply target lookup failed: " +
                                              std::string(error.base().what()));
                                response->set(Response::serverError("评论失败"));
                                trans->rollback();
                                completion->complete(completion->failureOutcome(error));
                            },
                            replyId);
                    },
                    [trans, completion, response](const orm::DrogonDbException& error) {
                        Logger::error("[Comment] Article visibility lookup failed: " +
                                      std::string(error.base().what()));
                        response->set(Response::serverError("评论失败"));
                        trans->rollback();
                        completion->complete(completion->failureOutcome(error));
                    },
                    articleId);
            });
    } catch (const std::exception& error) {
        Logger::error("[Comment] Could not start create transaction: " + std::string(error.what()));
        completion->complete(TransactionOutcome::unavailable);
    }
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
    const bool hasUserAttr = req->getAttributes()->find("user_id");
    int64_t userId = 0;
    if (!hasUserAttr ||
        !parsePositiveId(req->getAttributes()->get<std::string>("user_id"), userId)) {
        callback(Response::unauthorized("身份无效"));
        return;
    }
    Logger::debug("[Comment] Vote request",
                  {{"userid", std::to_string(userId)}, {"commentid", std::to_string(id)}});
    const auto json = req->getJsonObject();
    if (!json || !json->isObject() || !json->isMember("vote_type") ||
        !(*json)["vote_type"].isInt()) {
        callback(Response::badRequest("请指定有效的投票类型"));
        return;
    }

    const int voteType = (*json)["vote_type"].asInt();
    if (id <= 0 || (voteType != 1 && voteType != -1)) {
        callback(Response::badRequest("无效的投票类型"));
        return;
    }

    const auto response = std::make_shared<ResponseSlot>(Response::serverError("投票失败"));
    auto completion = TransactionResponse::create(
        std::chrono::seconds(5),
        [callback, response, id, userId, voteType](TransactionOutcome outcome,
                                                   const std::string& requestId) {
            if (outcome == TransactionOutcome::committed) {
                Logger::info("[Comment] Voted",
                             {{"commentid", std::to_string(id)},
                              {"userid", std::to_string(userId)},
                              {"type", voteType > 0 ? "agree" : "oppose"}});
                callback(Response::ok(voteType > 0 ? "点赞成功" : "踩成功"));
            } else if (outcome == TransactionOutcome::unknown) {
                Logger::error("[Comment] Vote outcome unknown",
                              {{"commentid", std::to_string(id)},
                               {"userid", std::to_string(userId)},
                               {"request_id", requestId}});
                callback(TransactionResponse::unknownResponse(requestId));
            } else if (outcome == TransactionOutcome::unavailable) {
                callback(Response::error(503, "数据库暂时不可用", k503ServiceUnavailable));
            } else {
                callback(response->get());
            }
        },
        TransactionOutcome::unavailable);

    try {
        Database::beginTransaction(
            [completion, response, id, userId, voteType]
            (const std::shared_ptr<orm::Transaction>& trans) {
                if (!trans) {
                    completion->complete(TransactionOutcome::unavailable);
                    return;
                }
                if (completion->completed()) {
                    trans->rollback();
                    return;
                }
                trans->setCommitCallback([completion](bool committed) {
                    completion->complete(committed ? TransactionOutcome::committed
                                                   : TransactionOutcome::unknown);
                });

                trans->execSqlAsync(
                    "SELECT articleid, replyid FROM comment WHERE commentid = ?",
                    [trans, completion, response, id, userId, voteType]
                    (const orm::Result& targetResult) {
                        if (completion->completed()) {
                            trans->rollback();
                            return;
                        }
                        if (targetResult.empty()) {
                            response->set(Response::notFound("评论不存在"));
                            trans->rollback();
                            completion->complete(TransactionOutcome::aborted);
                            return;
                        }

                        const int64_t articleId = targetResult[0]["articleid"].as<int64_t>();
                        const int64_t expectedParentId = targetResult[0]["replyid"].isNull()
                            ? 0
                            : targetResult[0]["replyid"].as<int64_t>();
                        if (expectedParentId < 0) {
                            response->set(Response::notFound("评论不存在"));
                            trans->rollback();
                            completion->complete(TransactionOutcome::aborted);
                            return;
                        }

                        // Lock order is article first, then comment rows by ID.
                        // This serializes visibility changes with the vote write and
                        // avoids a target/parent lock-order inversion.
                        trans->execSqlAsync(
                            "SELECT userid, hidden, drafted FROM article WHERE articleid = ? FOR UPDATE",
                            [trans, completion, response, id, userId, voteType, articleId,
                             expectedParentId](const orm::Result& articleResult) {
                                if (completion->completed()) {
                                    trans->rollback();
                                    return;
                                }
                                if (articleResult.empty()) {
                                    response->set(Response::notFound("评论不存在"));
                                    trans->rollback();
                                    completion->complete(TransactionOutcome::aborted);
                                    return;
                                }
                                const bool articleOwner = articleResult[0]["userid"].as<int64_t>() == userId;
                                const bool publicArticle = articleResult[0]["hidden"].as<int>() == 0 &&
                                                           articleResult[0]["drafted"].as<int>() == 0;
                                if (!publicArticle && !articleOwner) {
                                    response->set(Response::notFound("评论不存在"));
                                    trans->rollback();
                                    completion->complete(TransactionOutcome::aborted);
                                    return;
                                }

                                auto commentIds = std::make_shared<std::vector<int64_t>>();
                                commentIds->push_back(id);
                                if (expectedParentId > 0 && expectedParentId != id) {
                                    commentIds->push_back(expectedParentId);
                                }
                                std::sort(commentIds->begin(), commentIds->end());
                                auto locked = std::make_shared<LockedCommentMap>();
                                auto validateAndWrite = [trans, completion, response, id, userId,
                                                         voteType, articleId, expectedParentId,
                                                         locked]() {
                                    const auto target = locked->find(id);
                                    if (target == locked->end() || target->second.hidden != 0 ||
                                        target->second.articleId != articleId ||
                                        target->second.replyId != expectedParentId) {
                                        response->set(Response::notFound("评论不存在"));
                                        trans->rollback();
                                        completion->complete(TransactionOutcome::aborted);
                                        return;
                                    }
                                    if (expectedParentId > 0) {
                                        const auto parent = locked->find(expectedParentId);
                                        if (expectedParentId == id || parent == locked->end() ||
                                            parent->second.hidden != 0 ||
                                            parent->second.articleId != articleId ||
                                            parent->second.replyId != 0) {
                                            response->set(Response::notFound("评论不存在"));
                                            trans->rollback();
                                            completion->complete(TransactionOutcome::aborted);
                                            return;
                                        }
                                    }
                                    if (!completion->beginWriting()) {
                                        trans->rollback();
                                        return;
                                    }

                                    trans->execSqlAsync(
                                        "INSERT INTO comment_votes (commentid, userid, vote_type, createtime) "
                                        "VALUES (?, ?, ?, NOW())",
                                        [trans, completion, response, id, voteType](const orm::Result&) {
                                            if (completion->completed()) {
                                                trans->rollback();
                                                return;
                                            }
                                            const std::string column = voteType > 0 ? "agreecount" : "opposecount";
                                            const std::string sql = "UPDATE comment SET " + column + " = " + column +
                                                                    " + 1 WHERE commentid = ? AND hidden = 0";
                                            trans->execSqlAsync(
                                                sql,
                                                [trans, completion, response](const orm::Result& updateResult) {
                                                    if (completion->completed()) {
                                                        trans->rollback();
                                                        return;
                                                    }
                                                    if (updateResult.affectedRows() != 1) {
                                                        response->set(Response::notFound("评论不存在"));
                                                        trans->rollback();
                                                        completion->complete(TransactionOutcome::aborted);
                                                        return;
                                                    }
                                                },
                                                [trans, completion, response](const orm::DrogonDbException& error) {
                                                    Logger::error("[Comment] Vote count update error: " +
                                                                  std::string(error.base().what()));
                                                    response->set(Response::serverError("投票失败"));
                                                    trans->rollback();
                                                    completion->complete(completion->failureOutcome(error));
                                                },
                                                id);
                                        },
                                        [trans, completion, response](const orm::DrogonDbException& error) {
                                            setVoteFailure(response, error);
                                            trans->rollback();
                                            completion->complete(completion->failureOutcome(error));
                                        },
                                        id, userId, voteType);
                                };

                                lockVoteCommentRows(trans, completion, response, locked,
                                                    commentIds, 0, validateAndWrite);
                            },
                            [trans, completion, response](const orm::DrogonDbException& error) {
                                Logger::error("[Comment] Vote article visibility lookup error: " +
                                              std::string(error.base().what()));
                                response->set(Response::serverError("投票失败"));
                                trans->rollback();
                                completion->complete(completion->failureOutcome(error));
                            },
                            articleId);
                    },
                    [trans, completion, response](const orm::DrogonDbException& error) {
                        Logger::error("[Comment] Vote target lookup error: " +
                                      std::string(error.base().what()));
                        response->set(Response::serverError("投票失败"));
                        trans->rollback();
                        completion->complete(completion->failureOutcome(error));
                    },
                    id);
            });
    } catch (const std::exception& error) {
        Logger::error("[Comment] Could not start vote transaction: " + std::string(error.what()));
        completion->complete(TransactionOutcome::unavailable);
    }
}

} // namespace controllers
} // namespace woniunote
