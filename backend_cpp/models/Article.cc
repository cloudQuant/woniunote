/**
 * @file Article.cc
 * @brief Article Model Implementation
 */

#include "Article.h"
#include "core/logger.h"

namespace woniunote {
namespace models {

Article::Article(const drogon::orm::Row& row)
{
    if (!row["articleid"].isNull()) articleid_ = row["articleid"].as<int64_t>();
    Logger::debug("[Model] Article loaded", {{"articleid", std::to_string(articleid_)}});
    if (!row["userid"].isNull()) userid_ = row["userid"].as<int64_t>();
    if (!row["type"].isNull()) type_ = row["type"].as<int>();
    if (!row["headline"].isNull()) headline_ = row["headline"].as<std::string>();
    if (!row["content"].isNull()) content_ = row["content"].as<std::string>();
    if (!row["thumbnail"].isNull()) thumbnail_ = row["thumbnail"].as<std::string>();
    if (!row["credit"].isNull()) credit_ = row["credit"].as<int>();
    if (!row["readcount"].isNull()) readcount_ = row["readcount"].as<int>();
    if (!row["replycount"].isNull()) replycount_ = row["replycount"].as<int>();
    if (!row["recommended"].isNull()) recommended_ = row["recommended"].as<int>();
    if (!row["hidden"].isNull()) hidden_ = row["hidden"].as<int>();
    if (!row["drafted"].isNull()) drafted_ = row["drafted"].as<int>();
    if (!row["checked"].isNull()) checked_ = row["checked"].as<int>();
    if (!row["createtime"].isNull()) createtime_ = row["createtime"].as<std::string>();
    if (!row["updatetime"].isNull()) updatetime_ = row["updatetime"].as<std::string>();
    // Join field from users table
    if (!row["nickname"].isNull()) nickname_ = row["nickname"].as<std::string>();
}

// Helper function to generate stable thumbnail filename based on article type
// Returns just the filename (e.g., "906.png"), NOT the full path
// Frontend will prepend "/api/thumb/" prefix
static std::string getStableThumbnail(const std::string& thumbnail, int type)
{
    // If thumbnail is already set and valid (just filename), use it
    if (!thumbnail.empty() && thumbnail.find(".png") != std::string::npos) {
        // If it's a full path starting with /api/thumb/, extract just the filename
        size_t pos = thumbnail.rfind('/');
        if (pos != std::string::npos) {
            return thumbnail.substr(pos + 1);
        }
        return thumbnail;
    }
    // Generate thumbnail filename based on article type (e.g., "906.png")
    return std::to_string(type) + ".png";
}

Json::Value Article::toJson() const
{
    Logger::debug("[Model] Article toJson", {{"articleid", std::to_string(articleid_)}, {"headline", headline_}});
    Json::Value ret;
    ret["articleid"] = static_cast<Json::Int64>(articleid_);
    ret["userid"] = static_cast<Json::Int64>(userid_);
    ret["type"] = type_;
    ret["headline"] = headline_;
    ret["content"] = content_;
    ret["thumbnail"] = getStableThumbnail(thumbnail_, type_);
    ret["credit"] = credit_;
    ret["readcount"] = readcount_;
    ret["replycount"] = replycount_;
    ret["recommended"] = recommended_;
    ret["hidden"] = hidden_;
    ret["drafted"] = drafted_;
    ret["checked"] = checked_;
    ret["createtime"] = createtime_;
    ret["updatetime"] = updatetime_;
    // Wrap author info in author object for frontend compatibility
    Json::Value author;
    author["nickname"] = nickname_;
    author["userid"] = static_cast<Json::Int64>(userid_);
    ret["author"] = author;
    return ret;
}

Json::Value Article::toJsonBrief() const
{
    Json::Value ret;
    ret["articleid"] = static_cast<Json::Int64>(articleid_);
    ret["userid"] = static_cast<Json::Int64>(userid_);
    ret["type"] = type_;
    ret["headline"] = headline_;
    ret["thumbnail"] = getStableThumbnail(thumbnail_, type_);
    ret["credit"] = credit_;
    ret["readcount"] = readcount_;
    ret["replycount"] = replycount_;
    ret["recommended"] = recommended_;
    ret["createtime"] = createtime_;
    ret["content"] = content_;  // For excerpt generation
    // Wrap author info in author object for frontend compatibility
    Json::Value author;
    author["nickname"] = nickname_;
    author["userid"] = static_cast<Json::Int64>(userid_);
    ret["author"] = author;
    return ret;
}

} // namespace models
} // namespace woniunote
