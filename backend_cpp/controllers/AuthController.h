/**
 * @file AuthController.h
 * @brief Authentication API Controller
 * 
 * Handles user registration, login, logout, and token management.
 * Corresponds to FastAPI's auth.py router.
 */

#ifndef WONIUNOTE_CONTROLLERS_AUTH_CONTROLLER_H
#define WONIUNOTE_CONTROLLERS_AUTH_CONTROLLER_H

#include <drogon/HttpController.h>
#include <drogon/orm/DbClient.h>

namespace woniunote {
namespace controllers {

/**
 * @class AuthController
 * @brief Authentication API endpoints
 * 
 * Routes:
 * - POST /api/auth/register - User registration
 * - POST /api/auth/login - User login
 * - POST /api/auth/refresh - Refresh access token
 * - GET /api/auth/me - Get current user info
 * - POST /api/auth/logout - User logout
 */
class AuthController : public drogon::HttpController<AuthController>
{
public:
    METHOD_LIST_BEGIN
    ADD_METHOD_TO(AuthController::registerUser, "/api/auth/register", drogon::Post, "woniunote::RateLimitFilter");
    ADD_METHOD_TO(AuthController::login, "/api/auth/login", drogon::Post, "woniunote::RateLimitFilter");
    ADD_METHOD_TO(AuthController::refresh, "/api/auth/refresh", drogon::Post, "woniunote::RateLimitFilter");
    ADD_METHOD_TO(AuthController::me, "/api/auth/me", drogon::Get, "woniunote::AuthFilter");
    ADD_METHOD_TO(AuthController::logout, "/api/auth/logout", drogon::Post, "woniunote::OptionalAuthFilter");
    METHOD_LIST_END

    /**
     * @brief User registration
     * @param req HTTP request with JSON body: {username, password, nickname?, qq?}
     * @param callback Response callback
     */
    void registerUser(const drogon::HttpRequestPtr& req,
                      std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    /**
     * @brief User login
     * @param req HTTP request with JSON body: {username, password, captcha_id?, captcha_code?}
     * @param callback Response callback
     */
    void login(const drogon::HttpRequestPtr& req,
               std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    /**
     * @brief Refresh access token
     * @param req HTTP request with JSON body: {refresh_token}
     * @param callback Response callback
     */
    void refresh(const drogon::HttpRequestPtr& req,
                 std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    /**
     * @brief Get current user info
     * @param req HTTP request (requires AuthFilter)
     * @param callback Response callback
     */
    void me(const drogon::HttpRequestPtr& req,
            std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    /**
     * @brief User logout
     * @param req HTTP request
     * @param callback Response callback
     */
    void logout(const drogon::HttpRequestPtr& req,
                std::function<void(const drogon::HttpResponsePtr&)>&& callback);

private:
    // Helper to create standard JSON responses
    static drogon::HttpResponsePtr makeJsonResponse(int code, 
                                                     const std::string& message,
                                                     const Json::Value& data = Json::Value());
    
    static drogon::HttpResponsePtr makeErrorResponse(int httpCode, 
                                                      const std::string& message);
};

} // namespace controllers
} // namespace woniunote

#endif // WONIUNOTE_CONTROLLERS_AUTH_CONTROLLER_H
