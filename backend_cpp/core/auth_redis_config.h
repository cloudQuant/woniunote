#pragma once

#include <json/json.h>

#include <istream>
#include <stdexcept>
#include <string>
#include <utility>

namespace woniunote {

inline constexpr char kAuthSessionRedisClientName[] = "woniunote_auth_sessions";
inline constexpr double kAuthSessionRedisTimeoutSeconds = 1.5;

// Parse the same JSON-with-comments format accepted by Drogon's config files.
// Parser diagnostics are intentionally not returned because they can include
// configuration text such as credentials.
inline bool parseDrogonConfig(std::istream& input, Json::Value& config)
{
    Json::CharReaderBuilder builder;
    builder["allowComments"] = true;
    std::string ignoredDiagnostics;
    return Json::parseFromStream(builder, input, &config, &ignoredDiagnostics);
}

// Add a framework-managed authentication pool derived from the default Redis
// client. The original default entry and all unrelated clients remain intact.
// Returns false when no default client is configured; callers can keep serving
// unrelated routes and fail authentication requests closed at runtime.
inline bool addAuthSessionRedisClient(Json::Value& config)
{
    if (!config.isObject()) {
        throw std::invalid_argument("invalid Redis client configuration");
    }
    if (!config.isMember("redis_clients")) {
        return false;
    }

    Json::Value& clients = config["redis_clients"];
    if (!clients.isArray()) {
        throw std::invalid_argument("invalid Redis client configuration");
    }

    Json::Value defaultClient;
    bool foundDefault = false;
    for (const auto& client : clients) {
        if (!client.isObject()) {
            throw std::invalid_argument("invalid Redis client configuration");
        }

        if (client.isMember("name") && !client["name"].isString()) {
            throw std::invalid_argument("invalid Redis client configuration");
        }
        const std::string name = client.isMember("name")
            ? client["name"].asString()
            : "default";
        if (name == kAuthSessionRedisClientName) {
            throw std::invalid_argument("reserved Redis client name is configured");
        }
        if (name == "default") {
            if (foundDefault) {
                throw std::invalid_argument("duplicate default Redis client");
            }
            defaultClient = client;
            foundDefault = true;
        }
    }

    if (!foundDefault) {
        return false;
    }

    defaultClient["name"] = kAuthSessionRedisClientName;
    defaultClient["timeout"] = kAuthSessionRedisTimeoutSeconds;
    defaultClient["is_fast"] = false;
    clients.append(std::move(defaultClient));
    return true;
}

}  // namespace woniunote
