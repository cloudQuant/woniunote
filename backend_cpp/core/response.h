/**
 * @file response.h
 * @brief Unified JSON response helpers.
 *
 * Centralizes the `{code, message, data}` response envelope so controllers
 * stop hand-rolling `Json::Value ret; ret["code"]=...; callback(...)` and so
 * the HTTP status code is always set consistently with the body code.
 *
 * Header-only for zero build wiring.
 */

#ifndef WONIUNOTE_CORE_RESPONSE_H
#define WONIUNOTE_CORE_RESPONSE_H

#include <drogon/HttpResponse.h>
#include <json/json.h>
#include <string>

namespace woniunote {

class Response {
public:
    /**
     * @brief Build a JSON response with an explicit body code and HTTP status.
     * @param code      business code placed in body.code
     * @param message   human-readable message
     * @param data      optional payload placed in body.data
     * @param httpStatus HTTP status code to set on the response
     */
    static drogon::HttpResponsePtr make(int code,
                                        const std::string& message,
                                        const Json::Value& data,
                                        drogon::HttpStatusCode httpStatus)
    {
        Json::Value body;
        body["code"] = code;
        body["message"] = message;
        if (!data.isNull()) {
            body["data"] = data;
        }
        auto resp = drogon::HttpResponse::newHttpJsonResponse(body);
        resp->setStatusCode(httpStatus);
        return resp;
    }

    /** 200 OK with optional data. */
    static drogon::HttpResponsePtr success(const Json::Value& data = Json::Value(),
                                           const std::string& message = "success")
    {
        return make(200, message, data, drogon::k200OK);
    }

    /** 200 OK carrying both data and a custom message. */
    static drogon::HttpResponsePtr ok(const std::string& message,
                                      const Json::Value& data = Json::Value())
    {
        return make(200, message, data, drogon::k200OK);
    }

    /**
     * @brief Error response. HTTP status mirrors the body code when it maps to
     *        a known HTTP status; otherwise falls back to the provided default.
     */
    static drogon::HttpResponsePtr error(int code,
                                         const std::string& message,
                                         drogon::HttpStatusCode httpStatus)
    {
        return make(code, message, Json::Value(), httpStatus);
    }

    // Common shortcuts -----------------------------------------------------
    static drogon::HttpResponsePtr badRequest(const std::string& message) {
        return error(400, message, drogon::k400BadRequest);
    }
    static drogon::HttpResponsePtr unauthorized(const std::string& message) {
        return error(401, message, drogon::k401Unauthorized);
    }
    static drogon::HttpResponsePtr forbidden(const std::string& message) {
        return error(403, message, drogon::k403Forbidden);
    }
    static drogon::HttpResponsePtr notFound(const std::string& message) {
        return error(404, message, drogon::k404NotFound);
    }
    static drogon::HttpResponsePtr tooManyRequests(const std::string& message) {
        return error(429, message, drogon::k429TooManyRequests);
    }
    static drogon::HttpResponsePtr serverError(const std::string& message) {
        return error(500, message, drogon::k500InternalServerError);
    }
};

} // namespace woniunote

#endif // WONIUNOTE_CORE_RESPONSE_H
