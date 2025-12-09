/**
 * @file TodoController.h
 * @brief Todo API Controller
 */

#ifndef WONIUNOTE_CONTROLLERS_TODO_CONTROLLER_H
#define WONIUNOTE_CONTROLLERS_TODO_CONTROLLER_H

#include <drogon/HttpController.h>

namespace woniunote {
namespace controllers {

class TodoController : public drogon::HttpController<TodoController>
{
public:
    METHOD_LIST_BEGIN
    // Categories
    ADD_METHOD_TO(TodoController::listCategories, "/api/todos/categories", drogon::Get, "woniunote::AuthFilter");
    ADD_METHOD_TO(TodoController::createCategory, "/api/todos/categories", drogon::Post, "woniunote::AuthFilter");
    ADD_METHOD_TO(TodoController::deleteCategory, "/api/todos/categories/{id}", drogon::Delete, "woniunote::AuthFilter");
    
    // Items
    ADD_METHOD_TO(TodoController::listItems, "/api/todos/items", drogon::Get, "woniunote::AuthFilter");
    ADD_METHOD_TO(TodoController::createItem, "/api/todos/items", drogon::Post, "woniunote::AuthFilter");
    ADD_METHOD_TO(TodoController::updateItem, "/api/todos/items/{id}", drogon::Put, "woniunote::AuthFilter");
    ADD_METHOD_TO(TodoController::deleteItem, "/api/todos/items/{id}", drogon::Delete, "woniunote::AuthFilter");
    ADD_METHOD_TO(TodoController::toggleDone, "/api/todos/items/{id}/toggle", drogon::Post, "woniunote::AuthFilter");
    METHOD_LIST_END

    void listCategories(const drogon::HttpRequestPtr& req,
                        std::function<void(const drogon::HttpResponsePtr&)>&& callback);
    void createCategory(const drogon::HttpRequestPtr& req,
                        std::function<void(const drogon::HttpResponsePtr&)>&& callback);
    void deleteCategory(const drogon::HttpRequestPtr& req,
                        std::function<void(const drogon::HttpResponsePtr&)>&& callback, int64_t id);

    void listItems(const drogon::HttpRequestPtr& req,
                   std::function<void(const drogon::HttpResponsePtr&)>&& callback);
    void createItem(const drogon::HttpRequestPtr& req,
                    std::function<void(const drogon::HttpResponsePtr&)>&& callback);
    void updateItem(const drogon::HttpRequestPtr& req,
                    std::function<void(const drogon::HttpResponsePtr&)>&& callback, int64_t id);
    void deleteItem(const drogon::HttpRequestPtr& req,
                    std::function<void(const drogon::HttpResponsePtr&)>&& callback, int64_t id);
    void toggleDone(const drogon::HttpRequestPtr& req,
                    std::function<void(const drogon::HttpResponsePtr&)>&& callback, int64_t id);
};

} // namespace controllers
} // namespace woniunote

#endif // WONIUNOTE_CONTROLLERS_TODO_CONTROLLER_H
