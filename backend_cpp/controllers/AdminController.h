/**
 * @file AdminController.h
 * @brief Admin API Controller
 */

#ifndef WONIUNOTE_CONTROLLERS_ADMIN_CONTROLLER_H
#define WONIUNOTE_CONTROLLERS_ADMIN_CONTROLLER_H

#include <drogon/HttpController.h>

namespace woniunote {
namespace controllers {

class AdminController : public drogon::HttpController<AdminController>
{
public:
    METHOD_LIST_BEGIN
    // Dashboard
    ADD_METHOD_TO(AdminController::getStats, "/api/admin/stats", drogon::Get, "woniunote::AdminFilter");
    
    // User Management
    ADD_METHOD_TO(AdminController::listUsers, "/api/admin/users", drogon::Get, "woniunote::AdminFilter");
    ADD_METHOD_TO(AdminController::updateUser, "/api/admin/users/{id}", drogon::Put, "woniunote::AdminFilter");
    ADD_METHOD_TO(AdminController::deleteUser, "/api/admin/users/{id}", drogon::Delete, "woniunote::AdminFilter");
    
    // Article Management
    ADD_METHOD_TO(AdminController::listArticles, "/api/admin/articles", drogon::Get, "woniunote::AdminFilter");
    ADD_METHOD_TO(AdminController::updateArticleType, "/api/admin/articles/{id}/type", drogon::Put, "woniunote::AdminFilter");
    ADD_METHOD_TO(AdminController::deleteArticle, "/api/admin/articles/{id}", drogon::Delete, "woniunote::AdminFilter");

    // Article Category/Menu Management
    ADD_METHOD_TO(AdminController::listArticleCategories, "/api/admin/article-categories", drogon::Get, "woniunote::AdminFilter");
    ADD_METHOD_TO(AdminController::createArticleCategory, "/api/admin/article-categories", drogon::Post, "woniunote::AdminFilter");
    ADD_METHOD_TO(AdminController::updateArticleCategory, "/api/admin/article-categories/{id}", drogon::Put, "woniunote::AdminFilter");
    ADD_METHOD_TO(AdminController::deleteArticleCategory, "/api/admin/article-categories/{id}", drogon::Delete, "woniunote::AdminFilter");
    
    // Comment Management
    ADD_METHOD_TO(AdminController::listComments, "/api/admin/comments", drogon::Get, "woniunote::AdminFilter");
    ADD_METHOD_TO(AdminController::deleteComment, "/api/admin/comments/{id}", drogon::Delete, "woniunote::AdminFilter");
    METHOD_LIST_END

    void getStats(const drogon::HttpRequestPtr& req,
                  std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void listUsers(const drogon::HttpRequestPtr& req,
                   std::function<void(const drogon::HttpResponsePtr&)>&& callback);
    void updateUser(const drogon::HttpRequestPtr& req,
                    std::function<void(const drogon::HttpResponsePtr&)>&& callback, int64_t id);
    void deleteUser(const drogon::HttpRequestPtr& req,
                    std::function<void(const drogon::HttpResponsePtr&)>&& callback, int64_t id);

    void listArticles(const drogon::HttpRequestPtr& req,
                      std::function<void(const drogon::HttpResponsePtr&)>&& callback);
    void updateArticleType(const drogon::HttpRequestPtr& req,
                           std::function<void(const drogon::HttpResponsePtr&)>&& callback, int64_t id);
    void deleteArticle(const drogon::HttpRequestPtr& req,
                       std::function<void(const drogon::HttpResponsePtr&)>&& callback, int64_t id);

    void listArticleCategories(const drogon::HttpRequestPtr& req,
                               std::function<void(const drogon::HttpResponsePtr&)>&& callback);
    void createArticleCategory(const drogon::HttpRequestPtr& req,
                               std::function<void(const drogon::HttpResponsePtr&)>&& callback);
    void updateArticleCategory(const drogon::HttpRequestPtr& req,
                               std::function<void(const drogon::HttpResponsePtr&)>&& callback, int64_t id);
    void deleteArticleCategory(const drogon::HttpRequestPtr& req,
                               std::function<void(const drogon::HttpResponsePtr&)>&& callback, int64_t id);

    void listComments(const drogon::HttpRequestPtr& req,
                      std::function<void(const drogon::HttpResponsePtr&)>&& callback);
    void deleteComment(const drogon::HttpRequestPtr& req,
                       std::function<void(const drogon::HttpResponsePtr&)>&& callback, int64_t id);
};

} // namespace controllers
} // namespace woniunote

#endif // WONIUNOTE_CONTROLLERS_ADMIN_CONTROLLER_H
