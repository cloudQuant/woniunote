/**
 * @file ArticleAuthorService.h
 * @brief Own-article management service.
 *
 * Owns the SQL construction, ownership checks and validation logic for the
 * endpoints where the authenticated user manages their own articles (list,
 * drafts, create, update, category change, delete) so controllers stay thin.
 * All methods respond through the unified core/response.h envelope.
 */

#ifndef WONIUNOTE_SERVICES_ARTICLE_AUTHOR_SERVICE_H
#define WONIUNOTE_SERVICES_ARTICLE_AUTHOR_SERVICE_H

#include <drogon/HttpResponse.h>
#include <json/json.h>
#include <functional>
#include <string>

namespace woniunote {
namespace services {

class ArticleAuthorService
{
public:
    using ResponseCallback = std::function<void(const drogon::HttpResponsePtr&)>;

    // Lists the user's own articles. `page`/`pageSize` are pre-clamped by the
    // caller; `type` filters by category (0 = all categories).
    static void listMyArticles(const std::string& userId,
                               int page,
                               int pageSize,
                               int type,
                               ResponseCallback callback);

    // Lists the user's own drafts.
    static void listMyDrafts(const std::string& userId, ResponseCallback callback);

    // Creates an article. `json` must contain "headline" and "type" members;
    // optional "content"/"thumbnail"/"credit"/"drafted" fields are honored.
    static void createArticle(const std::string& userId,
                              const Json::Value& json,
                              ResponseCallback callback);

    // Updates the article owned by the user. `json` may carry
    // "headline"/"content"/"type" with the same defaults as before.
    static void updateArticle(const std::string& userId,
                              int64_t id,
                              const Json::Value& json,
                              ResponseCallback callback);

    // Moves the user's own article to another category; `type` must be > 0.
    static void updateArticleType(const std::string& userId,
                                  int64_t id,
                                  int type,
                                  ResponseCallback callback);

    // Deletes the article owned by the user.
    static void removeArticle(const std::string& userId,
                              int64_t id,
                              ResponseCallback callback);
};

} // namespace services
} // namespace woniunote

#endif // WONIUNOTE_SERVICES_ARTICLE_AUTHOR_SERVICE_H
