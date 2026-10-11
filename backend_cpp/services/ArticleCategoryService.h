/**
 * @file ArticleCategoryService.h
 * @brief Article category/menu management service.
 *
 * Owns the SQL construction, bootstrap and validation logic behind the admin
 * article category endpoints so controllers stay thin. All methods respond
 * through the unified core/response.h envelope.
 */

#ifndef WONIUNOTE_SERVICES_ARTICLE_CATEGORY_SERVICE_H
#define WONIUNOTE_SERVICES_ARTICLE_CATEGORY_SERVICE_H

#include <drogon/HttpResponse.h>
#include <json/json.h>
#include <functional>

namespace woniunote {
namespace services {

class ArticleCategoryService
{
public:
    using ResponseCallback = std::function<void(const drogon::HttpResponsePtr&)>;

    // Parsed delete options (from the move_articles_to query parameter or
    // JSON body). `moveArticlesTo` is the target category for the deleted
    // category's articles (0 = not provided); `moveTargetInvalid` marks a
    // provided but malformed value.
    struct DeleteOptions {
        int moveArticlesTo = 0;
        bool moveTargetInvalid = false;
    };

    // Lists every category. Bootstraps the article_category table when it is
    // missing and falls back to the legacy built-in category map when the
    // table is unavailable.
    static void listCategories(ResponseCallback callback);

    // Creates a category. `json` must contain a "name" member; optional
    // "parent_id"/"sort_order"/"visible" fields are honored.
    static void createCategory(const Json::Value& json, ResponseCallback callback);

    // Updates the category identified by `id` with the fields present in
    // `json` (name/sort_order/visible/parent_id).
    static void updateCategory(int64_t id, const Json::Value& json, ResponseCallback callback);

    // Deletes the category identified by `id`, relocating its articles and
    // child categories according to `options`.
    static void deleteCategory(int64_t id, const DeleteOptions& options, ResponseCallback callback);
};

} // namespace services
} // namespace woniunote

#endif // WONIUNOTE_SERVICES_ARTICLE_CATEGORY_SERVICE_H
