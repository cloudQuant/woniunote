cmake_minimum_required(VERSION 3.16)
project(woniunote_backend CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 选项: 使用系统库而不是 vcpkg
option(USE_SYSTEM_LIBS "使用系统安装的库而不是 vcpkg" OFF)

# MSVC specific: Use UTF-8 for source and execution charset
if(MSVC)
    add_compile_options(/utf-8)
    add_compile_definitions(NOMINMAX WIN32_LEAN_AND_MEAN)
endif()

# Find Drogon package
if(USE_SYSTEM_LIBS)
    # 系统库模式: 使用 pkg-config 查找 Drogon
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(DROGON REQUIRED drogon)
    pkg_check_modules(TRANTOR REQUIRED trantor)
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
    ${FILTER_SOURCES}
)

# Link libraries
if(USE_SYSTEM_LIBS)
    # 系统库模式
    target_include_directories(${PROJECT_NAME} PRIVATE
        ${DROGON_INCLUDE_DIRS}
        ${TRANTOR_INCLUDE_DIRS}
        ${JSONCPP_INCLUDE_DIRS}
    )
    target_link_libraries(${PROJECT_NAME} PRIVATE
        ${DROGON_LIBRARIES}
        ${TRANTOR_LIBRARIES}
        ${JSONCPP_LIBRARIES}
        OpenSSL::SSL
        OpenSSL::Crypto
        spdlog::spdlog
        fmt::fmt
        pthread
        dl
    )
    target_compile_options(${PROJECT_NAME} PRIVATE
        ${DROGON_CFLAGS_OTHER}
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
endif()

# Include directories
target_include_directories(${PROJECT_NAME} PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/core
    ${CMAKE_CURRENT_SOURCE_DIR}/controllers
    ${CMAKE_CURRENT_SOURCE_DIR}/filters
    ${CMAKE_CURRENT_SOURCE_DIR}/models
    ${JWT_CPP_INCLUDE_DIRS}
)

# Copy config.json to build directory
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/config.json
    ${CMAKE_CURRENT_BINARY_DIR}/config.json COPYONLY)

# Testing (optional)
option(BUILD_TESTING "Build tests" OFF)
if(BUILD_TESTING)
    enable_testing()
    add_subdirectory(tests)
endif()

# Installation
install(TARGETS ${PROJECT_NAME} DESTINATION bin)
install(FILES config.json DESTINATION etc/woniunote)

