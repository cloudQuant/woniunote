/**
 * @file CaptchaController.cc
 * @brief Captcha API Controller Implementation
 * 
 * Generates simple text-based captcha codes stored in memory cache.
 */

#include "CaptchaController.h"
#include "core/database.h"
#include "core/logger.h"
#include "core/response.h"
#include <drogon/HttpResponse.h>
#include <random>
#include <sstream>
#include <iomanip>
#include <map>
#include <mutex>
#include <chrono>
#include <algorithm>

using namespace drogon;

namespace woniunote {
namespace controllers {

// In-memory captcha storage (thread-safe)
static std::map<std::string, std::pair<std::string, std::chrono::steady_clock::time_point>> captchaCache;
static std::mutex cacheMutex;

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

// Generate a simple SVG captcha image as base64
static std::string generateCaptchaSvg(const std::string& code)
{
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> colorDis(50, 150);
    std::uniform_int_distribution<> posDis(-5, 5);
    std::uniform_int_distribution<> rotDis(-15, 15);
    
    std::ostringstream svg;
    svg << "<svg xmlns='http://www.w3.org/2000/svg' width='120' height='40'>";
    svg << "<rect width='120' height='40' fill='#f0f0f0'/>";
    
    // Add noise lines
    for (int i = 0; i < 5; ++i) {
        int x1 = std::uniform_int_distribution<>(0, 120)(gen);
        int y1 = std::uniform_int_distribution<>(0, 40)(gen);
        int x2 = std::uniform_int_distribution<>(0, 120)(gen);
        int y2 = std::uniform_int_distribution<>(0, 40)(gen);
        int r = colorDis(gen), g = colorDis(gen), b = colorDis(gen);
        svg << "<line x1='" << x1 << "' y1='" << y1 << "' x2='" << x2 << "' y2='" << y2 
            << "' stroke='rgb(" << r << "," << g << "," << b << ")' stroke-width='1'/>";
    }
    
    // Add characters
    int x = 10;
    for (char c : code) {
        int r = colorDis(gen), g = colorDis(gen), b = colorDis(gen);
        int dy = posDis(gen);
        int rot = rotDis(gen);
        svg << "<text x='" << x << "' y='" << (25 + dy) << "' font-size='24' font-family='Arial' "
            << "fill='rgb(" << r << "," << g << "," << b << ")' "
            << "transform='rotate(" << rot << " " << x << " " << (25 + dy) << ")'>" << c << "</text>";
        x += 25;
    }
    
    svg << "</svg>";
    
    // Base64 encode
    static const char base64_chars[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string svgStr = svg.str();
    std::string encoded;
    int i = 0;
    unsigned char char_array_3[3];
    unsigned char char_array_4[4];
    int in_len = svgStr.size();
    const unsigned char* bytes_to_encode = reinterpret_cast<const unsigned char*>(svgStr.data());
    
    while (in_len--) {
        char_array_3[i++] = *(bytes_to_encode++);
        if (i == 3) {
            char_array_4[0] = (char_array_3[0] & 0xfc) >> 2;
            char_array_4[1] = ((char_array_3[0] & 0x03) << 4) + ((char_array_3[1] & 0xf0) >> 4);
            char_array_4[2] = ((char_array_3[1] & 0x0f) << 2) + ((char_array_3[2] & 0xc0) >> 6);
            char_array_4[3] = char_array_3[2] & 0x3f;
            for(i = 0; i < 4; i++) encoded += base64_chars[char_array_4[i]];
            i = 0;
        }
    }
    if (i) {
        for(int j = i; j < 3; j++) char_array_3[j] = '\0';
        char_array_4[0] = (char_array_3[0] & 0xfc) >> 2;
        char_array_4[1] = ((char_array_3[0] & 0x03) << 4) + ((char_array_3[1] & 0xf0) >> 4);
        char_array_4[2] = ((char_array_3[1] & 0x0f) << 2) + ((char_array_3[2] & 0xc0) >> 6);
        for (int j = 0; j < i + 1; j++) encoded += base64_chars[char_array_4[j]];
        while(i++ < 3) encoded += '=';
    }
    
    return "data:image/svg+xml;base64," + encoded;
}

// Store captcha in memory cache
static void storeCaptcha(const std::string& id, const std::string& code)
{
    std::lock_guard<std::mutex> lock(cacheMutex);
    auto expiry = std::chrono::steady_clock::now() + std::chrono::minutes(5);
    captchaCache[id] = {code, expiry};
    
    // Clean expired entries
    auto now = std::chrono::steady_clock::now();
    for (auto it = captchaCache.begin(); it != captchaCache.end();) {
        if (it->second.second < now) {
            it = captchaCache.erase(it);
        } else {
            ++it;
        }
    }
}

// Get captcha from memory cache
static std::string getCaptcha(const std::string& id)
{
    std::lock_guard<std::mutex> lock(cacheMutex);
    auto it = captchaCache.find(id);
    if (it != captchaCache.end() && it->second.second > std::chrono::steady_clock::now()) {
        std::string code = it->second.first;
        captchaCache.erase(it);  // One-time use
        return code;
    }
    return "";
}

bool CaptchaController::validateCaptcha(const std::string& captchaId,
                                        const std::string& captchaCode)
{
    if (captchaId.empty() || captchaCode.empty()) {
        return false;
    }
    std::string stored = getCaptcha(captchaId);
    if (stored.empty()) {
        return false;
    }
    std::string upper = captchaCode;
    std::transform(upper.begin(), upper.end(), upper.begin(), ::toupper);
    return stored == upper;
}

void CaptchaController::generate(const HttpRequestPtr& req,
                                 std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::debug("[Captcha] Generate request", {{"ip", req->getPeerAddr().toIp()}});
    std::string captchaId = generateCaptchaId();
    std::string captchaCode = generateCaptchaCode();
    
    // Store in memory cache
    storeCaptcha(captchaId, captchaCode);
    
    // Generate SVG image
    std::string imageData = generateCaptchaSvg(captchaCode);
    
    Logger::debug("[Captcha] Generated", {{"captcha_id", captchaId}});
    Json::Value data;
    data["captcha_id"] = captchaId;
    data["image"] = imageData;
    callback(Response::success(data));
}

void CaptchaController::verify(const HttpRequestPtr& req,
                               std::function<void(const HttpResponsePtr&)>&& callback)
{
    Logger::debug("[Captcha] Verify request");
    auto json = req->getJsonObject();
    if (!json || !json->isMember("captcha_id") || !json->isMember("captcha_code")) {
        Logger::warning("[Captcha] Verify failed: missing fields");
        callback(Response::badRequest("请提供验证码ID和验证码"));
        return;
    }
    
    std::string captchaId = (*json)["captcha_id"].asString();
    std::string captchaCode = (*json)["captcha_code"].asString();
    
    // Convert to uppercase for comparison
    std::transform(captchaCode.begin(), captchaCode.end(), captchaCode.begin(), ::toupper);
    
    // Get from memory cache
    std::string storedCode = getCaptcha(captchaId);
    
    if (storedCode.empty()) {
        Json::Value data;
        data["valid"] = false;
        callback(Response::make(400, "验证码已过期", data, k400BadRequest));
        return;
    }
    
    bool valid = (storedCode == captchaCode);
    
    if (valid) {
        Logger::debug("[Captcha] Verified successfully", {{"captcha_id", captchaId}});
    } else {
        Logger::debug("[Captcha] Verification failed", {{"captcha_id", captchaId}});
    }
    
    Json::Value data;
    data["valid"] = valid;
    callback(Response::make(valid ? 200 : 400,
                            valid ? "验证成功" : "验证码错误",
                            data,
                            valid ? k200OK : k400BadRequest));
}

} // namespace controllers
} // namespace woniunote
