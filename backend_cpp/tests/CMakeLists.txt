# Tests for WoniuNote C++ backend
#
# Lightweight, dependency-free test harness (no gtest required) so it can run
# in any environment that can build the main project. Tests cover pure logic
# (password hashing, JWT round-trips) that do not need a live database.
#
# Build & run:
#   cmake .. -DBUILD_TESTING=ON
#   cmake --build . --target woniunote_tests
#   ctest --output-on-failure   (or run ./tests/woniunote_tests directly)

add_executable(woniunote_tests
    test_main.cc
    test_security.cc
    test_upload_safety.cc
    test_response.cc
    test_article_category.cc
    ${CMAKE_SOURCE_DIR}/core/security.cc
    ${CMAKE_SOURCE_DIR}/core/config.cc
    ${CMAKE_SOURCE_DIR}/core/logger.cc
    ${CMAKE_SOURCE_DIR}/models/ArticleCategory.cc
)

target_include_directories(woniunote_tests PRIVATE
    ${CMAKE_SOURCE_DIR}
    ${CMAKE_SOURCE_DIR}/core
    ${CMAKE_SOURCE_DIR}/third_party
    ${JWT_CPP_INCLUDE_DIRS}
)

if(USE_SYSTEM_LIBS)
    target_link_libraries(woniunote_tests PRIVATE
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
    target_link_libraries(woniunote_tests PRIVATE
        Drogon::Drogon
        OpenSSL::SSL
        OpenSSL::Crypto
        JsonCpp::JsonCpp
        spdlog::spdlog_header_only
    )
endif()

add_test(NAME woniunote_tests COMMAND woniunote_tests)
