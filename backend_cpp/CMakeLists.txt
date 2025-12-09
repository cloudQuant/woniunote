cmake_minimum_required(VERSION 3.20)
project(woniunote_backend CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Drogon package
find_package(Drogon CONFIG REQUIRED)

# Find additional packages
find_package(OpenSSL REQUIRED)
find_package(jsoncpp CONFIG REQUIRED)

# Source files
set(CORE_SOURCES
    core/config.cc
    core/database.cc
    core/security.cc
    core/logger.cc
)

set(CONTROLLER_SOURCES
    controllers/AuthController.cc
    controllers/ArticleController.cc
    controllers/CommentController.cc
    controllers/FavoriteController.cc
    controllers/UserController.cc
    controllers/CreditController.cc
    controllers/UploadController.cc
    controllers/CaptchaController.cc
    controllers/ThumbController.cc
    controllers/UEditorController.cc
    controllers/AdminController.cc
    controllers/TodoController.cc
    controllers/CardController.cc
    controllers/SystemController.cc
)

set(FILTER_SOURCES
    filters/AuthFilter.cc
    filters/AdminFilter.cc
    filters/RateLimitFilter.cc
)

# Main executable
add_executable(${PROJECT_NAME}
    main.cc
    ${CORE_SOURCES}
    # Controllers and filters will be added as implemented
    # ${CONTROLLER_SOURCES}
    # ${FILTER_SOURCES}
)

# Link libraries
target_link_libraries(${PROJECT_NAME} PRIVATE
    Drogon::Drogon
    OpenSSL::SSL
    OpenSSL::Crypto
    JsonCpp::JsonCpp
)

# Include directories
target_include_directories(${PROJECT_NAME} PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/core
    ${CMAKE_CURRENT_SOURCE_DIR}/controllers
    ${CMAKE_CURRENT_SOURCE_DIR}/filters
    ${CMAKE_CURRENT_SOURCE_DIR}/models
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
