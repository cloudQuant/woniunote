/**
 * @file AuthFilter.h
 * @brief JWT Authentication Filter
 * 
 * HTTP filter that validates JWT tokens for protected routes.
 */

#ifndef WONIUNOTE_FILTERS_AUTH_FILTER_H
#define WONIUNOTE_FILTERS_AUTH_FILTER_H

#include <drogon/HttpFilter.h>
#include <string>

namespace woniunote {

/**
 * @class AuthFilter
 * @brief JWT authentication filter
 * 
 * Validates the Authorization header and extracts user ID.
 * Use with ADD_FILTER(woniunote::AuthFilter) macro on protected endpoints.
 */
class AuthFilter : public drogon::HttpFilter<AuthFilter>
{
public:
    AuthFilter() = default;

    /**
     * @brief Filter incoming requests for valid JWT
     * @param req HTTP request
     * @param callback Filter callback to continue or reject
     * @param chainCallback Callback to continue the filter chain
     */
    void doFilter(const drogon::HttpRequestPtr& req,
                  drogon::FilterCallback&& callback,
                  drogon::FilterChainCallback&& chainCallback) override;
};

/**
 * @class OptionalAuthFilter
 * @brief Optional JWT authentication filter
 * 
 * Extracts user ID if token is present, but allows anonymous access.
 */
class OptionalAuthFilter : public drogon::HttpFilter<OptionalAuthFilter>
{
public:
    OptionalAuthFilter() = default;

    void doFilter(const drogon::HttpRequestPtr& req,
                  drogon::FilterCallback&& callback,
                  drogon::FilterChainCallback&& chainCallback) override;
};

} // namespace woniunote

#endif // WONIUNOTE_FILTERS_AUTH_FILTER_H
