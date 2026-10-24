/**
 * @file test_auth_sessions.cc
 * @brief Unit tests for stable JWT session identifiers.
 */

#include "test_framework.h"
#include "core/security.h"
#include "core/auth_redis_config.h"

#include <algorithm>
#include <sstream>
#include <string>

using namespace woniunote;

namespace {
bool isLowerHex(const std::string& value)
{
    return std::all_of(value.begin(), value.end(), [](unsigned char ch) {
        return (ch >= '0' && ch <= '9') || (ch >= 'a' && ch <= 'f');
    });
}
}  // namespace

TEST_CASE(session_ids_are_128_bit_hex_and_unique)
{
    const std::string first = Security::generateSessionId();
    const std::string second = Security::generateSessionId();

    CHECK_EQ(first.size(), static_cast<std::size_t>(32));
    CHECK_EQ(second.size(), static_cast<std::size_t>(32));
    CHECK(isLowerHex(first));
    CHECK(isLowerHex(second));
    CHECK(first != second);
}

TEST_CASE(access_and_refresh_tokens_carry_the_same_session_id)
{
    const std::string sid = Security::generateSessionId();
    const std::string jti = Security::generateJti();
    CHECK(!sid.empty());
    CHECK(!jti.empty());

    const auto access = Security::decodeToken(
        Security::createAccessToken("42", 60, sid));
    const auto refresh = Security::decodeToken(
        Security::createRefreshToken("42", 1, jti, sid));

    CHECK(access.has_value());
    CHECK(refresh.has_value());
    if (access.has_value()) {
        CHECK_EQ(access->type, std::string("access"));
        CHECK_EQ(access->sid, sid);
    }
    if (refresh.has_value()) {
        CHECK_EQ(refresh->type, std::string("refresh"));
        CHECK_EQ(refresh->sid, sid);
        CHECK_EQ(refresh->jti, jti);
    }
}

TEST_CASE(legacy_refresh_tokens_decode_without_session_claims)
{
    const auto legacy = Security::decodeToken(
        Security::createRefreshToken("7", 1));

    CHECK(legacy.has_value());
    if (legacy.has_value()) {
        CHECK_EQ(legacy->type, std::string("refresh"));
        CHECK(legacy->sid.empty());
        CHECK(legacy->jti.empty());
    }
}

TEST_CASE(auth_redis_config_derives_client_without_changing_existing_clients)
{
    Json::Value config(Json::objectValue);
    config["redis_clients"] = Json::Value(Json::arrayValue);

    Json::Value defaultClient(Json::objectValue);
    defaultClient["name"] = "default";
    defaultClient["host"] = "redis.internal";
    defaultClient["port"] = 6380;
    defaultClient["db"] = 4;
    defaultClient["username"] = "service-user";
    defaultClient["passwd"] = "private-passwd-value";
    defaultClient["number_of_connections"] = 7;
    defaultClient["timeout"] = 8.0;
    defaultClient["is_fast"] = true;
    const Json::Value originalDefault = defaultClient;

    Json::Value otherClient(Json::objectValue);
    otherClient["name"] = "metrics";
    otherClient["host"] = "metrics.internal";
    otherClient["password"] = "private-password-value";
    otherClient["connection_number"] = 3;
    const Json::Value originalOther = otherClient;
    config["redis_clients"].append(defaultClient);
    config["redis_clients"].append(otherClient);

    Json::Value expectedAuthClient = originalDefault;
    expectedAuthClient["name"] = kAuthSessionRedisClientName;
    expectedAuthClient["timeout"] = kAuthSessionRedisTimeoutSeconds;
    expectedAuthClient["is_fast"] = false;

    CHECK(addAuthSessionRedisClient(config));
    CHECK(config["redis_clients"].size() == 3);
    CHECK(config["redis_clients"][0] == originalDefault);
    CHECK(config["redis_clients"][1] == originalOther);
    CHECK(config["redis_clients"][2] == expectedAuthClient);
}

TEST_CASE(auth_redis_config_supports_omitted_default_name_and_alias_fields)
{
    Json::Value config(Json::objectValue);
    config["redis_clients"] = Json::Value(Json::arrayValue);
    Json::Value defaultClient(Json::objectValue);
    defaultClient["host"] = "127.0.0.1";
    defaultClient["port"] = 6379;
    defaultClient["password"] = "private-password-alias-value";
    defaultClient["connection_number"] = 2;
    config["redis_clients"].append(defaultClient);

    Json::Value expectedAuthClient = defaultClient;
    expectedAuthClient["name"] = kAuthSessionRedisClientName;
    expectedAuthClient["timeout"] = kAuthSessionRedisTimeoutSeconds;
    expectedAuthClient["is_fast"] = false;

    CHECK(addAuthSessionRedisClient(config));
    CHECK(config["redis_clients"].size() == 2);
    CHECK(config["redis_clients"][0] == defaultClient);
    CHECK(config["redis_clients"][1] == expectedAuthClient);
}

TEST_CASE(auth_redis_config_without_default_leaves_clients_unchanged)
{
    Json::Value config(Json::objectValue);
    config["redis_clients"] = Json::Value(Json::arrayValue);
    Json::Value otherClient(Json::objectValue);
    otherClient["name"] = "metrics";
    config["redis_clients"].append(otherClient);
    const Json::Value originalClients = config["redis_clients"];

    CHECK(!addAuthSessionRedisClient(config));
    CHECK(config["redis_clients"] == originalClients);
}

TEST_CASE(auth_redis_config_rejects_default_and_reserved_name_conflicts)
{
    Json::Value duplicateConfig(Json::objectValue);
    duplicateConfig["redis_clients"] = Json::Value(Json::arrayValue);
    Json::Value defaultClient(Json::objectValue);
    defaultClient["name"] = "default";
    duplicateConfig["redis_clients"].append(defaultClient);
    duplicateConfig["redis_clients"].append(defaultClient);
    bool duplicateRejected = false;
    try {
        addAuthSessionRedisClient(duplicateConfig);
    } catch (const std::invalid_argument& error) {
        duplicateRejected = std::string(error.what()) == "duplicate default Redis client";
    }
    CHECK(duplicateRejected);

    Json::Value reservedConfig(Json::objectValue);
    reservedConfig["redis_clients"] = Json::Value(Json::arrayValue);
    Json::Value reservedClient(Json::objectValue);
    reservedClient["name"] = kAuthSessionRedisClientName;
    reservedClient["passwd"] = "private-conflict-value";
    reservedConfig["redis_clients"].append(reservedClient);
    bool reservedRejected = false;
    try {
        addAuthSessionRedisClient(reservedConfig);
    } catch (const std::invalid_argument& error) {
        reservedRejected = std::string(error.what()) ==
            "reserved Redis client name is configured";
    }
    CHECK(reservedRejected);
}

TEST_CASE(auth_redis_config_parser_accepts_json_comments)
{
    std::istringstream input(R"json({
        // Existing Drogon configs may use comments.
        "redis_clients": [{"host": "127.0.0.1", "port": 6379}]
    })json");
    Json::Value config;

    CHECK(parseDrogonConfig(input, config));
    CHECK(config["redis_clients"].isArray());
    CHECK(addAuthSessionRedisClient(config));
}
