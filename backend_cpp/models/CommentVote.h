/**
 * @file CommentVote.h
 * @brief CommentVote Model for Drogon ORM
 */

#ifndef WONIUNOTE_MODELS_COMMENT_VOTE_H
#define WONIUNOTE_MODELS_COMMENT_VOTE_H

#include <drogon/orm/Mapper.h>
#include <json/json.h>

namespace woniunote {
namespace models {

class CommentVote {
public:
    static constexpr const char* tableName = "comment_vote";
    static constexpr const char* primaryKeyName = "id";

    CommentVote() = default;
    explicit CommentVote(const drogon::orm::Row& row);

    int64_t getId() const { return id_; }
    int64_t getUserid() const { return userid_; }
    int64_t getCommentid() const { return commentid_; }
    int getVoteType() const { return voteType_; }

    void setId(int64_t v) { id_ = v; }
    void setUserid(int64_t v) { userid_ = v; }
    void setCommentid(int64_t v) { commentid_ = v; }
    void setVoteType(int v) { voteType_ = v; }

    Json::Value toJson() const;

private:
    int64_t id_ = 0;
    int64_t userid_ = 0;
    int64_t commentid_ = 0;
    int voteType_ = 0;  // 1: agree, -1: oppose
};

} // namespace models
} // namespace woniunote

#endif // WONIUNOTE_MODELS_COMMENT_VOTE_H
