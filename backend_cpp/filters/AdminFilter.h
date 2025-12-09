/**
 * @file AdminFilter.h
 * @brief Admin Authentication Filter
 * 
 * Extends AuthFilter to require admin role.
 */

#ifndef WONIUNOTE_FILTERS_ADMIN_FILTER_H
#define WONIUNOTE_FILTERS_ADMIN_FILTER_H

#include <drogon/HttpFilter.h>

namespace woniunote {

/**
 * @class AdminFilter
 * @brief Filter that requires authenticated admin user
 */
class AdminFilter : public drogon::HttpFilter<AdminFilter>
{
public:
    void doFilter(const drogon::HttpRequestPtr& req,
                  drogon::FilterCallback&& fcb,
                  drogon::FilterChainCallback&& fccb) override;
};

} // namespace woniunote

#endif // WONIUNOTE_FILTERS_ADMIN_FILTER_H
