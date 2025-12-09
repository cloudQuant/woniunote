/**
 * @file UserController.h
 * @brief User API Controller
 * 
 * User profile management endpoints.
 */

#ifndef WONIUNOTE_CONTROLLERS_USER_CONTROLLER_H
#define WONIUNOTE_CONTROLLERS_USER_CONTROLLER_H

#include <drogon/HttpController.h>

namespace woniunote {
namespace controllers {

class UserController : public drogon::HttpController<UserController>
{
public:
    METHOD_LIST_BEGIN
    ADD_METHOD_TO(UserController::getUser, "/api/users/{id}", drogon::Get);
    ADD_METHOD_TO(UserController::updateProfile, "/api/users/profile", drogon::Put, "woniunote::AuthFilter");
    ADD_METHOD_TO(UserController::changePassword, "/api/users/password", drogon::Post, "woniunote::AuthFilter");
    METHOD_LIST_END

    void getUser(const drogon::HttpRequestPtr& req,
                 std::function<void(const drogon::HttpResponsePtr&)>&& callback,
                 int64_t id);

    void updateProfile(const drogon::HttpRequestPtr& req,
                       std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void changePassword(const drogon::HttpRequestPtr& req,
                        std::function<void(const drogon::HttpResponsePtr&)>&& callback);
};

} // namespace controllers
} // namespace woniunote

#endif // WONIUNOTE_CONTROLLERS_USER_CONTROLLER_H
