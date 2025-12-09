/**
 * @file main.cc
 * @brief WoniuNote C++ Backend Entry Point
 * 
 * Main entry point for the Drogon-based WoniuNote backend server.
 */

#include <drogon/drogon.h>
#include <iostream>
#include "core/config.h"
#include "core/logger.h"

using namespace drogon;

int main(int argc, char* argv[])
{
    // Initialize logger
    woniunote::Logger::init();
    woniunote::Logger::info("WoniuNote C++ Backend starting...");

    // Load Drogon configuration
    try {
        app().loadConfigFile("config.json");
    } catch (const std::exception& e) {
        woniunote::Logger::error("Failed to load config.json: " + std::string(e.what()));
        return 1;
    }

    // CORS configuration
    auto& customConfig = app().getCustomConfig();
    if (customConfig.isMember("cors_origins")) {
        // CORS will be handled by a filter
        woniunote::Logger::info("CORS origins configured from config.json");
    }

    // Register lifecycle callbacks
    app().registerBeginningAdvice([]() {
        woniunote::Logger::info("WoniuNote API v2.0.0 (C++) started successfully");
        woniunote::Logger::info("Server listening on configured ports");
    });

    // Health check endpoint
    app().registerHandler(
        "/health",
        [](const HttpRequestPtr& req,
           std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value ret;
            ret["status"] = "healthy";
            ret["version"] = "2.0.0-cpp";
            auto resp = HttpResponse::newHttpJsonResponse(ret);
            callback(resp);
        },
        {Get}
    );

    // Root endpoint
    app().registerHandler(
        "/",
        [](const HttpRequestPtr& req,
           std::function<void(const HttpResponsePtr&)>&& callback) {
            Json::Value ret;
            ret["message"] = "WoniuNote API v2.0.0 (C++)";
            ret["status"] = "running";
            auto resp = HttpResponse::newHttpJsonResponse(ret);
            callback(resp);
        },
        {Get}
    );

    woniunote::Logger::info("Registered core routes: /, /health");

    // Run the application
    app().run();

    return 0;
}
