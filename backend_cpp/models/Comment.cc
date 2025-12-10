/**
 * @file Comment.cc
 * @brief Comment Model Implementation
 */

#include "Comment.h"
#include "core/logger.h"

namespace woniunote {
namespace models {

Comment::Comment(const drogon::orm::Row& row)
{
    if (!row["commentid"].isNull()) commentid_ = row["commentid"].as<int64_t>();
    Logger::debug("[Model] Comment loaded", {{"commentid", std::to_string(commentid_)}});
    if (!row["userid"].isNull()) userid_ = row["userid"].as<int64_t>();
    if (!row["articleid"].isNull()) articleid_ = row["articleid"].as<int64_t>();
    if (!row["content"].isNull()) content_ = row["content"].as<std::string>();
    if (!row["ipaddr"].isNull()) ipaddr_ = row["ipaddr"].as<std::string>();
    if (!row["replyid"].isNull()) replyid_ = row["replyid"].as<int64_t>();
    if (!row["agreecount"].isNull()) agreecount_ = row["agreecount"].as<int>();
    if (!row["opposecount"].isNull()) opposecount_ = row["opposecount"].as<int>();
    if (!row["hidden"].isNull()) hidden_ = row["hidden"].as<int>();
}

Json::Value Comment::toJson() const
{
    Json::Value ret;
    ret["commentid"] = static_cast<Json::Int64>(commentid_);
    ret["userid"] = static_cast<Json::Int64>(userid_);
    ret["articleid"] = static_cast<Json::Int64>(articleid_);
    ret["content"] = content_;
    ret["ipaddr"] = ipaddr_;
    ret["replyid"] = static_cast<Json::Int64>(replyid_);
    ret["agreecount"] = agreecount_;
    ret["opposecount"] = opposecount_;
    ret["hidden"] = hidden_;
    return ret;
}

} // namespace models
} // namespace woniunote
