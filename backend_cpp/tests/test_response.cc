/**
 * @file test_response.cc
 * @brief Unit tests for the unified Response envelope helpers (core/response.h).
 *
 * These guard the contract every controller relies on after the iteration 10
 * response-unification work: the JSON body always carries {code, message[, data]}
 * and the HTTP status code matches the semantic of the helper used. The frontend
 * Axios interceptor branches on HTTP status (401/403/404/429/500), so a drift
 * between body code and HTTP status would silently break error handling.
 */

#include "test_framework.h"
#include "core/response.h"

#include <json/json.h>
#include <memory>
#include <string>

using namespace woniunote;
using namespace drogon;

namespace {

// Parse a Drogon response body back into a Json::Value for assertions.
Json::Value parseBody(const HttpResponsePtr& resp) {
    Json::Value root;
    Json::CharReaderBuilder builder;
    const std::string body{resp->getBody()};
    std::string errs;
    std::unique_ptr<Json::CharReader> reader(builder.newCharReader());
    reader->parse(body.data(), body.data() + body.size(), &root, &errs);
    return root;
}

} // namespace

// ---------------------------------------------------------------------------
// success / ok — 200 path
// ---------------------------------------------------------------------------

TEST_CASE(response_success_sets_200_and_envelope) {
    Json::Value data;
    data["articleid"] = 7;
    auto resp = Response::success(data);

    CHECK(resp != nullptr);
    CHECK(resp->getStatusCode() == k200OK);

    auto body = parseBody(resp);
    CHECK_EQ(body["code"].asInt(), 200);
    CHECK_EQ(body["message"].asString(), std::string("success"));
    CHECK_EQ(body["data"]["articleid"].asInt(), 7);
}

TEST_CASE(response_success_omits_data_when_null) {
    auto resp = Response::success();
    auto body = parseBody(resp);
    CHECK_EQ(body["code"].asInt(), 200);
    // Null data must not be serialized into the envelope.
    CHECK(!body.isMember("data"));
}

TEST_CASE(response_ok_carries_custom_message_and_data) {
    Json::Value data;
    data["id"] = 1;
    auto resp = Response::ok("创建成功", data);
    auto body = parseBody(resp);
    CHECK(resp->getStatusCode() == k200OK);
    CHECK_EQ(body["message"].asString(), std::string("创建成功"));
    CHECK_EQ(body["data"]["id"].asInt(), 1);
}

TEST_CASE(response_content_type_is_json) {
    auto resp = Response::success();
    // newHttpJsonResponse sets application/json.
    CHECK(resp->getContentType() == CT_APPLICATION_JSON);
}

// ---------------------------------------------------------------------------
// error shortcuts — HTTP status must mirror the semantic code
// ---------------------------------------------------------------------------

TEST_CASE(response_badRequest_is_400) {
    auto resp = Response::badRequest("参数错误");
    CHECK(resp->getStatusCode() == k400BadRequest);
    auto body = parseBody(resp);
    CHECK_EQ(body["code"].asInt(), 400);
    CHECK_EQ(body["message"].asString(), std::string("参数错误"));
    // Error responses carry no data field.
    CHECK(!body.isMember("data"));
}

TEST_CASE(response_unauthorized_is_401) {
    auto resp = Response::unauthorized("未认证");
    CHECK(resp->getStatusCode() == k401Unauthorized);
    CHECK_EQ(parseBody(resp)["code"].asInt(), 401);
}

TEST_CASE(response_forbidden_is_403) {
    auto resp = Response::forbidden("无权限");
    CHECK(resp->getStatusCode() == k403Forbidden);
    CHECK_EQ(parseBody(resp)["code"].asInt(), 403);
}

TEST_CASE(response_notFound_is_404) {
    auto resp = Response::notFound("不存在");
    CHECK(resp->getStatusCode() == k404NotFound);
    CHECK_EQ(parseBody(resp)["code"].asInt(), 404);
}

TEST_CASE(response_tooManyRequests_is_429) {
    auto resp = Response::tooManyRequests("请求过于频繁");
    CHECK(resp->getStatusCode() == k429TooManyRequests);
    CHECK_EQ(parseBody(resp)["code"].asInt(), 429);
}

TEST_CASE(response_serverError_is_500) {
    auto resp = Response::serverError("服务器错误");
    CHECK(resp->getStatusCode() == k500InternalServerError);
    CHECK_EQ(parseBody(resp)["code"].asInt(), 500);
}

// ---------------------------------------------------------------------------
// make — explicit code/status decoupling
// ---------------------------------------------------------------------------

TEST_CASE(response_make_allows_explicit_code_and_status) {
    Json::Value data;
    data["k"] = "v";
    // Body code and HTTP status are independent inputs to make().
    auto resp = Response::make(200, "partial", data, k206PartialContent);
    CHECK(resp->getStatusCode() == k206PartialContent);
    auto body = parseBody(resp);
    CHECK_EQ(body["code"].asInt(), 200);
    CHECK_EQ(body["message"].asString(), std::string("partial"));
    CHECK_EQ(body["data"]["k"].asString(), std::string("v"));
}

TEST_CASE(response_error_generic_sets_both) {
    auto resp = Response::error(418, "teapot", k418ImATeapot);
    CHECK(resp->getStatusCode() == k418ImATeapot);
    CHECK_EQ(parseBody(resp)["code"].asInt(), 418);
}
