/**
 * @file FavoriteController.h
 * @brief Favorite API Controller
 */

#ifndef WONIUNOTE_CONTROLLERS_FAVORITE_CONTROLLER_H
#define WONIUNOTE_CONTROLLERS_FAVORITE_CONTROLLER_H

#include <drogon/HttpController.h>

namespace woniunote {
namespace controllers {

class FavoriteController : public drogon::HttpController<FavoriteController>
{
public:
    METHOD_LIST_BEGIN
    ADD_METHOD_TO(FavoriteController::list, "/api/favorites", drogon::Get, "woniunote::AuthFilter");
    ADD_METHOD_TO(FavoriteController::add, "/api/favorites", drogon::Post, "woniunote::AuthFilter");
    ADD_METHOD_TO(FavoriteController::remove, "/api/favorites/{articleId}", drogon::Delete, "woniunote::AuthFilter");
    ADD_METHOD_TO(FavoriteController::check, "/api/favorites/check/{articleId}", drogon::Get, "woniunote::AuthFilter");
    METHOD_LIST_END

    void list(const drogon::HttpRequestPtr& req,
              std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void add(const drogon::HttpRequestPtr& req,
             std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void remove(const drogon::HttpRequestPtr& req,
                std::function<void(const drogon::HttpResponsePtr&)>&& callback,
                int64_t articleId);

    void check(const drogon::HttpRequestPtr& req,
               std::function<void(const drogon::HttpResponsePtr&)>&& callback,
               int64_t articleId);
};

} // namespace controllers
} // namespace woniunote

#endif // WONIUNOTE_CONTROLLERS_FAVORITE_CONTROLLER_H
