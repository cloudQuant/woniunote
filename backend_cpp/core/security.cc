/**
 * @file security.cc
 * @brief Security Utilities Implementation
 * 
 * Provides password hashing (bcrypt) and JWT token management.
 * 
 * Required dependencies (install via vcpkg):
 *   vcpkg install jwt-cpp openssl
 */

#include "security.h"
#include "config.h"
#include "logger.h"

// OpenSSL for MD5 (legacy compatibility)
#include <openssl/md5.h>
#include <openssl/rand.h>
#include <openssl/evp.h>
#include <openssl/sha.h>

// System crypt for bcrypt support
#include <crypt.h>

// jwt-cpp header
#include <jwt-cpp/jwt.h>

#include <sstream>
#include <iomanip>
#include <cstring>
#include <random>
#include <algorithm>

namespace woniunote {

// ============================================================================
// BCrypt Implementation using OpenSSL
// ============================================================================

namespace {

// Base64 encoding table for bcrypt (custom alphabet)
static const char BCRYPT_BASE64[] = 
    "./ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

std::string generateSalt(int workFactor) {
    // Generate 16 random bytes
    unsigned char rawSalt[16];
    RAND_bytes(rawSalt, 16);
    
    // Encode to bcrypt base64 (22 chars)
    std::string encoded;
    encoded.reserve(22);
    
    for (int i = 0; i < 16; i += 3) {
        unsigned int val = rawSalt[i] << 16;
        if (i + 1 < 16) val |= rawSalt[i + 1] << 8;
        if (i + 2 < 16) val |= rawSalt[i + 2];
        
        encoded += BCRYPT_BASE64[(val >> 18) & 0x3f];
        encoded += BCRYPT_BASE64[(val >> 12) & 0x3f];
        if (i + 1 < 16) encoded += BCRYPT_BASE64[(val >> 6) & 0x3f];
        if (i + 2 < 16) encoded += BCRYPT_BASE64[val & 0x3f];
    }
    
    // Format: $2b$<work>$<22-char-salt>
    std::ostringstream oss;
    oss << "$2b$" << std::setw(2) << std::setfill('0') << workFactor << "$" << encoded;
    return oss.str();
}

// Use system crypt() for bcrypt - it properly supports $2b$ format
std::string bcryptHash(const std::string& password, const std::string& salt) {
    // Use crypt_r for thread safety
    struct crypt_data data;
    memset(&data, 0, sizeof(data));
    
    char* result = crypt_r(password.c_str(), salt.c_str(), &data);
    if (result == nullptr) {
        return "";
    }
    return std::string(result);
}

bool bcryptVerify(const std::string& password, const std::string& hash) {
    if (hash.length() < 60) {
        return false;
    }
    
    // Verify using system crypt which supports bcrypt ($2a$, $2b$, $2y$)
    struct crypt_data data;
    memset(&data, 0, sizeof(data));
    
    char* result = crypt_r(password.c_str(), hash.c_str(), &data);
    if (result == nullptr) {
        return false;
    }
    
    // Constant-time comparison to prevent timing attacks
    if (strlen(result) != hash.length()) {
        return false;
    }
    
    int diff = 0;
    for (size_t i = 0; i < hash.length(); ++i) {
        diff |= result[i] ^ hash[i];
    }
    return diff == 0;
}

} // anonymous namespace

// ============================================================================
// Security Class Implementation
// ============================================================================

std::string Security::hashPassword(const std::string& password)
{
    std::string salt = generateSalt(BCRYPT_WORK_FACTOR);
    return bcryptHash(password, salt);
}

bool Security::verifyPassword(const std::string& password, const std::string& hash)
{
    Logger::debug("[Security] verifyPassword called", {
        {"hash_length", std::to_string(hash.length())},
        {"hash_prefix", hash.length() >= 4 ? hash.substr(0, 4) : hash}
    });
    
    // Check for MD5 format (32 hex chars) - legacy compatibility
    if (isMd5Password(hash)) {
        Logger::debug("[Security] Using MD5 verification");
        return getMd5Hash(password) == hash;
    }
    
    // Check for bcrypt format ($2a$, $2b$, $2y$)
    if (hash.length() >= 60 && hash.substr(0, 2) == "$2") {
        Logger::debug("[Security] Using bcrypt verification");
        return bcryptVerify(password, hash);
    }
    
    // Unknown format
    Logger::warning("Unknown password hash format", {
        {"hash_length", std::to_string(hash.length())},
        {"hash_prefix", hash.length() >= 10 ? hash.substr(0, 10) : hash}
    });
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

    auto token = jwt::create()
        .set_issuer("woniunote")
        .set_type("JWT")
        .set_payload_claim("sub", jwt::claim(userId))
        .set_payload_claim("type", jwt::claim(std::string("access")))
        .set_issued_at(std::chrono::system_clock::now())
        .set_expires_at(std::chrono::system_clock::now() + 
                        std::chrono::minutes(expireMinutes))
        .sign(jwt::algorithm::hs256{config.getJwtSecret()});
    
    return token;
}

std::string Security::createRefreshToken(const std::string& userId, int expireDays)
{
    auto& config = Config::instance();
    
    if (expireDays == 0) {
        expireDays = config.getRefreshTokenExpireDays();
    }

    auto token = jwt::create()
        .set_issuer("woniunote")
        .set_type("JWT")
        .set_payload_claim("sub", jwt::claim(userId))
        .set_payload_claim("type", jwt::claim(std::string("refresh")))
        .set_issued_at(std::chrono::system_clock::now())
        .set_expires_at(std::chrono::system_clock::now() + 
                        std::chrono::hours(24 * expireDays))
        .sign(jwt::algorithm::hs256{config.getJwtSecret()});
    
    return token;
}

std::optional<TokenPayload> Security::decodeToken(const std::string& token)
{
    auto& config = Config::instance();

    try {
        auto decoded = jwt::decode(token);
        
        auto verifier = jwt::verify()
            .allow_algorithm(jwt::algorithm::hs256{config.getJwtSecret()})
            .with_issuer("woniunote");
        
        verifier.verify(decoded);

        TokenPayload payload;
        payload.sub = decoded.get_payload_claim("sub").as_string();
        payload.type = decoded.get_payload_claim("type").as_string();
        payload.exp = decoded.get_expires_at();
        
        return payload;
    } catch (const jwt::error::token_verification_exception& e) {
        Logger::debug("Token verification failed: " + std::string(e.what()));
        return std::nullopt;
    } catch (const std::exception& e) {
        Logger::debug("Token decode failed: " + std::string(e.what()));
        return std::nullopt;
    }
}

} // namespace woniunote
