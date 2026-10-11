/**
 * @file ArticleCategoryService.cc
 * @brief Article category/menu management service implementation.
 */

#include "ArticleCategoryService.h"
#include "core/database.h"
#include "core/logger.h"
#include "core/response.h"
#include "models/ArticleCategory.h"
#include <drogon/HttpResponse.h>
#include <algorithm>
#include <cctype>
#include <iterator>
#include <optional>
#include <sstream>
#include <vector>

using namespace drogon;

namespace woniunote {
namespace services {

namespace {

std::string trimCopy(const std::string& value) {
    auto begin = std::find_if_not(value.begin(), value.end(), [](unsigned char ch) {
        return std::isspace(ch);
    });
    auto end = std::find_if_not(value.rbegin(), value.rend(), [](unsigned char ch) {
        return std::isspace(ch);
    }).base();
    if (begin >= end) return "";
    return std::string(begin, end);
}

models::ArticleCategory articleCategoryFromRow(const orm::Row& row) {
    models::ArticleCategory category;
    if (!row["id"].isNull()) category.id = row["id"].as<int>();
    if (!row["parent_id"].isNull()) category.parentId = row["parent_id"].as<int>();
    if (!row["name"].isNull()) category.name = row["name"].as<std::string>();
    if (!row["sort_order"].isNull()) category.sortOrder = row["sort_order"].as<int>();
    if (!row["visible"].isNull()) category.visible = row["visible"].as<int>() != 0;
    if (!row["article_count"].isNull()) category.articleCount = row["article_count"].as<int>();
    return category;
}

std::vector<models::ArticleCategory> articleCategoriesFromResult(const orm::Result& result) {
    std::vector<models::ArticleCategory> categories;
    categories.reserve(result.size());
    std::transform(result.begin(), result.end(), std::back_inserter(categories),
                   [](const orm::Row& row) { return articleCategoryFromRow(row); });
    return categories;
}

Json::Value articleCategoryResponseData(const std::vector<models::ArticleCategory>& categories,
                                        bool visibleOnly,
                                        bool includeArticleCount) {
    Json::Value data;
    data["types"] = models::articleCategoryTypeMap(categories, visibleOnly);
    data["flat"] = models::articleCategoryFlatJson(categories, visibleOnly, includeArticleCount);
    data["tree"] = models::articleCategoryTreeJson(categories, visibleOnly, includeArticleCount);
    return data;
}

const models::ArticleCategory* findCategory(const std::vector<models::ArticleCategory>& categories,
                                            int categoryId) {
    auto found = std::find_if(categories.begin(), categories.end(), [categoryId](const auto& category) {
        return category.id == categoryId;
    });
    return found == categories.end() ? nullptr : &(*found);
}

std::optional<int> parseOptionalParent(const Json::Value& json,
                                       const std::optional<int>& fallback) {
    if (!json.isMember("parent_id")) {
        return fallback;
    }
    if (json["parent_id"].isNull() || json["parent_id"].asInt() <= 0) {
        return std::nullopt;
    }
    return json["parent_id"].asInt();
}

void checkDuplicateSibling(const DbClientPtr& dbClient,
                           const std::string& name,
                           const std::optional<int>& parentId,
                           int excludeId,
                           std::function<void(bool)> onDone,
                           std::function<void(const orm::DrogonDbException&)> onError) {
    if (parentId.has_value()) {
        dbClient->execSqlAsync(
            "SELECT id FROM article_category WHERE parent_id = ? AND name = ? AND id <> ? LIMIT 1",
            [onDone](const orm::Result& result) { onDone(result.size() > 0); },
            std::move(onError),
            *parentId, name, excludeId
        );
        return;
    }

    dbClient->execSqlAsync(
        "SELECT id FROM article_category WHERE parent_id IS NULL AND name = ? AND id <> ? LIMIT 1",
        [onDone](const orm::Result& result) { onDone(result.size() > 0); },
        std::move(onError),
        name, excludeId
    );
}

void updateCategoryParentAndFields(const std::shared_ptr<Transaction>& trans,
                                   const std::optional<int>& parentId,
                                   const std::string& name,
                                   int sortOrder,
                                   bool visible,
                                   int categoryId,
                                   std::function<void(const orm::Result&)> onDone,
                                   std::function<void(const orm::DrogonDbException&)> onError) {
    if (parentId.has_value()) {
        trans->execSqlAsync(
            "UPDATE article_category SET parent_id = ?, name = ?, sort_order = ?, visible = ?, updatetime = NOW() WHERE id = ?",
            std::move(onDone),
            std::move(onError),
            *parentId, name, sortOrder, visible ? 1 : 0, categoryId
        );
        return;
    }

    trans->execSqlAsync(
        "UPDATE article_category SET parent_id = NULL, name = ?, sort_order = ?, visible = ?, updatetime = NOW() WHERE id = ?",
        std::move(onDone),
        std::move(onError),
        name, sortOrder, visible ? 1 : 0, categoryId
    );
}

const std::string ARTICLE_CATEGORY_SELECT_SQL =
    "SELECT c.id, c.parent_id, c.name, c.sort_order, c.visible, COUNT(a.articleid) AS article_count "
    "FROM article_category c "
    "LEFT JOIN article a ON a.type = c.id "
    "GROUP BY c.id, c.parent_id, c.name, c.sort_order, c.visible "
    "ORDER BY COALESCE(c.parent_id, 0), c.sort_order, c.id";

const std::string ARTICLE_CATEGORY_CREATE_SQL =
    "CREATE TABLE IF NOT EXISTS article_category ("
    "id INT NOT NULL AUTO_INCREMENT,"
    "parent_id INT DEFAULT NULL COMMENT 'Parent category ID; NULL for root nodes',"
    "name VARCHAR(64) NOT NULL COMMENT 'Category/menu node name',"
    "sort_order INT NOT NULL DEFAULT 0 COMMENT 'Display order among siblings',"
    "visible TINYINT(1) NOT NULL DEFAULT 1 COMMENT 'Whether shown in public navigation',"
    "createtime DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time',"
    "updatetime DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update time',"
    "PRIMARY KEY (id),"
    "KEY idx_parent_sort (parent_id, visible, sort_order, id),"
    "KEY idx_visible_sort (visible, sort_order, id),"
    "CONSTRAINT fk_article_category_parent FOREIGN KEY (parent_id) "
    "REFERENCES article_category (id) ON DELETE SET NULL"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci "
    "COMMENT='Article category/menu tree'";

std::string sqlStringLiteral(const std::string& value) {
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

std::string legacyCategoryInsertSql(bool rootOnly) {
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

void bootstrapArticleCategoryTable(const DbClientPtr& dbClient,
                                   std::function<void()> onDone,
                                   std::function<void(const orm::DrogonDbException&)> onError) {
    dbClient->execSqlAsync(
        ARTICLE_CATEGORY_CREATE_SQL,
        [dbClient, onDone, onError](const orm::Result&) {
            dbClient->execSqlAsync(
                legacyCategoryInsertSql(true),
                [dbClient, onDone, onError](const orm::Result&) {
                    dbClient->execSqlAsync(
                        legacyCategoryInsertSql(false),
                        [onDone](const orm::Result&) { onDone(); },
                        onError
                    );
                },
                onError
            );
        },
        onError
    );
}

void applyLegacyArticleCounts(std::vector<models::ArticleCategory>& categories,
                              const orm::Result& result) {
    for (const auto& row : result) {
        if (row["type"].isNull() || row["article_count"].isNull()) {
            continue;
        }
        const int type = row["type"].as<int>();
        const int articleCount = row["article_count"].as<int>();
        auto found = std::find_if(categories.begin(), categories.end(),
                                  [type](const auto& category) { return category.id == type; });
        if (found != categories.end()) {
            found->articleCount = articleCount;
        }
    }
}

void respondWithLegacyArticleCategories(const DbClientPtr& dbClient,
                                        std::function<void(const HttpResponsePtr&)> callback) {
    dbClient->execSqlAsync(
        "SELECT type, COUNT(*) AS article_count FROM article GROUP BY type",
        [callback](const orm::Result& result) {
            auto categories = models::legacyArticleCategories();
            applyLegacyArticleCounts(categories, result);
            callback(Response::success(articleCategoryResponseData(categories, false, true)));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::warning("[Admin] Legacy article category counts unavailable: " + std::string(e.base().what()));
            callback(Response::success(articleCategoryResponseData(
                models::legacyArticleCategories(), false, true
            )));
        }
    );
}

} // namespace

void ArticleCategoryService::listCategories(ArticleCategoryService::ResponseCallback callback)
{
    auto dbClient = Database::getClient();

    auto sendCategories = [callback](const orm::Result& result) {
        callback(Response::success(articleCategoryResponseData(
            articleCategoriesFromResult(result), false, true
        )));
    };

    auto bootstrapAndReload = [callback, dbClient, sendCategories]() {
        bootstrapArticleCategoryTable(
            dbClient,
            [callback, dbClient, sendCategories]() {
                dbClient->execSqlAsync(
                    ARTICLE_CATEGORY_SELECT_SQL,
                    sendCategories,
                    [callback, dbClient](const orm::DrogonDbException& e) {
                        Logger::warning("[Admin] Reload article categories after bootstrap failed: " + std::string(e.base().what()));
                        respondWithLegacyArticleCategories(dbClient, callback);
                    }
                );
            },
            [callback, dbClient](const orm::DrogonDbException& e) {
                Logger::warning("[Admin] Bootstrap article categories failed: " + std::string(e.base().what()));
                respondWithLegacyArticleCategories(dbClient, callback);
            }
        );
    };

    dbClient->execSqlAsync(
        ARTICLE_CATEGORY_SELECT_SQL,
        [sendCategories, bootstrapAndReload](const orm::Result& result) {
            if (result.size() == 0) {
                bootstrapAndReload();
                return;
            }
            sendCategories(result);
        },
        [bootstrapAndReload](const orm::DrogonDbException& e) {
            Logger::warning("[Admin] List article categories needs bootstrap: " + std::string(e.base().what()));
            bootstrapAndReload();
        }
    );
}

void ArticleCategoryService::createCategory(const Json::Value& json,
                                            ArticleCategoryService::ResponseCallback callback)
{
    std::string name = trimCopy(json["name"].asString());
    if (name.empty()) {
        callback(Response::badRequest("分类名称不能为空"));
        return;
    }
    auto parentId = parseOptionalParent(json, std::nullopt);
    int sortOrder = json.get("sort_order", 0).asInt();
    bool visible = json.get("visible", 1).asInt() != 0;
    auto dbClient = Database::getClient();

    auto insertCategory = [callback, dbClient, name, parentId, sortOrder, visible]() {
        checkDuplicateSibling(
            dbClient,
            name,
            parentId,
            0,
            [callback, dbClient, name, parentId, sortOrder, visible](bool duplicate) {
                if (duplicate) {
                    callback(Response::badRequest("同级分类名称已存在"));
                    return;
                }

                if (parentId.has_value()) {
                    dbClient->execSqlAsync(
                        "INSERT INTO article_category (parent_id, name, sort_order, visible, createtime, updatetime) "
                        "VALUES (?, ?, ?, ?, NOW(), NOW())",
                        [callback](const orm::Result& result) {
                            Json::Value data;
                            data["id"] = static_cast<Json::Int64>(result.insertId());
                            callback(Response::ok("创建成功", data));
                        },
                        [callback](const orm::DrogonDbException& e) {
                            Logger::error("[Admin] Create article category failed: " + std::string(e.base().what()));
                            callback(Response::serverError("创建失败"));
                        },
                        *parentId, name, sortOrder, visible ? 1 : 0
                    );
                    return;
                }

                dbClient->execSqlAsync(
                    "INSERT INTO article_category (parent_id, name, sort_order, visible, createtime, updatetime) "
                    "VALUES (NULL, ?, ?, ?, NOW(), NOW())",
                    [callback](const orm::Result& result) {
                        Json::Value data;
                        data["id"] = static_cast<Json::Int64>(result.insertId());
                        callback(Response::ok("创建成功", data));
                    },
                    [callback](const orm::DrogonDbException& e) {
                        Logger::error("[Admin] Create article category failed: " + std::string(e.base().what()));
                        callback(Response::serverError("创建失败"));
                    },
                    name, sortOrder, visible ? 1 : 0
                );
            },
            [callback](const orm::DrogonDbException& e) {
                Logger::error("[Admin] Duplicate category check failed: " + std::string(e.base().what()));
                callback(Response::serverError("数据库错误"));
            }
        );
    };

    if (!parentId.has_value()) {
        insertCategory();
        return;
    }

    dbClient->execSqlAsync(
        "SELECT id FROM article_category WHERE id = ? LIMIT 1",
        [callback, insertCategory](const orm::Result& result) {
            if (result.size() == 0) {
                callback(Response::badRequest("父分类不存在"));
                return;
            }
            insertCategory();
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[Admin] Parent category lookup failed: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        },
        *parentId
    );
}

void ArticleCategoryService::updateCategory(int64_t id,
                                            const Json::Value& json,
                                            ArticleCategoryService::ResponseCallback callback)
{
    auto dbClient = Database::getClient();
    dbClient->execSqlAsync(
        ARTICLE_CATEGORY_SELECT_SQL,
        [callback, json, dbClient, id](const orm::Result& result) {
            auto categories = articleCategoriesFromResult(result);
            const auto* current = findCategory(categories, static_cast<int>(id));
            if (!current) {
                callback(Response::notFound("分类不存在"));
                return;
            }

            std::string name = json.isMember("name") ? trimCopy(json["name"].asString()) : current->name;
            if (name.empty()) {
                callback(Response::badRequest("分类名称不能为空"));
                return;
            }

            auto parentId = parseOptionalParent(json, current->parentId);
            int sortOrder = json.isMember("sort_order") ? json["sort_order"].asInt() : current->sortOrder;
            bool visible = json.isMember("visible") ? (json["visible"].asInt() != 0) : current->visible;

            if (parentId.has_value()) {
                if (*parentId == id) {
                    callback(Response::badRequest("父分类不能是自身"));
                    return;
                }
                if (!findCategory(categories, *parentId)) {
                    callback(Response::badRequest("父分类不存在"));
                    return;
                }
                if (models::isArticleCategoryDescendant(*parentId, static_cast<int>(id), categories)) {
                    callback(Response::badRequest("不能移动到自己的子分类下"));
                    return;
                }
            }

            checkDuplicateSibling(
                dbClient,
                name,
                parentId,
                static_cast<int>(id),
                [callback, id, parentId, name, sortOrder, visible](bool duplicate) {
                    if (duplicate) {
                        callback(Response::badRequest("同级分类名称已存在"));
                        return;
                    }

                    Database::beginTransaction(
                        [callback, id, parentId, name, sortOrder, visible](const std::shared_ptr<Transaction>& trans) {
                            if (!trans) {
                                callback(Response::serverError("无法开启事务"));
                                return;
                            }

                            updateCategoryParentAndFields(
                                trans,
                                parentId,
                                name,
                                sortOrder,
                                visible,
                                static_cast<int>(id),
                                [callback, id](const orm::Result&) {
                                    Json::Value data;
                                    data["id"] = static_cast<Json::Int64>(id);
                                    callback(Response::ok("更新成功", data));
                                },
                                [callback](const orm::DrogonDbException& e) {
                                    Logger::error("[Admin] Update article category failed: " + std::string(e.base().what()));
                                    callback(Response::serverError("更新失败"));
                                }
                            );
                        }
                    );
                },
                [callback](const orm::DrogonDbException& e) {
                    Logger::error("[Admin] Duplicate category check failed: " + std::string(e.base().what()));
                    callback(Response::serverError("数据库错误"));
                }
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[Admin] Load article categories failed: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        }
    );
}

void ArticleCategoryService::deleteCategory(int64_t id,
                                            const DeleteOptions& options,
                                            ArticleCategoryService::ResponseCallback callback)
{
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        ARTICLE_CATEGORY_SELECT_SQL,
        [callback, id, options](const orm::Result& result) {
            auto categories = articleCategoriesFromResult(result);
            const auto* current = findCategory(categories, static_cast<int>(id));
            if (!current) {
                callback(Response::notFound("分类不存在"));
                return;
            }

            if (options.moveTargetInvalid) {
                callback(Response::badRequest("迁移目标分类无效"));
                return;
            }
            int moveArticlesTo = options.moveArticlesTo;

            if (current->articleCount > 0) {
                if (moveArticlesTo <= 0) {
                    Json::Value data;
                    data["article_count"] = current->articleCount;
                    callback(Response::make(400, "删除前请选择文章迁移目标分类", data, k400BadRequest));
                    return;
                }
                if (moveArticlesTo == id || !findCategory(categories, moveArticlesTo)) {
                    callback(Response::badRequest("迁移目标分类不存在"));
                    return;
                }
                if (models::isArticleCategoryDescendant(moveArticlesTo, static_cast<int>(id), categories)) {
                    callback(Response::badRequest("迁移目标不能是待删除分类的子分类"));
                    return;
                }
            }

            auto deletedParentId = current->parentId;
            const bool shouldMoveArticles = current->articleCount > 0;

            Database::beginTransaction(
                [callback, id, moveArticlesTo, deletedParentId, shouldMoveArticles](const std::shared_ptr<Transaction>& trans) {
                    if (!trans) {
                        callback(Response::serverError("无法开启事务"));
                        return;
                    }

                    auto reparentChildren = [callback, trans, id, deletedParentId]() {
                        auto deleteCategory = [callback, trans, id](const orm::Result&) {
                            trans->execSqlAsync(
                                "DELETE FROM article_category WHERE id = ?",
                                [callback, id](const orm::Result&) {
                                    Json::Value data;
                                    data["id"] = static_cast<Json::Int64>(id);
                                    callback(Response::ok("删除成功", data));
                                },
                                [callback](const orm::DrogonDbException& e) {
                                    Logger::error("[Admin] Delete article category failed: " + std::string(e.base().what()));
                                    callback(Response::serverError("删除失败"));
                                },
                                id
                            );
                        };

                        if (deletedParentId.has_value()) {
                            trans->execSqlAsync(
                                "UPDATE article_category SET parent_id = ?, updatetime = NOW() WHERE parent_id = ?",
                                deleteCategory,
                                [callback](const orm::DrogonDbException& e) {
                                    Logger::error("[Admin] Reparent child categories failed: " + std::string(e.base().what()));
                                    callback(Response::serverError("删除失败"));
                                },
                                *deletedParentId, id
                            );
                            return;
                        }

                        trans->execSqlAsync(
                            "UPDATE article_category SET parent_id = NULL, updatetime = NOW() WHERE parent_id = ?",
                            deleteCategory,
                            [callback](const orm::DrogonDbException& e) {
                                Logger::error("[Admin] Reparent child categories failed: " + std::string(e.base().what()));
                                callback(Response::serverError("删除失败"));
                            },
                            id
                        );
                    };

                    if (shouldMoveArticles) {
                        trans->execSqlAsync(
                            "UPDATE article SET type = ?, updatetime = NOW() WHERE type = ?",
                            [reparentChildren](const orm::Result&) { reparentChildren(); },
                            [callback](const orm::DrogonDbException& e) {
                                Logger::error("[Admin] Move articles before category delete failed: " + std::string(e.base().what()));
                                callback(Response::serverError("删除失败"));
                            },
                            moveArticlesTo, id
                        );
                        return;
                    }

                    reparentChildren();
                }
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("[Admin] Load article categories failed: " + std::string(e.base().what()));
            callback(Response::serverError("数据库错误"));
        }
    );
}

} // namespace services
} // namespace woniunote
