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
     * @throws std::runtime_error in production mode when a placeholder/empty
     *         JWT secret is detected (fail-fast instead of running insecurely)
     */
    void init();

    // Getters for configuration values
    std::string getAppName() const { return appName_; }
    std::string getJwtSecret() const { return jwtSecret_; }
    std::string getJwtAlgorithm() const { return jwtAlgorithm_; }
    int getAccessTokenExpireMinutes() const { return accessTokenExpireMinutes_; }
    int getRefreshTokenExpireDays() const { return refreshTokenExpireDays_; }
    const std::vector<std::string>& getCorsOrigins() const { return corsOrigins_; }

    // Rate limiting
    int getRateLimitPerMinute() const { return rateLimitPerMinute_; }
    bool getRateLimitFailClosed() const { return rateLimitFailClosed_; }

    // Upload path & limits (bytes)
    std::string getUploadPath() const { return uploadPath_; }
    int64_t getMaxImageSize() const { return maxImageSize_; }
    int64_t getMaxFileSize() const { return maxFileSize_; }
    int64_t getMaxAvatarSize() const { return maxAvatarSize_; }
    const std::vector<std::string>& getAllowedImageExts() const { return allowedImageExts_; }
    const std::vector<std::string>& getAllowedFileExts() const { return allowedFileExts_; }

    // Runtime mode
    bool isProduction() const { return isProduction_; }

    // Database shortcuts
    std::string getDbName() const { return "mysql"; }

    /**
     * @brief Check whether a JWT secret is a known placeholder or empty.
     * @param secret value to test
     * @return true when the value must not be used in production
     */
    static bool isPlaceholderSecret(const std::string& secret);

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
    int rateLimitPerMinute_ = 60;
    bool rateLimitFailClosed_ = false;
    bool isProduction_ = false;

    // Upload limits (bytes) with sane defaults; overridable via custom_config.
    int64_t maxImageSize_ = 5 * 1024 * 1024;    // 5MB
    int64_t maxFileSize_ = 50 * 1024 * 1024;    // 50MB
    int64_t maxAvatarSize_ = 2 * 1024 * 1024;   // 2MB
    std::vector<std::string> allowedImageExts_ =
        {"jpg", "jpeg", "png", "gif", "webp", "bmp"};
    std::vector<std::string> allowedFileExts_ =
        {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "md",
         "zip", "rar", "7z"};
};

} // namespace woniunote

#endif // WONIUNOTE_CORE_CONFIG_H
