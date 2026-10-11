/**
 * @file test_config.cc
 * @brief Unit tests for core/config.h (iteration 16).
 *
 * Config is a singleton whose values come from Drogon's custom_config after
 * Config::init() runs. The four layers exercised here, in order (the later
 * cases mutate the singleton, so ordering matters within this binary):
 *
 *   1. Default contract — before init(), class-level defaults are exposed.
 *   2. init() loading — a fixture config.json is loaded through
 *      drogon::app().loadConfigFile() and every overridden key is applied.
 *   3. Secret precedence — the WONIUNOTE_JWT_SECRET env var beats the file.
 *   4. Production fail-fast — a placeholder secret in production mode must
 *      throw instead of starting insecurely.
 *
 * The fixture path is injected via WONIUNOTE_TEST_CONFIG_FIXTURE (CMake).
 */

#include "test_framework.h"
#include "core/config.h"

#include <cstdlib>
#include <drogon/drogon.h>

using namespace woniunote;

// ---------------------------------------------------------------------------
// 1. Default contract (no drogon config loaded yet in this process)
// ---------------------------------------------------------------------------

TEST_CASE(config_defaults_without_loaded_file) {
    auto& config = Config::instance();
    CHECK_EQ(config.getUploadPath(), std::string("./uploads"));
    CHECK_EQ(config.getAccessTokenExpireMinutes(), 1440);
    CHECK_EQ(config.getRefreshTokenExpireDays(), 7);
    CHECK_EQ(config.getRateLimitPerMinute(), 60);
    CHECK(!config.getRateLimitFailClosed());
    CHECK(!config.isProduction());
    CHECK_EQ(config.getDbName(), std::string("mysql"));
    CHECK_EQ(config.getMaxImageSize(), static_cast<int64_t>(5 * 1024 * 1024));
    CHECK_EQ(config.getMaxFileSize(), static_cast<int64_t>(50 * 1024 * 1024));
    CHECK_EQ(config.getMaxAvatarSize(), static_cast<int64_t>(2 * 1024 * 1024));

    const auto& images = config.getAllowedImageExts();
    bool hasPng = false, hasJpg = false;
    for (const auto& ext : images) {
        if (ext == "png") hasPng = true;
        if (ext == "jpg") hasJpg = true;
    }
    CHECK(hasPng);
    CHECK(hasJpg);

    const auto& files = config.getAllowedFileExts();
    bool hasPdf = false, hasMd = false;
    for (const auto& ext : files) {
        if (ext == "pdf") hasPdf = true;
        if (ext == "md") hasMd = true;
    }
    CHECK(hasPdf);
    CHECK(hasMd);
}

// ---------------------------------------------------------------------------
// 2. init() applies a loaded custom_config
// ---------------------------------------------------------------------------

TEST_CASE(config_init_loads_custom_config) {
    drogon::app().loadConfigFile(WONIUNOTE_TEST_CONFIG_FIXTURE);
    Config::instance().init();

    auto& config = Config::instance();
    CHECK_EQ(config.getAppName(), std::string("WoniuNoteTest"));
    CHECK_EQ(config.getJwtAlgorithm(), std::string("HS512"));
    CHECK_EQ(config.getJwtSecret(), std::string("CHANGE_ME_TEST_PLACEHOLDER_SECRET"));
    CHECK_EQ(config.getAccessTokenExpireMinutes(), 30);
    CHECK_EQ(config.getRefreshTokenExpireDays(), 3);
    CHECK_EQ(config.getRateLimitPerMinute(), 120);
    CHECK(!config.isProduction());

    const auto& origins = config.getCorsOrigins();
    CHECK_EQ(origins.size(), static_cast<size_t>(1));
    if (!origins.empty()) {
        CHECK_EQ(origins[0], std::string("https://unit-test.example.com"));
    }

    // Extension allow-lists are replaced (not merged) when overridden, and
    // are lower-cased on load.
    const auto& images = config.getAllowedImageExts();
    CHECK_EQ(images.size(), static_cast<size_t>(2));
    if (images.size() == 2) {
        CHECK_EQ(images[0], std::string("png"));
        CHECK_EQ(images[1], std::string("svg"));
    }
}

// ---------------------------------------------------------------------------
// 3. Env var secret beats the config file
// ---------------------------------------------------------------------------

TEST_CASE(config_env_secret_overrides_file) {
    ::setenv("WONIUNOTE_JWT_SECRET", "test-env-secret-value-123", 1);
    Config::instance().init();
    CHECK_EQ(Config::instance().getJwtSecret(),
             std::string("test-env-secret-value-123"));
    ::unsetenv("WONIUNOTE_JWT_SECRET");
}

// ---------------------------------------------------------------------------
// 4. Production mode refuses placeholder secrets (fail-fast)
// ---------------------------------------------------------------------------

TEST_CASE(config_production_mode_fails_fast_on_placeholder_secret) {
    // The previous case unset the env secret, so init() falls back to the
    // fixture's placeholder — combined with production mode this must throw.
    ::setenv("WONIUNOTE_ENV", "production", 1);
    bool threw = false;
    try {
        Config::instance().init();
    } catch (const std::runtime_error&) {
        threw = true;
    }
    CHECK(threw);
    ::unsetenv("WONIUNOTE_ENV");
}
