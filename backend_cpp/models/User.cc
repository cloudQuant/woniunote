/**
 * @file User.cc
 * @brief User Model Implementation
 */

#include "User.h"
#include "core/logger.h"
#include <trantor/utils/Date.h>

namespace woniunote {
namespace models {

User::User(const drogon::orm::Row& row)
{
    if (!row["userid"].isNull()) {
        userid_ = row["userid"].as<int64_t>();
        Logger::debug("[Model] User loaded", {{"userid", std::to_string(userid_)}});
    }
    if (!row["username"].isNull()) {
        username_ = row["username"].as<std::string>();
    }
    if (!row["password"].isNull()) {
        password_ = row["password"].as<std::string>();
    }
    if (!row["nickname"].isNull()) {
        nickname_ = row["nickname"].as<std::string>();
    }
    if (!row["avatar"].isNull()) {
        avatar_ = row["avatar"].as<std::string>();
    }
    if (!row["qq"].isNull()) {
        qq_ = row["qq"].as<std::string>();
    }
    if (!row["role"].isNull()) {
        role_ = row["role"].as<std::string>();
    }
    if (!row["credit"].isNull()) {
        credit_ = row["credit"].as<int>();
    }
    // Note: Time fields are handled by Drogon's date utilities
}

Json::Value User::toJson() const
{
    Json::Value ret;
    ret["userid"] = static_cast<Json::Int64>(userid_);
    ret["username"] = username_;
    ret["password"] = password_;
    ret["nickname"] = nickname_;
    ret["avatar"] = avatar_;
    ret["qq"] = qq_;
    ret["role"] = role_;
    ret["credit"] = credit_;
    return ret;
}

Json::Value User::toJsonWithoutPassword() const
{
    Logger::debug("[Model] User toJson", {{"userid", std::to_string(userid_)}, {"username", username_}});
    Json::Value ret;
    ret["userid"] = static_cast<Json::Int64>(userid_);
    ret["username"] = username_;
    ret["nickname"] = nickname_;
    ret["avatar"] = avatar_;
    ret["qq"] = qq_;
    ret["role"] = role_;
    ret["credit"] = credit_;
    return ret;
}

} // namespace models
} // namespace woniunote
