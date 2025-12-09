/**
 * @file Todo.cc
 * @brief Todo Models Implementation
 */

#include "Todo.h"

namespace woniunote {
namespace models {

TodoCategory::TodoCategory(const drogon::orm::Row& row)
{
    if (!row["id"].isNull()) id_ = row["id"].as<int64_t>();
    if (!row["userid"].isNull()) userid_ = row["userid"].as<int64_t>();
    if (!row["name"].isNull()) name_ = row["name"].as<std::string>();
    if (!row["sort_order"].isNull()) sortOrder_ = row["sort_order"].as<int>();
}

Json::Value TodoCategory::toJson() const
{
    Json::Value ret;
    ret["id"] = static_cast<Json::Int64>(id_);
    ret["userid"] = static_cast<Json::Int64>(userid_);
    ret["name"] = name_;
    ret["sort_order"] = sortOrder_;
    return ret;
}

TodoItem::TodoItem(const drogon::orm::Row& row)
{
    if (!row["id"].isNull()) id_ = row["id"].as<int64_t>();
    if (!row["userid"].isNull()) userid_ = row["userid"].as<int64_t>();
    if (!row["category_id"].isNull()) categoryId_ = row["category_id"].as<int64_t>();
    if (!row["body"].isNull()) body_ = row["body"].as<std::string>();
    if (!row["done"].isNull()) done_ = row["done"].as<int>();
    if (!row["priority"].isNull()) priority_ = row["priority"].as<int>();
}

Json::Value TodoItem::toJson() const
{
    Json::Value ret;
    ret["id"] = static_cast<Json::Int64>(id_);
    ret["userid"] = static_cast<Json::Int64>(userid_);
    ret["category_id"] = static_cast<Json::Int64>(categoryId_);
    ret["body"] = body_;
    ret["done"] = done_;
    ret["priority"] = priority_;
    return ret;
}

} // namespace models
} // namespace woniunote
