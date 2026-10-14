# Tests for WoniuNote C++ backend
#
# Lightweight, dependency-free test harness (no gtest required) so it can run
# in any environment that can build the main project. Tests cover pure logic
# (password hashing, JWT round-trips, config invariants, response envelopes)
# that does not need a live database; HTTP-level controller branches are
# covered by tests/integration/run_integration.sh.
#
# One ctest target per module so a failure points at the failing area:
#   cmake .. -DBUILD_TESTING=ON
#   cmake --build . --target test_security test_config ...
#   ctest --output-on-failure

# Core sources shared by the test executables (uniform link set; unused
# objects per module are dropped by the linker).
set(TEST_CORE_SOURCES
    ${CMAKE_SOURCE_DIR}/core/security.cc
    ${CMAKE_SOURCE_DIR}/core/config.cc
    ${CMAKE_SOURCE_DIR}/core/logger.cc
    ${CMAKE_SOURCE_DIR}/models/ArticleCategory.cc
)

set(TEST_MODULES
    test_security
    test_upload_safety
    test_response
    test_article_category
    test_config
    test_services
)

foreach(module IN LISTS TEST_MODULES)
    add_executable(${module}
        test_main.cc
        ${module}.cc
        ${TEST_CORE_SOURCES}
    )

    target_include_directories(${module} PRIVATE
        ${CMAKE_SOURCE_DIR}
        ${CMAKE_SOURCE_DIR}/core
        ${CMAKE_SOURCE_DIR}/third_party
        ${JWT_CPP_INCLUDE_DIRS}
    )

    if(USE_SYSTEM_LIBS)
        target_link_libraries(${module} PRIVATE
            Drogon::Drogon
            OpenSSL::SSL
            OpenSSL::Crypto
            spdlog::spdlog
            fmt::fmt
            crypt
            pthread
            dl
        )
    else()
        target_link_libraries(${module} PRIVATE
            Drogon::Drogon
            OpenSSL::SSL
            OpenSSL::Crypto
            JsonCpp::JsonCpp
            spdlog::spdlog_header_only
        )
        # Linux: bcrypt needs crypt_r() from libcrypt (see top-level CMakeLists).
        if(CRYPT_LIBRARY)
            target_link_libraries(${module} PRIVATE ${CRYPT_LIBRARY})
        endif()
    endif()

    add_test(NAME ${module} COMMAND ${module})
endforeach()

# Fixture config for test_config: loaded via drogon::app().loadConfigFile()
# to exercise Config::init() against a real custom_config section.
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/fixture_config.json [[{
  "custom_config": {
    "app_name": "WoniuNoteTest",
    "app_mode": "development",
    "jwt_secret": "CHANGE_ME_TEST_PLACEHOLDER_SECRET",
    "jwt_algorithm": "HS512",
    "access_token_expire_minutes": 30,
    "refresh_token_expire_days": 3,
    "cors_origins": ["https://unit-test.example.com"],
    "rate_limit_per_minute": 120,
    "allowed_image_exts": ["png", "svg"]
  }
}]])

target_compile_definitions(test_config PRIVATE
    WONIUNOTE_TEST_CONFIG_FIXTURE="${CMAKE_CURRENT_BINARY_DIR}/fixture_config.json"
)
