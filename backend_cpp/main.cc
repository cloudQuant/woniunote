/**
 * @file main.cc
 * @brief WoniuNote C++ Backend Entry Point
 * 
 * Main entry point for the Drogon-based WoniuNote backend server.
 */

#include <drogon/drogon.h>
#include <iostream>
#include <fstream>
#include "core/config.h"
#include "core/logger.h"

using namespace drogon;

int main(int argc, char* argv[])
{
    // Initialize logger
    woniunote::Logger::init("logs");
    woniunote::Logger::info("=== WoniuNote C++ Backend Starting ===");
    woniunote::Logger::info("Version: 2.0.0-cpp");

    // Load Drogon configuration. Prefer config.local.json when present so
    // local credentials (DB/Redis passwords, dev JWT secret) stay out of the
    // git-tracked config.json. Falls back to config.json otherwise.
    try {
        std::string configFile = "config.json";
        if (std::ifstream("config.local.json").good()) {
            configFile = "config.local.json";
        }
        woniunote::Logger::info("Loading configuration from " + configFile);
        app().loadConfigFile(configFile);
        woniunote::Logger::info("Configuration loaded successfully");
    } catch (const std::exception& e) {
        woniunote::Logger::error("Failed to load configuration: " + std::string(e.what()));
        return 1;
    }

    // Initialize application configuration (JWT secret, CORS whitelist, etc.)
    woniunote::Config::instance().init();

    // Resolve the CORS allow-list from configuration. Only origins on this
    // list may receive Access-Control-Allow-Origin with credentials enabled.
    const auto corsOrigins = woniunote::Config::instance().getCorsOrigins();
    auto isAllowedOrigin = [corsOrigins](const std::string& origin) -> bool {
        if (origin.empty()) return false;
        for (const auto& allowed : corsOrigins) {
            if (allowed == origin) return true;
        }
        return false;
    };

    // CORS configuration - only reflect Origin when it is whitelisted.
    app().registerPostHandlingAdvice(
        [isAllowedOrigin](const HttpRequestPtr& req, const HttpResponsePtr& resp) {
            auto origin = req->getHeader("Origin");
            if (isAllowedOrigin(origin)) {
                resp->addHeader("Access-Control-Allow-Origin", origin);
                resp->addHeader("Access-Control-Allow-Credentials", "true");
            }
            resp->addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
            resp->addHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With");
        });

    // Handle OPTIONS preflight requests globally
    app().registerHandler(
        "/api/{path}",
        [isAllowedOrigin](const HttpRequestPtr& req,
           std::function<void(const HttpResponsePtr&)>&& callback,
           const std::string& path) {
            woniunote::Logger::debug("[CORS] Preflight request", {{"path", "/api/" + path}});
            auto resp = HttpResponse::newHttpResponse();
            auto origin = req->getHeader("Origin");
            if (isAllowedOrigin(origin)) {
                resp->addHeader("Access-Control-Allow-Origin", origin);
                resp->addHeader("Access-Control-Allow-Credentials", "true");
            }
            resp->addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
            resp->addHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With");
            resp->addHeader("Access-Control-Max-Age", "86400");
            resp->setStatusCode(k204NoContent);
            callback(resp);
        },
        {Options}
    );

    woniunote::Logger::info("CORS handling configured");

    // Log all incoming requests
    app().registerPreRoutingAdvice([](const HttpRequestPtr& req) {
        woniunote::Logger::info("[Request] " + std::string(req->methodString()) + " " + req->getPath(), 
            {{"ip", req->getPeerAddr().toIp()}});
    });

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
    woniunote::Logger::info("=== Starting HTTP server ===");

    // Run the application
    app().run();

    woniunote::Logger::info("=== WoniuNote C++ Backend Shutting Down ===");
    woniunote::Logger::shutdown();

    return 0;
}
