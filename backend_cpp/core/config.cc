/**
 * @file config.cc
 * @brief Application Configuration Implementation
 */

#include "config.h"
#include <drogon/drogon.h>

namespace woniunote {

Config& Config::instance()
{
    static Config instance;
    return instance;
}

void Config::init()
{
    const auto& customConfig = drogon::app().getCustomConfig();

    if (customConfig.isMember("app_name")) {
        appName_ = customConfig["app_name"].asString();
    } else {
        appName_ = "WoniuNote";
    }

    if (customConfig.isMember("jwt_secret")) {
        jwtSecret_ = customConfig["jwt_secret"].asString();
    } else {
        jwtSecret_ = "default-secret-change-in-production";
    }

    if (customConfig.isMember("jwt_algorithm")) {
        jwtAlgorithm_ = customConfig["jwt_algorithm"].asString();
    } else {
        jwtAlgorithm_ = "HS256";
    }

    if (customConfig.isMember("access_token_expire_minutes")) {
        accessTokenExpireMinutes_ = customConfig["access_token_expire_minutes"].asInt();
    }

    if (customConfig.isMember("refresh_token_expire_days")) {
        refreshTokenExpireDays_ = customConfig["refresh_token_expire_days"].asInt();
    }

    if (customConfig.isMember("cors_origins")) {
        const auto& origins = customConfig["cors_origins"];
        for (const auto& origin : origins) {
            corsOrigins_.push_back(origin.asString());
        }
    }
}

} // namespace woniunote
