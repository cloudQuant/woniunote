/**
 * @file test_security.cc
 * @brief Unit tests for woniunote::Security (password hashing + JWT).
 *
 * These tests exercise pure logic and require no database connection.
 */

#include "test_framework.h"
#include "core/security.h"

using namespace woniunote;

// ---------------------------------------------------------------------------
// Password hashing
// ---------------------------------------------------------------------------

TEST_CASE(hashPassword_roundtrip_succeeds) {
    const std::string password = "S3cret!Pass";
    std::string hash = Security::hashPassword(password);

    CHECK(!hash.empty());
    // Same-platform verification must succeed.
    CHECK(Security::verifyPassword(password, hash));
}

TEST_CASE(verifyPassword_rejects_wrong_password) {
    std::string hash = Security::hashPassword("correct-horse");
    CHECK(!Security::verifyPassword("wrong-password", hash));
}

TEST_CASE(verifyPassword_rejects_empty_and_garbage_hash) {
    CHECK(!Security::verifyPassword("anything", ""));
    CHECK(!Security::verifyPassword("anything", "not-a-real-hash"));
}

TEST_CASE(hashPassword_uses_recognized_scheme) {
    // On non-Linux the portable scheme is PBKDF2; on Linux it is bcrypt ($2).
    // Either way the produced hash must verify and reject wrong passwords.
    std::string hash = Security::hashPassword("portable-pw");
    bool looksKnown = (hash.rfind("$pbkdf2-sha256$", 0) == 0) ||
                      (hash.rfind("$2", 0) == 0);
    CHECK(looksKnown);
    CHECK(Security::verifyPassword("portable-pw", hash));
    CHECK(!Security::verifyPassword("portable-pw-wrong", hash));
}

// ---------------------------------------------------------------------------
// MD5 legacy compatibility
// ---------------------------------------------------------------------------

TEST_CASE(md5_detection_and_value) {
    // Known MD5 of "123456".
    const std::string md5_123456 = "e10adc3949ba59abbe56e057f20f883e";
    CHECK(Security::isMd5Password(md5_123456));
    CHECK_EQ(Security::getMd5Hash("123456"), md5_123456);
    // Legacy MD5 hashes must still verify through verifyPassword.
    CHECK(Security::verifyPassword("123456", md5_123456));
}

TEST_CASE(md5_detection_rejects_non_md5) {
    CHECK(!Security::isMd5Password("short"));
    CHECK(!Security::isMd5Password("zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz")); // 32 non-hex
    CHECK(!Security::isMd5Password("e10adc3949ba59abbe56e057f20f883")); // 31 chars
}

// ---------------------------------------------------------------------------
// JWT tokens (signing + verification use the same configured secret)
// ---------------------------------------------------------------------------

TEST_CASE(jwt_access_token_roundtrip) {
    std::string token = Security::createAccessToken("42", 60);
    CHECK(!token.empty());

    auto payload = Security::decodeToken(token);
    CHECK(payload.has_value());
    if (payload.has_value()) {
        CHECK_EQ(payload->sub, std::string("42"));
        CHECK_EQ(payload->type, std::string("access"));
    }
}

TEST_CASE(jwt_refresh_token_has_refresh_type) {
    std::string token = Security::createRefreshToken("7", 1);
    auto payload = Security::decodeToken(token);
    CHECK(payload.has_value());
    if (payload.has_value()) {
        CHECK_EQ(payload->sub, std::string("7"));
        CHECK_EQ(payload->type, std::string("refresh"));
    }
}

TEST_CASE(jwt_rejects_tampered_token) {
    std::string token = Security::createAccessToken("99", 60);
    // Corrupt the token signature.
    token.back() = (token.back() == 'a') ? 'b' : 'a';
    auto payload = Security::decodeToken(token);
    CHECK(!payload.has_value());
}

TEST_CASE(jwt_rejects_garbage) {
    CHECK(!Security::decodeToken("").has_value());
    CHECK(!Security::decodeToken("not.a.jwt").has_value());
}

// ---------------------------------------------------------------------------
// Refresh token rotation: jti generation + embedding (iteration 13)
// ---------------------------------------------------------------------------

TEST_CASE(generateJti_is_nonempty_and_unique) {
    std::string a = Security::generateJti();
    std::string b = Security::generateJti();
    CHECK(!a.empty());
    CHECK(!b.empty());
    // 128-bit random ids must (practically) never collide.
    CHECK(a != b);
}

TEST_CASE(refresh_token_carries_jti_when_provided) {
    std::string jti = Security::generateJti();
    std::string token = Security::createRefreshToken("7", 1, jti);
    auto payload = Security::decodeToken(token);
    CHECK(payload.has_value());
    if (payload.has_value()) {
        CHECK_EQ(payload->type, std::string("refresh"));
        CHECK_EQ(payload->jti, jti);
    }
}

TEST_CASE(refresh_token_without_jti_has_empty_jti) {
    // Legacy/back-compat path: no jti supplied -> claim absent -> empty string.
    std::string token = Security::createRefreshToken("7", 1);
    auto payload = Security::decodeToken(token);
    CHECK(payload.has_value());
    if (payload.has_value()) {
        CHECK(payload->jti.empty());
    }
}

TEST_CASE(access_token_has_no_jti) {
    std::string token = Security::createAccessToken("42", 60);
    auto payload = Security::decodeToken(token);
    CHECK(payload.has_value());
    if (payload.has_value()) {
        CHECK(payload->jti.empty());
    }
}
