/**
 * @file CommentVote.cc
 * @brief CommentVote Model Implementation
 */

#include "CommentVote.h"
#include "core/logger.h"

namespace woniunote {
namespace models {

CommentVote::CommentVote(const drogon::orm::Row& row)
{
    if (!row["id"].isNull()) id_ = row["id"].as<int64_t>();
    Logger::debug("[Model] CommentVote loaded", {{"id", std::to_string(id_)}});
    if (!row["userid"].isNull()) userid_ = row["userid"].as<int64_t>();
    if (!row["commentid"].isNull()) commentid_ = row["commentid"].as<int64_t>();
    if (!row["vote_type"].isNull()) voteType_ = row["vote_type"].as<int>();
}

Json::Value CommentVote::toJson() const
{
    Json::Value ret;
    ret["id"] = static_cast<Json::Int64>(id_);
    ret["userid"] = static_cast<Json::Int64>(userid_);
    ret["commentid"] = static_cast<Json::Int64>(commentid_);
    ret["vote_type"] = voteType_;
    return ret;
}

} // namespace models
} // namespace woniunote
