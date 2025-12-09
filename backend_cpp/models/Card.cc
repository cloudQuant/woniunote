/**
 * @file Card.cc
 * @brief Card Models Implementation
 */

#include "Card.h"

namespace woniunote {
namespace models {

CardCategory::CardCategory(const drogon::orm::Row& row)
{
    if (!row["id"].isNull()) id_ = row["id"].as<int64_t>();
    if (!row["userid"].isNull()) userid_ = row["userid"].as<int64_t>();
    if (!row["name"].isNull()) name_ = row["name"].as<std::string>();
    if (!row["type"].isNull()) type_ = row["type"].as<int>();
    if (!row["sort_order"].isNull()) sortOrder_ = row["sort_order"].as<int>();
}

Json::Value CardCategory::toJson() const
{
    Json::Value ret;
    ret["id"] = static_cast<Json::Int64>(id_);
    ret["userid"] = static_cast<Json::Int64>(userid_);
    ret["name"] = name_;
    ret["type"] = type_;
    ret["sort_order"] = sortOrder_;
    return ret;
}

Card::Card(const drogon::orm::Row& row)
{
    if (!row["id"].isNull()) id_ = row["id"].as<int64_t>();
    if (!row["userid"].isNull()) userid_ = row["userid"].as<int64_t>();
    if (!row["category_id"].isNull()) categoryId_ = row["category_id"].as<int64_t>();
    if (!row["headline"].isNull()) headline_ = row["headline"].as<std::string>();
    if (!row["content"].isNull()) content_ = row["content"].as<std::string>();
    if (!row["type"].isNull()) type_ = row["type"].as<int>();
    if (!row["is_repeat"].isNull()) isRepeat_ = row["is_repeat"].as<int>();
    if (!row["usedtime"].isNull()) usedtime_ = row["usedtime"].as<int>();
}

Json::Value Card::toJson() const
{
    Json::Value ret;
    ret["id"] = static_cast<Json::Int64>(id_);
    ret["userid"] = static_cast<Json::Int64>(userid_);
    ret["category_id"] = static_cast<Json::Int64>(categoryId_);
    ret["headline"] = headline_;
    ret["content"] = content_;
    ret["type"] = type_;
    ret["is_repeat"] = isRepeat_;
    ret["usedtime"] = usedtime_;
    return ret;
}

} // namespace models
} // namespace woniunote
