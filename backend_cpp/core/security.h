/**
 * @file security.h
 * @brief Security Utilities
 * 
 * Provides password hashing and JWT token management.
 * 
 * @note Requires jwt-cpp and bcrypt libraries.
 *       Install via vcpkg: vcpkg install jwt-cpp
 */

#ifndef WONIUNOTE_CORE_SECURITY_H
#define WONIUNOTE_CORE_SECURITY_H

#include <string>
#include <optional>
#include <map>
#include <chrono>

namespace woniunote {

/**
 * @struct TokenPayload
 * @brief JWT token payload data
 */
struct TokenPayload {
    std::string sub;        // Subject (user ID)
    std::string type;       // Token type ("access" or "refresh")
    std::string jti;        // Unique token id (for refresh rotation / reuse detection)
    std::chrono::system_clock::time_point exp;  // Expiration time
};

/**
 * @class Security
 * @brief Security utility functions
 * 
 * Provides password hashing (bcrypt) and JWT token management.
 */
class Security {
public:
    /**
     * @brief Hash a password using bcrypt
     * @param password Plain text password
     * @return Hashed password string
     */
    static std::string hashPassword(const std::string& password);

    /**
     * @brief Verify password against hash
     * @param password Plain text password
     * @param hash Hashed password
     * @return true if password matches
     */
    static bool verifyPassword(const std::string& password, const std::string& hash);

    /**
     * @brief Check if hash is MD5 format (legacy)
     * @param hash Password hash
     * @return true if MD5 format
     */
    static bool isMd5Password(const std::string& hash);

    /**
     * @brief Get MD5 hash (for legacy compatibility)
     * @param password Plain text password
     * @return MD5 hash string
     */
    static std::string getMd5Hash(const std::string& password);

    /**
     * @brief Create access token
     * @param userId User ID string
     * @param expireMinutes Token expiration in minutes (optional, uses config default)
     * @return JWT token string
     */
    static std::string createAccessToken(const std::string& userId, 
                                          int expireMinutes = 0);

    /**
     * @brief Create refresh token
     * @param userId User ID string
     * @param expireDays Token expiration in days (optional, uses config default)
     * @param jti Unique token id to embed (optional; empty means none)
     * @return JWT token string
     */
    static std::string createRefreshToken(const std::string& userId,
                                           int expireDays = 0,
                                           const std::string& jti = "");

    /**
     * @brief Generate a random unique token id (jti), hex-encoded.
     * @return 32-char hex string (128 bits of entropy)
     */
    static std::string generateJti();

    /**
     * @brief Decode and verify a JWT token
     * @param token JWT token string
     * @return Optional TokenPayload if valid, nullopt if invalid
     */
    static std::optional<TokenPayload> decodeToken(const std::string& token);

private:
    static constexpr int BCRYPT_WORK_FACTOR = 12;
};

} // namespace woniunote

#endif // WONIUNOTE_CORE_SECURITY_H
