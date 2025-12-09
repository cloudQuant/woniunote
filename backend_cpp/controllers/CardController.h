/**
 * @file CardController.h
 * @brief Card API Controller
 */

#ifndef WONIUNOTE_CONTROLLERS_CARD_CONTROLLER_H
#define WONIUNOTE_CONTROLLERS_CARD_CONTROLLER_H

#include <drogon/HttpController.h>

namespace woniunote {
namespace controllers {

class CardController : public drogon::HttpController<CardController>
{
public:
    METHOD_LIST_BEGIN
    // Categories
    ADD_METHOD_TO(CardController::listCategories, "/api/cards/categories", drogon::Get, "woniunote::AuthFilter");
    ADD_METHOD_TO(CardController::createCategory, "/api/cards/categories", drogon::Post, "woniunote::AuthFilter");
    ADD_METHOD_TO(CardController::deleteCategory, "/api/cards/categories/{id}", drogon::Delete, "woniunote::AuthFilter");
    
    // Cards
    ADD_METHOD_TO(CardController::listCards, "/api/cards", drogon::Get, "woniunote::AuthFilter");
    ADD_METHOD_TO(CardController::createCard, "/api/cards", drogon::Post, "woniunote::AuthFilter");
    ADD_METHOD_TO(CardController::updateCard, "/api/cards/{id}", drogon::Put, "woniunote::AuthFilter");
    ADD_METHOD_TO(CardController::deleteCard, "/api/cards/{id}", drogon::Delete, "woniunote::AuthFilter");
    ADD_METHOD_TO(CardController::startTimer, "/api/cards/{id}/start", drogon::Post, "woniunote::AuthFilter");
    ADD_METHOD_TO(CardController::stopTimer, "/api/cards/{id}/stop", drogon::Post, "woniunote::AuthFilter");
    METHOD_LIST_END

    void listCategories(const drogon::HttpRequestPtr& req,
                        std::function<void(const drogon::HttpResponsePtr&)>&& callback);
    void createCategory(const drogon::HttpRequestPtr& req,
                        std::function<void(const drogon::HttpResponsePtr&)>&& callback);
    void deleteCategory(const drogon::HttpRequestPtr& req,
                        std::function<void(const drogon::HttpResponsePtr&)>&& callback, int64_t id);

    void listCards(const drogon::HttpRequestPtr& req,
                   std::function<void(const drogon::HttpResponsePtr&)>&& callback);
    void createCard(const drogon::HttpRequestPtr& req,
                    std::function<void(const drogon::HttpResponsePtr&)>&& callback);
    void updateCard(const drogon::HttpRequestPtr& req,
                    std::function<void(const drogon::HttpResponsePtr&)>&& callback, int64_t id);
    void deleteCard(const drogon::HttpRequestPtr& req,
                    std::function<void(const drogon::HttpResponsePtr&)>&& callback, int64_t id);
    void startTimer(const drogon::HttpRequestPtr& req,
                    std::function<void(const drogon::HttpResponsePtr&)>&& callback, int64_t id);
    void stopTimer(const drogon::HttpRequestPtr& req,
                   std::function<void(const drogon::HttpResponsePtr&)>&& callback, int64_t id);
};

} // namespace controllers
} // namespace woniunote

#endif // WONIUNOTE_CONTROLLERS_CARD_CONTROLLER_H
