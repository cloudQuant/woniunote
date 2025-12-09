/**
 * @file Credit.cc
 * @brief Credit Model Implementation
 */

#include "Credit.h"

namespace woniunote {
namespace models {

Credit::Credit(const drogon::orm::Row& row)
{
    if (!row["creditid"].isNull()) creditid_ = row["creditid"].as<int64_t>();
    if (!row["userid"].isNull()) userid_ = row["userid"].as<int64_t>();
    if (!row["category"].isNull()) category_ = row["category"].as<std::string>();
    if (!row["target"].isNull()) target_ = row["target"].as<int64_t>();
    if (!row["credit"].isNull()) credit_ = row["credit"].as<int>();
}

Json::Value Credit::toJson() const
{
    Json::Value ret;
    ret["creditid"] = static_cast<Json::Int64>(creditid_);
    ret["userid"] = static_cast<Json::Int64>(userid_);
    ret["category"] = category_;
    ret["target"] = static_cast<Json::Int64>(target_);
    ret["credit"] = credit_;
    return ret;
}

} // namespace models
} // namespace woniunote
