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

    /**
     * @brief Validate and consume a captcha code (one-time use).
     * @param captchaId Captcha identifier returned by generate
     * @param captchaCode User-supplied code (case-insensitive)
     * @return true if the code matches an unexpired stored captcha
     *
     * Shared with other controllers (e.g. login) so captcha logic lives in
     * one place. Consumes the captcha on a successful match.
     */
    static bool validateCaptcha(const std::string& captchaId,
                                const std::string& captchaCode);
};

} // namespace controllers
} // namespace woniunote

#endif // WONIUNOTE_CONTROLLERS_CAPTCHA_CONTROLLER_H
