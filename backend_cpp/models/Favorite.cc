/**
 * @file Favorite.cc
 * @brief Favorite Model Implementation
 */

#include "Favorite.h"
#include "core/logger.h"

namespace woniunote {
namespace models {

Favorite::Favorite(const drogon::orm::Row& row)
{
    if (!row["favoriteid"].isNull()) favoriteid_ = row["favoriteid"].as<int64_t>();
    Logger::debug("[Model] Favorite loaded", {{"favoriteid", std::to_string(favoriteid_)}});
    if (!row["userid"].isNull()) userid_ = row["userid"].as<int64_t>();
    if (!row["articleid"].isNull()) articleid_ = row["articleid"].as<int64_t>();
    if (!row["canceled"].isNull()) canceled_ = row["canceled"].as<int>();
}

Json::Value Favorite::toJson() const
{
    Json::Value ret;
    ret["favoriteid"] = static_cast<Json::Int64>(favoriteid_);
    ret["userid"] = static_cast<Json::Int64>(userid_);
    ret["articleid"] = static_cast<Json::Int64>(articleid_);
    ret["canceled"] = canceled_;
    return ret;
}

} // namespace models
} // namespace woniunote
