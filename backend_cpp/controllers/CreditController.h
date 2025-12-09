/**
 * @file CreditController.h
 * @brief Credit API Controller
 */

#ifndef WONIUNOTE_CONTROLLERS_CREDIT_CONTROLLER_H
#define WONIUNOTE_CONTROLLERS_CREDIT_CONTROLLER_H

#include <drogon/HttpController.h>

namespace woniunote {
namespace controllers {

class CreditController : public drogon::HttpController<CreditController>
{
public:
    METHOD_LIST_BEGIN
    ADD_METHOD_TO(CreditController::getBalance, "/api/credits/balance", drogon::Get, "woniunote::AuthFilter");
    ADD_METHOD_TO(CreditController::getHistory, "/api/credits/history", drogon::Get, "woniunote::AuthFilter");
    METHOD_LIST_END

    void getBalance(const drogon::HttpRequestPtr& req,
                    std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void getHistory(const drogon::HttpRequestPtr& req,
                    std::function<void(const drogon::HttpResponsePtr&)>&& callback);
};

} // namespace controllers
} // namespace woniunote

#endif // WONIUNOTE_CONTROLLERS_CREDIT_CONTROLLER_H
