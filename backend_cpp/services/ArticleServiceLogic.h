/**
 * @file ArticleServiceLogic.h
 * @brief Pure (DB-free) helpers behind the article category/author services.
 *
 * These helpers used to live in the anonymous namespaces of
 * ArticleCategoryService.cc / ArticleAuthorService.cc. They are header-only so
 * the unit tests (tests/test_services.cc) can exercise them without a live
 * DbClient: parameter validation, name normalization, pagination arithmetic,
 * SQL assembly and JSON/DTO assembly.
 *
 * The bodies are moved verbatim from the service translation units; the
 * behavior (including produced SQL strings) must stay byte-for-byte identical.
 * Anything that touches a live database stays in the service .cc files.
 */

#ifndef WONIUNOTE_SERVICES_ARTICLE_SERVICE_LOGIC_H
#define WONIUNOTE_SERVICES_ARTICLE_SERVICE_LOGIC_H

#include "models/ArticleCategory.h"

#include <json/json.h>
#include <algorithm>
#include <cctype>
#include <optional>
#include <sstream>
#include <string>
#include <vector>

namespace woniunote {
namespace services {
namespace logic {

// ---------------------------------------------------------------------------
// Name / parameter validation
// ---------------------------------------------------------------------------

/// Trims leading and trailing whitespace (std::isspace); an all-whitespace
/// input collapses to the empty string.
inline std::string trimCopy(const std::string& value) {
    auto begin = std::find_if_not(value.begin(), value.end(), [](unsigned char ch) {
        return std::isspace(ch);
    });
    auto end = std::find_if_not(value.rbegin(), value.rend(), [](unsigned char ch) {
        return std::isspace(ch);
    }).base();
    if (begin >= end) return "";
    return std::string(begin, end);
}

/// Parses the optional "parent_id" member: absent -> fallback, null/<=0 ->
/// nullopt (root node), otherwise the provided id.
inline std::optional<int> parseOptionalParent(const Json::Value& json,
                                              const std::optional<int>& fallback) {
    if (!json.isMember("parent_id")) {
        return fallback;
    }
    if (json["parent_id"].isNull() || json["parent_id"].asInt() <= 0) {
        return std::nullopt;
    }
    return json["parent_id"].asInt();
}

/// Looks up a category by id; returns nullptr when absent.
inline const models::ArticleCategory* findCategory(
    const std::vector<models::ArticleCategory>& categories,
    int categoryId) {
    auto found = std::find_if(categories.begin(), categories.end(), [categoryId](const auto& category) {
        return category.id == categoryId;
    });
    return found == categories.end() ? nullptr : &(*found);
}

/// True when `type` matches a visible entry of the built-in legacy map. Used as
/// the fallback validation path when the article_category table is unavailable.
inline bool legacyCategoryExists(int type) {
    const auto categories = models::legacyArticleCategories();
    return std::any_of(categories.begin(), categories.end(), [type](const auto& category) {
        return category.id == type && category.visible;
    });
}

// ---------------------------------------------------------------------------
// Pagination arithmetic
// ---------------------------------------------------------------------------

/// Zero-based row offset for a 1-based page number.
inline int pageOffset(int page, int pageSize) {
    return (page - 1) * pageSize;
}

/// Number of pages needed to hold `total` rows of `pageSize` (0 when total=0).
inline int totalPages(int total, int pageSize) {
    return (total + pageSize - 1) / pageSize;
}

// ---------------------------------------------------------------------------
// SQL assembly
// ---------------------------------------------------------------------------

/// Wraps `value` in single quotes, doubling embedded quotes and backslashes so
/// the literal is safe to inline into a generated statement.
inline std::string sqlStringLiteral(const std::string& value) {
    std::string escaped;
    escaped.reserve(value.size() + 2);
    escaped.push_back('\'');
    for (char ch : value) {
        if (ch == '\'' || ch == '\\') {
            escaped.push_back(ch);
        }
        escaped.push_back(ch);
    }
    escaped.push_back('\'');
    return escaped;
}

/// INSERT IGNORE statement seeding the article_category table from the legacy
/// built-in map; `rootOnly` selects root nodes or child nodes respectively.
inline std::string legacyCategoryInsertSql(bool rootOnly) {
    std::ostringstream sql;
    sql << "INSERT IGNORE INTO article_category "
        << "(id, parent_id, name, sort_order, visible) VALUES ";

    bool first = true;
    for (const auto& category : models::legacyArticleCategories()) {
        const bool isRoot = !category.parentId.has_value();
        if (isRoot != rootOnly) {
            continue;
        }
        if (!first) {
            sql << ",";
        }
        first = false;
        sql << "(" << category.id << ",";
        if (category.parentId.has_value()) {
            sql << *category.parentId;
        } else {
            sql << "NULL";
        }
        sql << "," << sqlStringLiteral(category.name)
            << "," << category.sortOrder
            << "," << (category.visible ? 1 : 0)
            << ")";
    }
    return sql.str();
}

/// COUNT(*) query for the author's own article list; `type > 0` adds the
/// category filter.
inline std::string buildMyArticlesCountSql(int type) {
    std::string countSql = "SELECT COUNT(*) AS total FROM article a WHERE a.userid = ?";
    if (type > 0) {
        countSql += " AND a.type = ?";
    }
    return countSql;
}

/// Data query for the author's own article list, including the LIMIT/OFFSET
/// tail (pageSize/offset are already clamped by the caller).
inline std::string buildMyArticlesDataSql(int type, int pageSize, int offset) {
    std::string dataSql = "SELECT a.*, u.nickname FROM article a LEFT JOIN users u ON a.userid = u.userid "
                          "WHERE a.userid = ?";
    if (type > 0) {
        dataSql += " AND a.type = ?";
    }
    dataSql += " ORDER BY a.createtime DESC LIMIT " + std::to_string(pageSize) +
               " OFFSET " + std::to_string(offset);
    return dataSql;
}

// ---------------------------------------------------------------------------
// JSON / DTO assembly
// ---------------------------------------------------------------------------

/// Builds the {types, flat, tree} payload shared by every category response.
inline Json::Value articleCategoryResponseData(const std::vector<models::ArticleCategory>& categories,
                                               bool visibleOnly,
                                               bool includeArticleCount) {
    Json::Value data;
    data["types"] = models::articleCategoryTypeMap(categories, visibleOnly);
    data["flat"] = models::articleCategoryFlatJson(categories, visibleOnly, includeArticleCount);
    data["tree"] = models::articleCategoryTreeJson(categories, visibleOnly, includeArticleCount);
    return data;
}

} // namespace logic
} // namespace services
} // namespace woniunote

#endif // WONIUNOTE_SERVICES_ARTICLE_SERVICE_LOGIC_H
