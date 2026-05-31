/**
 * @file config.cc
 * @brief Application Configuration Implementation
 */

#include "config.h"
#include "logger.h"
#include <drogon/drogon.h>
#include <cstdlib>
#include <algorithm>
#include <cctype>

namespace woniunote {

namespace {
// Read an environment variable, returning empty string if unset.
std::string getEnv(const char* name)
{
    const char* value = std::getenv(name);
    return value ? std::string(value) : std::string();
}
}  // namespace

Config& Config::instance()
{
    static Config instance;
    return instance;
}

bool Config::isPlaceholderSecret(const std::string& secret)
{
    return secret.empty() ||
           secret.rfind("CHANGE_ME", 0) == 0 ||
           secret.rfind("YOUR_SECURE", 0) == 0 ||
           secret == "default-secret-change-in-production" ||
           secret == "jwt-secret-key-change-in-production";
}

void Config::init()
{
    const auto& customConfig = drogon::app().getCustomConfig();

    if (customConfig.isMember("app_name")) {
        appName_ = customConfig["app_name"].asString();
    } else {
        appName_ = "WoniuNote";
    }

    // Resolve runtime mode. Precedence: WONIUNOTE_ENV env var > app_mode config.
    // Anything starting with "prod" (case-insensitive) is treated as production.
    std::string mode = getEnv("WONIUNOTE_ENV");
    if (mode.empty() && customConfig.isMember("app_mode")) {
        mode = customConfig["app_mode"].asString();
    }
    std::string modeLower = mode;
    std::transform(modeLower.begin(), modeLower.end(), modeLower.begin(),
                   [](unsigned char c) { return std::tolower(c); });
    isProduction_ = (modeLower.rfind("prod", 0) == 0);

    // JWT secret precedence: WONIUNOTE_JWT_SECRET env var > config file.
    // Never run with the well-known placeholder/default value.
    std::string envSecret = getEnv("WONIUNOTE_JWT_SECRET");
    if (!envSecret.empty()) {
        jwtSecret_ = envSecret;
        Logger::info("[Config] JWT secret loaded from environment");
    } else if (customConfig.isMember("jwt_secret")) {
        jwtSecret_ = customConfig["jwt_secret"].asString();
    } else {
        jwtSecret_ = "";
    }

    if (isPlaceholderSecret(jwtSecret_)) {
        if (isProduction_) {
            // Fail fast: refuse to start in production with an insecure secret.
            Logger::error("[Config] Refusing to start in production with a "
                          "placeholder/empty JWT secret. Set WONIUNOTE_JWT_SECRET "
                          "to a strong random value.");
            throw std::runtime_error(
                "Insecure JWT secret in production: set WONIUNOTE_JWT_SECRET");
        }
        Logger::warning("[Config] Insecure or placeholder JWT secret detected. "
                        "Set WONIUNOTE_JWT_SECRET to a strong random value.");
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

    if (customConfig.isMember("rate_limit_per_minute")) {
        rateLimitPerMinute_ = customConfig["rate_limit_per_minute"].asInt();
    }
    if (customConfig.isMember("rate_limit_fail_closed")) {
        rateLimitFailClosed_ = customConfig["rate_limit_fail_closed"].asBool();
    }

    // Upload path mirrors Drogon's app.upload_path so saved files and the
    // static document_root stay consistent.
    if (drogon::app().getUploadPath().size() > 0) {
        uploadPath_ = drogon::app().getUploadPath();
    }

    // Upload limits & allow-lists (optional overrides).
    if (customConfig.isMember("max_image_size")) {
        maxImageSize_ = customConfig["max_image_size"].asInt64();
    }
    if (customConfig.isMember("max_file_size")) {
        maxFileSize_ = customConfig["max_file_size"].asInt64();
    }
    if (customConfig.isMember("max_avatar_size")) {
        maxAvatarSize_ = customConfig["max_avatar_size"].asInt64();
    }
    auto readExtList = [&customConfig](const char* key,
                                       std::vector<std::string>& out) {
        if (customConfig.isMember(key) && customConfig[key].isArray()) {
            out.clear();
            for (const auto& ext : customConfig[key]) {
                std::string e = ext.asString();
                std::transform(e.begin(), e.end(), e.begin(),
                               [](unsigned char c) { return std::tolower(c); });
                out.push_back(e);
            }
        }
    };
    readExtList("allowed_image_exts", allowedImageExts_);
    readExtList("allowed_file_exts", allowedFileExts_);
}

} // namespace woniunote
