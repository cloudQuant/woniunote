/**
 * @file RateLimitFilter.h
 * @brief Rate Limiting Filter
 * 
 * HTTP filter that implements token bucket rate limiting using Redis.
 */

#ifndef WONIUNOTE_FILTERS_RATE_LIMIT_FILTER_H
#define WONIUNOTE_FILTERS_RATE_LIMIT_FILTER_H

#include <drogon/HttpFilter.h>

namespace woniunote {

/**
 * @class RateLimitFilter
 * @brief Token bucket rate limiting filter
 * 
 * Limits requests per IP address using Redis for distributed counting.
 */
class RateLimitFilter : public drogon::HttpFilter<RateLimitFilter>
{
public:
    RateLimitFilter() = default;

    void doFilter(const drogon::HttpRequestPtr& req,
                  drogon::FilterCallback&& callback,
                  drogon::FilterChainCallback&& chainCallback) override;

private:
    // Default limits
    static constexpr int REQUESTS_PER_MINUTE = 60;
    static constexpr int BURST_SIZE = 10;
};

} // namespace woniunote

#endif // WONIUNOTE_FILTERS_RATE_LIMIT_FILTER_H
