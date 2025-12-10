cmake_minimum_required(VERSION 3.20)
project(woniunote_backend CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# MSVC specific: Use UTF-8 for source and execution charset
if(MSVC)
    add_compile_options(/utf-8)
    add_compile_definitions(NOMINMAX WIN32_LEAN_AND_MEAN)
endif()

# Find Drogon package
find_package(Drogon CONFIG REQUIRED)

# Find additional packages
find_package(OpenSSL REQUIRED)
find_package(jsoncpp CONFIG REQUIRED)
find_package(spdlog CONFIG REQUIRED)

# jwt-cpp is header-only, just need include path
# Install via: vcpkg install jwt-cpp
find_path(JWT_CPP_INCLUDE_DIRS "jwt-cpp/jwt.h")

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
    models/Todo.cc
    models/Card.cc
    models/CommentVote.cc
)

set(CONTROLLER_SOURCES
    controllers/AuthController.cc
    controllers/ArticleController.cc
    controllers/CommentController.cc
    controllers/FavoriteController.cc
    controllers/UserController.cc
    controllers/CreditController.cc
    controllers/TodoController.cc
    controllers/CardController.cc
    controllers/SystemController.cc
    controllers/UploadController.cc
    controllers/CaptchaController.cc
    controllers/AdminController.cc
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
target_link_libraries(${PROJECT_NAME} PRIVATE
    Drogon::Drogon
    OpenSSL::SSL
    OpenSSL::Crypto
    JsonCpp::JsonCpp
    spdlog::spdlog
)

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

