/**
 * @file CommentController.h
 * @brief Comment API Controller
 */

#ifndef WONIUNOTE_CONTROLLERS_COMMENT_CONTROLLER_H
#define WONIUNOTE_CONTROLLERS_COMMENT_CONTROLLER_H

#include <drogon/HttpController.h>

namespace woniunote {
namespace controllers {

class CommentController : public drogon::HttpController<CommentController>
{
public:
    METHOD_LIST_BEGIN
    ADD_METHOD_TO(CommentController::listByArticle, "/api/comments/article/{articleId}", drogon::Get);
    ADD_METHOD_TO(CommentController::myComments, "/api/comments/my", drogon::Get, "woniunote::AuthFilter");
    ADD_METHOD_TO(CommentController::create, "/api/comments", drogon::Post, "woniunote::AuthFilter");
    ADD_METHOD_TO(CommentController::remove, "/api/comments/{id}", drogon::Delete, "woniunote::AuthFilter");
    ADD_METHOD_TO(CommentController::vote, "/api/comments/{id}/vote", drogon::Post, "woniunote::AuthFilter");
    METHOD_LIST_END

    void listByArticle(const drogon::HttpRequestPtr& req,
                       std::function<void(const drogon::HttpResponsePtr&)>&& callback,
                       int64_t articleId);

    void myComments(const drogon::HttpRequestPtr& req,
                    std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void create(const drogon::HttpRequestPtr& req,
                std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void remove(const drogon::HttpRequestPtr& req,
                std::function<void(const drogon::HttpResponsePtr&)>&& callback,
                int64_t id);

    void vote(const drogon::HttpRequestPtr& req,
              std::function<void(const drogon::HttpResponsePtr&)>&& callback,
              int64_t id);
};

} // namespace controllers
} // namespace woniunote

#endif // WONIUNOTE_CONTROLLERS_COMMENT_CONTROLLER_H
