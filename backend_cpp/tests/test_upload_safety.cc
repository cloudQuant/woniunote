/**
 * @file test_upload_safety.cc
 * @brief Unit tests for upload filename/extension sanitization and the
 *        config placeholder-secret detection (iteration 10 security work).
 */

#include "test_framework.h"
#include "core/upload_safety.h"
#include "core/config.h"

using namespace woniunote;

// ---------------------------------------------------------------------------
// Extension sanitization — path traversal defense (A1)
// ---------------------------------------------------------------------------

TEST_CASE(sanitizeExtension_basic) {
    CHECK_EQ(sanitizeExtension("photo.png"), std::string("png"));
    CHECK_EQ(sanitizeExtension("archive.TAR"), std::string("tar"));
    CHECK_EQ(sanitizeExtension("report.PDF"), std::string("pdf"));
}

TEST_CASE(sanitizeExtension_strips_traversal_and_separators) {
    // The security guarantee: whatever comes out must be purely alphanumeric
    // (no path separators, no dots), so it can never escape the upload dir.
    auto isClean = [](const std::string& s) {
        for (char c : s) {
            if (!std::isalnum(static_cast<unsigned char>(c))) return false;
        }
        return true;
    };
    CHECK(isClean(sanitizeExtension("avatar.jpg/../../etc/passwd")));
    CHECK(isClean(sanitizeExtension("x.pn/g")));
    CHECK(isClean(sanitizeExtension("a.jp\\g")));
    // No separator characters survive.
    CHECK(sanitizeExtension("avatar.jpg/../../etc/passwd").find('/') == std::string::npos);
    CHECK(sanitizeExtension("a.jp\\g").find('\\') == std::string::npos);
}

TEST_CASE(sanitizeExtension_no_extension) {
    CHECK_EQ(sanitizeExtension("noext"), std::string(""));
    CHECK_EQ(sanitizeExtension("trailingdot."), std::string(""));
    CHECK_EQ(sanitizeExtension(""), std::string(""));
}

TEST_CASE(sanitizeExtension_caps_length) {
    // Absurdly long extensions are capped at 10 chars.
    std::string ext = sanitizeExtension("f.aaaaaaaaaaaaaaaaaaaa");
    CHECK(ext.size() <= 10);
}

TEST_CASE(isExtAllowed_respects_allow_list) {
    std::vector<std::string> images = {"jpg", "png", "gif"};
    CHECK(isExtAllowed("png", images));
    CHECK(!isExtAllowed("exe", images));
    CHECK(!isExtAllowed("", images));
}

// ---------------------------------------------------------------------------
// Placeholder secret detection — fail-fast in production (A3)
// ---------------------------------------------------------------------------

TEST_CASE(isPlaceholderSecret_detects_known_placeholders) {
    CHECK(Config::isPlaceholderSecret(""));
    CHECK(Config::isPlaceholderSecret("CHANGE_ME_SET_VIA_WONIUNOTE_JWT_SECRET_ENV"));
    CHECK(Config::isPlaceholderSecret("YOUR_SECURE_JWT_SECRET_CHANGE_IN_PRODUCTION"));
    CHECK(Config::isPlaceholderSecret("default-secret-change-in-production"));
    CHECK(Config::isPlaceholderSecret("jwt-secret-key-change-in-production"));
}

TEST_CASE(isPlaceholderSecret_accepts_real_secret) {
    CHECK(!Config::isPlaceholderSecret("a7f3c9e1b5d84266aa90f1c2e4b6d8f0"));
    CHECK(!Config::isPlaceholderSecret("super-strong-random-value-9912"));
}
