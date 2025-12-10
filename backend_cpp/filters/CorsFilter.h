/**
 * @file CorsFilter.h
 * @brief CORS Filter for handling cross-origin requests
 */

#pragma once

#include <drogon/HttpFilter.h>

namespace woniunote {

class CorsFilter : public drogon::HttpFilter<CorsFilter>
{
public:
    void doFilter(const drogon::HttpRequestPtr& req,
                  drogon::FilterCallback&& callback,
                  drogon::FilterChainCallback&& chainCallback) override;
};

} // namespace woniunote
