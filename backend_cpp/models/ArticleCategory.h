/**
 * @file ArticleCategory.h
 * @brief Article category/menu tree helpers.
 */

#ifndef WONIUNOTE_MODELS_ARTICLE_CATEGORY_H
#define WONIUNOTE_MODELS_ARTICLE_CATEGORY_H

#include <json/json.h>
#include <optional>
#include <string>
#include <vector>

namespace woniunote {
namespace models {

struct ArticleCategory {
    int id = 0;
    std::optional<int> parentId;
    std::string name;
    int sortOrder = 0;
    bool visible = true;
    int articleCount = 0;

    Json::Value toJson(bool includeArticleCount = true) const;
};

std::vector<ArticleCategory> legacyArticleCategories();
Json::Value articleCategoryTypeMap(const std::vector<ArticleCategory>& categories,
                                   bool visibleOnly);
Json::Value articleCategoryFlatJson(const std::vector<ArticleCategory>& categories,
                                    bool visibleOnly,
                                    bool includeArticleCount);
Json::Value articleCategoryTreeJson(const std::vector<ArticleCategory>& categories,
                                    bool visibleOnly,
                                    bool includeArticleCount);
std::vector<int> articleCategoryPath(int categoryId,
                                     const std::vector<ArticleCategory>& categories);
bool isArticleCategoryDescendant(int maybeDescendantId,
                                 int ancestorId,
                                 const std::vector<ArticleCategory>& categories);

} // namespace models
} // namespace woniunote

#endif // WONIUNOTE_MODELS_ARTICLE_CATEGORY_H
