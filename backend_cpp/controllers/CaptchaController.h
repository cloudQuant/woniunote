/**
 * @file CaptchaController.h
 * @brief Captcha API Controller
 */

#ifndef WONIUNOTE_CONTROLLERS_CAPTCHA_CONTROLLER_H
#define WONIUNOTE_CONTROLLERS_CAPTCHA_CONTROLLER_H

#include <drogon/HttpController.h>

namespace woniunote {
namespace controllers {

class CaptchaController : public drogon::HttpController<CaptchaController>
{
public:
    METHOD_LIST_BEGIN
    ADD_METHOD_TO(CaptchaController::generate, "/api/captcha/generate", drogon::Get);
    ADD_METHOD_TO(CaptchaController::verify, "/api/captcha/verify", drogon::Post);
    METHOD_LIST_END

    void generate(const drogon::HttpRequestPtr& req,
                  std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void verify(const drogon::HttpRequestPtr& req,
                std::function<void(const drogon::HttpResponsePtr&)>&& callback);
};

} // namespace controllers
} // namespace woniunote

#endif // WONIUNOTE_CONTROLLERS_CAPTCHA_CONTROLLER_H
