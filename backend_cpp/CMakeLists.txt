cmake_minimum_required(VERSION 3.16)
# Release version — single source of truth for the backend's version strings.
# main.cc / SystemController.cc use the WONIUNOTE_VERSION macro; the release
# check (scripts/check_release_version.sh) verifies this matches
# frontend/package.json and backend_cpp/vcpkg.json.
project(woniunote_backend VERSION 2.0.0 LANGUAGES CXX)
add_compile_definitions(WONIUNOTE_VERSION="${PROJECT_VERSION}")

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 选项: 使用系统库而不是 vcpkg
option(USE_SYSTEM_LIBS "使用系统安装的库而不是 vcpkg" OFF)

# 选项: 启用 AddressSanitizer + UBSan（仅用于本地/CI 测试构建）
option(ENABLE_SANITIZERS "Enable Address/UB sanitizers for test builds" OFF)

# 选项: 启用代码覆盖率插桩（GCC/Clang 通用的 --coverage）
# 用法见 scripts/coverage.sh；默认关闭，不影响常规构建。
option(ENABLE_COVERAGE "Enable code coverage instrumentation (gcov/lcov)" OFF)

# 编译告警门禁: 在非 MSVC 上开启常用告警，暴露潜在质量问题
if(NOT MSVC)
    add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Sanitizer 配置（GCC/Clang）
if(ENABLE_SANITIZERS AND NOT MSVC)
    message(STATUS "Sanitizers enabled: address, undefined")
    add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer -g)
    add_link_options(-fsanitize=address,undefined)
endif()

# 覆盖率配置（GCC/Clang 通用；macOS 的 Apple clang 同样支持 --coverage）
# -O0 -g 保证行号信息准确，避免优化导致的分支/行合并。
if(ENABLE_COVERAGE)
    if(MSVC)
        message(WARNING "ENABLE_COVERAGE is not supported with MSVC; ignoring")
    else()
        message(STATUS "Coverage enabled: --coverage -O0 -g")
        add_compile_options(--coverage -O0 -g)
        add_link_options(--coverage)
    endif()
endif()

# MSVC specific: Use UTF-8 for source and execution charset
if(MSVC)
    add_compile_options(/utf-8)
    add_compile_definitions(NOMINMAX WIN32_LEAN_AND_MEAN)
endif()

# bcrypt (core/security.cc) uses crypt_r() on Linux, which lives in libcrypt
# (libxcrypt). macOS has no separate libcrypt (crypt_r comes from libSystem and
# the code uses its PBKDF2 fallback), so the library is linked only when found.
find_library(CRYPT_LIBRARY crypt)

# Find Drogon package
if(USE_SYSTEM_LIBS)
    # 系统库模式: 使用 CMake find_package 查找 Drogon
    find_package(Drogon CONFIG REQUIRED)
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(JSONCPP REQUIRED jsoncpp)
    
    # OpenSSL
    find_package(OpenSSL REQUIRED)
    
    # spdlog 和 fmt
    find_package(spdlog REQUIRED)
    find_package(fmt REQUIRED)
    
    # jwt-cpp header-only
    find_path(JWT_CPP_INCLUDE_DIRS "jwt-cpp/jwt.h"
        PATHS /usr/local/include /usr/include
    )
else()
    # vcpkg 模式
    find_package(Drogon CONFIG REQUIRED)
    find_package(OpenSSL REQUIRED)
    find_package(jsoncpp CONFIG REQUIRED)
    find_package(spdlog CONFIG REQUIRED)
    find_path(JWT_CPP_INCLUDE_DIRS "jwt-cpp/jwt.h")
endif()

# Source files
set(CORE_SOURCES
    core/config.cc
    core/database.cc
    core/security.cc
    core/logger.cc
)

set(MODEL_SOURCES
    models/User.cc
    models/Article.cc
    models/Comment.cc
    models/Favorite.cc
    models/Credit.cc
    models/CommentVote.cc
    models/MathTraining.cc
    models/ArticleCategory.cc
)

set(CONTROLLER_SOURCES
    controllers/AuthController.cc
    controllers/ArticleController.cc
    controllers/CommentController.cc
    controllers/FavoriteController.cc
    controllers/UserController.cc
    controllers/CreditController.cc
    controllers/SystemController.cc
    controllers/UploadController.cc
    controllers/CaptchaController.cc
    controllers/AdminController.cc
    controllers/ThumbController.cc
    controllers/MathTrainingController.cc
    controllers/UEditorController.cc
)

set(SERVICE_SOURCES
    services/ArticleCategoryService.cc
    services/ArticleAuthorService.cc
)

set(FILTER_SOURCES
    filters/AuthFilter.cc
    filters/RateLimitFilter.cc
    filters/AdminFilter.cc
)

# Main executable
add_executable(${PROJECT_NAME}
    main.cc
    ${CORE_SOURCES}
    ${MODEL_SOURCES}
    ${CONTROLLER_SOURCES}
    ${SERVICE_SOURCES}
    ${FILTER_SOURCES}
)

# Link libraries
if(USE_SYSTEM_LIBS)
    # 系统库模式
    target_include_directories(${PROJECT_NAME} PRIVATE
        ${JSONCPP_INCLUDE_DIRS}
    )
    target_link_libraries(${PROJECT_NAME} PRIVATE
        Drogon::Drogon
        ${JSONCPP_LIBRARIES}
        OpenSSL::SSL
        OpenSSL::Crypto
        spdlog::spdlog
        fmt::fmt
        crypt
        pthread
        dl
    )
else()
    # vcpkg 模式
    target_link_libraries(${PROJECT_NAME} PRIVATE
        Drogon::Drogon
        OpenSSL::SSL
        OpenSSL::Crypto
        JsonCpp::JsonCpp
        spdlog::spdlog_header_only
    )
    # Linux: bcrypt needs crypt_r() from libcrypt (see find_library above).
    if(CRYPT_LIBRARY)
        target_link_libraries(${PROJECT_NAME} PRIVATE ${CRYPT_LIBRARY})
    endif()
endif()

# Include directories
target_include_directories(${PROJECT_NAME} PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/core
    ${CMAKE_CURRENT_SOURCE_DIR}/controllers
    ${CMAKE_CURRENT_SOURCE_DIR}/filters
    ${CMAKE_CURRENT_SOURCE_DIR}/models
    ${CMAKE_CURRENT_SOURCE_DIR}/third_party
    ${JWT_CPP_INCLUDE_DIRS}
)

# Copy config.json to build directory
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/config.json
    ${CMAKE_CURRENT_BINARY_DIR}/config.json COPYONLY)

# Copy local config override (git-ignored, holds real local credentials) when
# present, so it survives reconfigures and the binary can prefer it.
if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/config.local.json)
    configure_file(${CMAKE_CURRENT_SOURCE_DIR}/config.local.json
        ${CMAKE_CURRENT_BINARY_DIR}/config.local.json COPYONLY)
endif()

# Testing (optional)
option(BUILD_TESTING "Build tests" OFF)
if(BUILD_TESTING)
    enable_testing()
    add_subdirectory(tests)
endif()

# Installation
install(TARGETS ${PROJECT_NAME} DESTINATION bin)
install(FILES config.json DESTINATION etc/woniunote)
