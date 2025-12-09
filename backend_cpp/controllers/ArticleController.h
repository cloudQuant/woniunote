/**
 * @file ArticleController.h
 * @brief Article API Controller
 * 
 * Article CRUD and listing endpoints.
 */

#ifndef WONIUNOTE_CONTROLLERS_ARTICLE_CONTROLLER_H
#define WONIUNOTE_CONTROLLERS_ARTICLE_CONTROLLER_H

#include <drogon/HttpController.h>

namespace woniunote {
namespace controllers {

class ArticleController : public drogon::HttpController<ArticleController>
{
public:
    METHOD_LIST_BEGIN
    // Public endpoints
    ADD_METHOD_TO(ArticleController::list, "/api/articles", drogon::Get);
    ADD_METHOD_TO(ArticleController::getTypes, "/api/articles/types", drogon::Get);
    ADD_METHOD_TO(ArticleController::getHot, "/api/articles/hot", drogon::Get);
    ADD_METHOD_TO(ArticleController::get, "/api/articles/{id}", drogon::Get);
    
    // Protected endpoints
    ADD_METHOD_TO(ArticleController::myArticles, "/api/articles/my", drogon::Get, "woniunote::AuthFilter");
    ADD_METHOD_TO(ArticleController::create, "/api/articles", drogon::Post, "woniunote::AuthFilter");
    ADD_METHOD_TO(ArticleController::update, "/api/articles/{id}", drogon::Put, "woniunote::AuthFilter");
    ADD_METHOD_TO(ArticleController::remove, "/api/articles/{id}", drogon::Delete, "woniunote::AuthFilter");
    
    // Admin endpoints
    ADD_METHOD_TO(ArticleController::toggleRecommend, "/api/articles/{id}/recommend", drogon::Post, "woniunote::AdminFilter");
    ADD_METHOD_TO(ArticleController::toggleHide, "/api/articles/{id}/hide", drogon::Post, "woniunote::AdminFilter");
    METHOD_LIST_END

    void list(const drogon::HttpRequestPtr& req,
              std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void getTypes(const drogon::HttpRequestPtr& req,
                  std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void getHot(const drogon::HttpRequestPtr& req,
                std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void get(const drogon::HttpRequestPtr& req,
             std::function<void(const drogon::HttpResponsePtr&)>&& callback,
             int64_t id);

    void myArticles(const drogon::HttpRequestPtr& req,
                    std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void create(const drogon::HttpRequestPtr& req,
                std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void update(const drogon::HttpRequestPtr& req,
                std::function<void(const drogon::HttpResponsePtr&)>&& callback,
                int64_t id);

    void remove(const drogon::HttpRequestPtr& req,
                std::function<void(const drogon::HttpResponsePtr&)>&& callback,
                int64_t id);

    void toggleRecommend(const drogon::HttpRequestPtr& req,
                         std::function<void(const drogon::HttpResponsePtr&)>&& callback,
                         int64_t id);

    void toggleHide(const drogon::HttpRequestPtr& req,
                    std::function<void(const drogon::HttpResponsePtr&)>&& callback,
                    int64_t id);
};

} // namespace controllers
} // namespace woniunote

#endif // WONIUNOTE_CONTROLLERS_ARTICLE_CONTROLLER_H
