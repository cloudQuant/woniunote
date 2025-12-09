/**
 * @file CaptchaController.cc
 * @brief Captcha API Controller Implementation
 * 
 * Generates simple text-based captcha codes stored in Redis.
 * For production, consider using image captcha libraries.
 */

#include "CaptchaController.h"
#include "core/database.h"
#include "core/logger.h"
#include <drogon/HttpResponse.h>
#include <drogon/nosql/RedisClient.h>
#include <random>
#include <sstream>
#include <iomanip>

using namespace drogon;

namespace woniunote {
namespace controllers {

static std::string generateCaptchaId()
{
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(0, 15);
    
    std::ostringstream oss;
    for (int i = 0; i < 32; ++i) {
        oss << std::hex << dis(gen);
    }
    return oss.str();
}

static std::string generateCaptchaCode(int length = 4)
{
    static const char chars[] = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(0, sizeof(chars) - 2);
    
    std::string code;
    code.reserve(length);
    for (int i = 0; i < length; ++i) {
        code += chars[dis(gen)];
    }
    return code;
}

void CaptchaController::generate(const HttpRequestPtr& req,
                                 std::function<void(const HttpResponsePtr&)>&& callback)
{
    std::string captchaId = generateCaptchaId();
    std::string captchaCode = generateCaptchaCode();
    
    // Store in Redis with 5 minute expiration
    auto redisClient = app().getRedisClient();
    if (redisClient) {
        redisClient->execCommandAsync(
            [captchaId, captchaCode, callback](const drogon::nosql::RedisResult& r) {
                Json::Value ret;
                ret["code"] = 200;
                ret["message"] = "success";
                ret["data"]["captcha_id"] = captchaId;
                ret["data"]["captcha_code"] = captchaCode;  // In production, return image instead
                callback(HttpResponse::newHttpJsonResponse(ret));
            },
            [callback](const std::exception& e) {
                Logger::error("Redis error: " + std::string(e.what()));
                Json::Value ret;
                ret["code"] = 500;
                ret["message"] = "生成验证码失败";
                callback(HttpResponse::newHttpJsonResponse(ret));
            },
            "SETEX captcha:%s 300 %s",
            captchaId.c_str(),
            captchaCode.c_str()
        );
    } else {
        // Fallback: return code without storing (for testing)
        Json::Value ret;
        ret["code"] = 200;
        ret["message"] = "success";
        ret["data"]["captcha_id"] = captchaId;
        ret["data"]["captcha_code"] = captchaCode;
        callback(HttpResponse::newHttpJsonResponse(ret));
    }
}

void CaptchaController::verify(const HttpRequestPtr& req,
                               std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto json = req->getJsonObject();
    if (!json || !json->isMember("captcha_id") || !json->isMember("captcha_code")) {
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "请提供验证码ID和验证码";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }
    
    std::string captchaId = (*json)["captcha_id"].asString();
    std::string captchaCode = (*json)["captcha_code"].asString();
    
    // Convert to uppercase for comparison
    std::transform(captchaCode.begin(), captchaCode.end(), captchaCode.begin(), ::toupper);
    
    auto redisClient = app().getRedisClient();
    if (redisClient) {
        redisClient->execCommandAsync(
            [captchaId, captchaCode, callback](const drogon::nosql::RedisResult& r) {
                if (r.isNil()) {
                    Json::Value ret;
                    ret["code"] = 400;
                    ret["message"] = "验证码已过期";
                    ret["data"]["valid"] = false;
                    callback(HttpResponse::newHttpJsonResponse(ret));
                    return;
                }
                
                std::string storedCode = r.asString();
                bool valid = (storedCode == captchaCode);
                
                Json::Value ret;
                ret["code"] = valid ? 200 : 400;
                ret["message"] = valid ? "验证成功" : "验证码错误";
                ret["data"]["valid"] = valid;
                callback(HttpResponse::newHttpJsonResponse(ret));
            },
            [callback](const std::exception& e) {
                Logger::error("Redis error: " + std::string(e.what()));
                Json::Value ret;
                ret["code"] = 500;
                ret["message"] = "验证失败";
                callback(HttpResponse::newHttpJsonResponse(ret));
            },
            "GET captcha:%s",
            captchaId.c_str()
        );
    } else {
        // Fallback: always succeed (for testing)
        Json::Value ret;
        ret["code"] = 200;
        ret["message"] = "验证成功 (Redis不可用，已跳过验证)";
        ret["data"]["valid"] = true;
        callback(HttpResponse::newHttpJsonResponse(ret));
    }
}

} // namespace controllers
} // namespace woniunote
