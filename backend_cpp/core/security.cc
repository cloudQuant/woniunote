/**
 * @file security.cc
 * @brief Security Utilities Implementation
 * 
 * @note This is a reference implementation.
 *       You need to install jwt-cpp and a bcrypt library:
 *       - vcpkg install jwt-cpp
 *       - For bcrypt, use OpenSSL or a dedicated library
 */

#include "security.h"
#include "config.h"
#include "logger.h"
#include <openssl/md5.h>
#include <openssl/rand.h>
#include <openssl/evp.h>
#include <sstream>
#include <iomanip>
#include <cstring>

// Uncomment when jwt-cpp is installed:
// #include <jwt-cpp/jwt.h>

namespace woniunote {

std::string Security::hashPassword(const std::string& password)
{
    // TODO: Implement proper bcrypt hashing
    // For now, use a placeholder that should be replaced with actual bcrypt
    // 
    // With bcrypt library:
    // return BCrypt::generateHash(password, BCRYPT_WORK_FACTOR);
    
    // Temporary: Use MD5 (NOT SECURE - replace with bcrypt!)
    Logger::warning("Using MD5 for password hashing - replace with bcrypt in production!");
    return getMd5Hash(password);
}

bool Security::verifyPassword(const std::string& password, const std::string& hash)
{
    // Check for MD5 format (32 hex chars)
    if (isMd5Password(hash)) {
        return getMd5Hash(password) == hash;
    }

    // TODO: Implement bcrypt verification
    // With bcrypt library:
    // return BCrypt::validatePassword(password, hash);
    
    Logger::warning("Password verification fallback - implement bcrypt!");
    return false;
}

bool Security::isMd5Password(const std::string& hash)
{
    if (hash.length() != 32) {
        return false;
    }
    for (char c : hash) {
        if (!std::isxdigit(c)) {
            return false;
        }
    }
    return true;
}

std::string Security::getMd5Hash(const std::string& password)
{
    unsigned char digest[MD5_DIGEST_LENGTH];
    
    EVP_MD_CTX* ctx = EVP_MD_CTX_new();
    EVP_DigestInit_ex(ctx, EVP_md5(), nullptr);
    EVP_DigestUpdate(ctx, password.c_str(), password.length());
    EVP_DigestFinal_ex(ctx, digest, nullptr);
    EVP_MD_CTX_free(ctx);
    
    std::ostringstream oss;
    for (int i = 0; i < MD5_DIGEST_LENGTH; ++i) {
        oss << std::hex << std::setw(2) << std::setfill('0') << (int)digest[i];
    }
    return oss.str();
}

std::string Security::createAccessToken(const std::string& userId, int expireMinutes)
{
    auto& config = Config::instance();
    
    if (expireMinutes == 0) {
        expireMinutes = config.getAccessTokenExpireMinutes();
    }

    // TODO: Implement with jwt-cpp
    // 
    // auto token = jwt::create()
    //     .set_issuer("woniunote")
    //     .set_type("JWT")
    //     .set_payload_claim("sub", jwt::claim(userId))
    //     .set_payload_claim("type", jwt::claim(std::string("access")))
    //     .set_issued_at(std::chrono::system_clock::now())
    //     .set_expires_at(std::chrono::system_clock::now() + 
    //                     std::chrono::minutes(expireMinutes))
    //     .sign(jwt::algorithm::hs256{config.getJwtSecret()});
    // return token;

    Logger::warning("JWT creation not implemented - install jwt-cpp");
    return "placeholder-access-token-" + userId;
}

std::string Security::createRefreshToken(const std::string& userId, int expireDays)
{
    auto& config = Config::instance();
    
    if (expireDays == 0) {
        expireDays = config.getRefreshTokenExpireDays();
    }

    // TODO: Implement with jwt-cpp (similar to createAccessToken)
    Logger::warning("JWT creation not implemented - install jwt-cpp");
    return "placeholder-refresh-token-" + userId;
}

std::optional<TokenPayload> Security::decodeToken(const std::string& token)
{
    auto& config = Config::instance();

    // TODO: Implement with jwt-cpp
    //
    // try {
    //     auto decoded = jwt::decode(token);
    //     auto verifier = jwt::verify()
    //         .allow_algorithm(jwt::algorithm::hs256{config.getJwtSecret()})
    //         .with_issuer("woniunote");
    //     verifier.verify(decoded);
    //
    //     TokenPayload payload;
    //     payload.sub = decoded.get_payload_claim("sub").as_string();
    //     payload.type = decoded.get_payload_claim("type").as_string();
    //     payload.exp = decoded.get_expires_at();
    //     return payload;
    // } catch (const std::exception& e) {
    //     Logger::debug("Token decode failed: " + std::string(e.what()));
    //     return std::nullopt;
    // }

    Logger::warning("JWT decoding not implemented - install jwt-cpp");
    
    // Placeholder: extract user ID from token format
    if (token.find("placeholder-access-token-") == 0) {
        TokenPayload payload;
        payload.sub = token.substr(25);
        payload.type = "access";
        payload.exp = std::chrono::system_clock::now() + std::chrono::hours(24);
        return payload;
    }
    
    return std::nullopt;
}

} // namespace woniunote
