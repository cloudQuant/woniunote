/**
 * @file config.h
 * @brief Application Configuration Module
 * 
 * Provides access to application configuration loaded from config.json.
 */

#ifndef WONIUNOTE_CORE_CONFIG_H
#define WONIUNOTE_CORE_CONFIG_H

#include <string>
#include <vector>
#include <drogon/drogon.h>

namespace woniunote {

/**
 * @class Config
 * @brief Singleton configuration manager
 * 
 * Provides access to custom configuration values from Drogon's config.json.
 */
class Config {
public:
    /**
     * @brief Get singleton instance
     * @return Reference to Config instance
     */
    static Config& instance();

    /**
     * @brief Initialize configuration from Drogon's custom_config
     */
    void init();

    // Getters for configuration values
    std::string getAppName() const { return appName_; }
    std::string getJwtSecret() const { return jwtSecret_; }
    std::string getJwtAlgorithm() const { return jwtAlgorithm_; }
    int getAccessTokenExpireMinutes() const { return accessTokenExpireMinutes_; }
    int getRefreshTokenExpireDays() const { return refreshTokenExpireDays_; }
    const std::vector<std::string>& getCorsOrigins() const { return corsOrigins_; }

    // Upload path
    std::string getUploadPath() const { return uploadPath_; }

    // Database shortcuts
    std::string getDbName() const { return "mysql"; }

private:
    Config() = default;
    Config(const Config&) = delete;
    Config& operator=(const Config&) = delete;

    std::string appName_;
    std::string jwtSecret_;
    std::string jwtAlgorithm_;
    std::string uploadPath_ = "./uploads";
    int accessTokenExpireMinutes_ = 1440;  // 24 hours
    int refreshTokenExpireDays_ = 7;
    std::vector<std::string> corsOrigins_;
};

} // namespace woniunote

#endif // WONIUNOTE_CORE_CONFIG_H
