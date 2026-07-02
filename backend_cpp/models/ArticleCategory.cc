/**
 * @file ArticleCategory.cc
 * @brief Article category/menu tree helpers.
 */

#include "ArticleCategory.h"

#include <algorithm>
#include <map>
#include <set>

namespace woniunote {
namespace models {

Json::Value ArticleCategory::toJson(bool includeArticleCount) const {
    Json::Value ret;
    ret["id"] = id;
    if (parentId.has_value()) {
        ret["parent_id"] = *parentId;
    } else {
        ret["parent_id"] = Json::nullValue;
    }
    ret["name"] = name;
    ret["sort_order"] = sortOrder;
    ret["visible"] = visible ? 1 : 0;
    if (includeArticleCount) {
        ret["article_count"] = articleCount;
    }
    return ret;
}

std::vector<ArticleCategory> legacyArticleCategories() {
    return {
        {1, std::nullopt, "交易策略", 10, true, 0},
        {101, 1, "CTA策略", 10, true, 0},
        {102, 1, "统计套利", 20, true, 0},
        {103, 1, "高频交易", 30, true, 0},
        {104, 1, "因子策略", 40, true, 0},
        {105, 1, "选股与择时", 50, true, 0},
        {106, 1, "机器学习", 60, true, 0},
        {107, 1, "深度学习", 70, true, 0},
        {2, std::nullopt, "量化框架", 20, true, 0},
        {201, 2, "backtrader", 10, true, 0},
        {202, 2, "wondertrader", 20, true, 0},
        {203, 2, "wtpy", 30, true, 0},
        {204, 2, "pyfolio", 40, true, 0},
        {205, 2, "alphalens", 50, true, 0},
        {3, std::nullopt, "投资", 30, true, 0},
        {301, 3, "股票", 10, true, 0},
        {302, 3, "期货", 20, true, 0},
        {303, 3, "期权", 30, true, 0},
        {304, 3, "外汇", 40, true, 0},
        {305, 3, "crypto", 50, true, 0},
        {306, 3, "黄金", 60, true, 0},
        {307, 3, "债券", 70, true, 0},
        {4, std::nullopt, "理财", 40, true, 0},
        {401, 4, "基金", 10, true, 0},
        {402, 4, "保险", 20, true, 0},
        {403, 4, "信托", 30, true, 0},
        {404, 4, "银行理财", 40, true, 0},
        {405, 4, "存款", 50, true, 0},
        {5, std::nullopt, "区块链与defi", 50, true, 0},
        {501, 5, "去中心化交易所", 10, true, 0},
        {502, 5, "去中心化金融", 20, true, 0},
        {503, 5, "去中心化借贷", 30, true, 0},
        {504, 5, "去中心化治理", 40, true, 0},
        {505, 5, "其他defi", 50, true, 0},
        {506, 5, "区块链", 60, true, 0},
        {507, 5, "比特币", 70, true, 0},
        {508, 5, "以太坊", 80, true, 0},
        {6, std::nullopt, "机器学习", 60, true, 0},
        {601, 6, "tensorflow", 10, true, 0},
        {602, 6, "pytorch", 20, true, 0},
        {603, 6, "keras", 30, true, 0},
        {604, 6, "scikit-learn", 40, true, 0},
        {605, 6, "机器学习与交易", 50, true, 0},
        {606, 6, "深度学习与交易", 60, true, 0},
        {7, std::nullopt, "编程", 70, true, 0},
        {701, 7, "python", 10, true, 0},
        {702, 7, "c++", 20, true, 0},
        {703, 7, "cython", 30, true, 0},
        {704, 7, "java", 40, true, 0},
        {705, 7, "javascript", 50, true, 0},
        {706, 7, "swing", 60, true, 0},
        {707, 7, "pybind11", 70, true, 0},
        {8, std::nullopt, "笔记", 80, true, 0},
        {801, 8, "幸福", 10, true, 0},
        {802, 8, "金融", 20, true, 0},
        {803, 8, "经济", 30, true, 0},
        {804, 8, "哲学", 40, true, 0},
        {805, 8, "历史", 50, true, 0},
        {806, 8, "科技", 60, true, 0},
        {807, 8, "读书笔记", 70, true, 0},
        {808, 8, "其他笔记", 80, true, 0},
        {809, 8, "个人知识库", 90, true, 0},
        {9, std::nullopt, "教程", 90, true, 0},
        {901, 9, "woniunote入门教程", 10, true, 0},
        {902, 9, "backtrader基础教程", 20, true, 0},
        {903, 9, "airflow入门教程", 30, true, 0},
        {904, 9, "arrow入门教程", 40, true, 0},
        {905, 9, "量化交易入门教程", 50, true, 0},
        {906, 9, "机器学习入门教程", 60, true, 0},
        {907, 9, "ib_tws_api入门教程", 70, true, 0}
    };
}

namespace {

bool shouldInclude(const ArticleCategory& category, bool visibleOnly) {
    return !visibleOnly || category.visible;
}

std::vector<ArticleCategory> sortedCategories(const std::vector<ArticleCategory>& categories,
                                              bool visibleOnly) {
    std::vector<ArticleCategory> filtered;
    for (const auto& category : categories) {
        if (shouldInclude(category, visibleOnly)) {
            filtered.push_back(category);
        }
    }
    std::sort(filtered.begin(), filtered.end(), [](const auto& a, const auto& b) {
        const int aParent = a.parentId.value_or(0);
        const int bParent = b.parentId.value_or(0);
        if (aParent != bParent) return aParent < bParent;
        if (a.sortOrder != b.sortOrder) return a.sortOrder < b.sortOrder;
        return a.id < b.id;
    });
    return filtered;
}

Json::Value buildTreeForParent(const std::optional<int>& parentId,
                               const std::map<int, std::vector<ArticleCategory>>& children,
                               bool includeArticleCount) {
    const int parentKey = parentId.value_or(0);
    Json::Value nodes(Json::arrayValue);
    auto found = children.find(parentKey);
    if (found == children.end()) {
        return nodes;
    }

    for (const auto& category : found->second) {
        Json::Value node = category.toJson(includeArticleCount);
        node["children"] = buildTreeForParent(category.id, children, includeArticleCount);
        nodes.append(node);
    }
    return nodes;
}

} // namespace

Json::Value articleCategoryTypeMap(const std::vector<ArticleCategory>& categories,
                                   bool visibleOnly) {
    Json::Value types(Json::objectValue);
    for (const auto& category : sortedCategories(categories, visibleOnly)) {
        types[std::to_string(category.id)] = category.name;
    }
    return types;
}

Json::Value articleCategoryFlatJson(const std::vector<ArticleCategory>& categories,
                                    bool visibleOnly,
                                    bool includeArticleCount) {
    Json::Value flat(Json::arrayValue);
    for (const auto& category : sortedCategories(categories, visibleOnly)) {
        flat.append(category.toJson(includeArticleCount));
    }
    return flat;
}

Json::Value articleCategoryTreeJson(const std::vector<ArticleCategory>& categories,
                                    bool visibleOnly,
                                    bool includeArticleCount) {
    std::map<int, std::vector<ArticleCategory>> children;
    std::set<int> includedIds;
    for (const auto& category : categories) {
        if (shouldInclude(category, visibleOnly)) {
            includedIds.insert(category.id);
        }
    }

    for (const auto& category : sortedCategories(categories, visibleOnly)) {
        std::optional<int> parentId = category.parentId;
        if (parentId.has_value() && includedIds.count(*parentId) == 0) {
            parentId = std::nullopt;
        }
        children[parentId.value_or(0)].push_back(category);
    }

    return buildTreeForParent(std::nullopt, children, includeArticleCount);
}

std::vector<int> articleCategoryPath(int categoryId,
                                     const std::vector<ArticleCategory>& categories) {
    std::map<int, ArticleCategory> byId;
    for (const auto& category : categories) {
        byId[category.id] = category;
    }

    std::vector<int> reversed;
    std::set<int> seen;
    int current = categoryId;
    while (byId.count(current) > 0 && seen.count(current) == 0) {
        seen.insert(current);
        reversed.push_back(current);
        const auto& category = byId[current];
        if (!category.parentId.has_value()) {
            break;
        }
        current = *category.parentId;
    }

    std::reverse(reversed.begin(), reversed.end());
    return reversed;
}

bool isArticleCategoryDescendant(int maybeDescendantId,
                                 int ancestorId,
                                 const std::vector<ArticleCategory>& categories) {
    if (maybeDescendantId == ancestorId) {
        return true;
    }

    std::map<int, ArticleCategory> byId;
    for (const auto& category : categories) {
        byId[category.id] = category;
    }

    std::set<int> seen;
    int current = maybeDescendantId;
    while (byId.count(current) > 0 && seen.count(current) == 0) {
        seen.insert(current);
        const auto& category = byId[current];
        if (!category.parentId.has_value()) {
            return false;
        }
        if (*category.parentId == ancestorId) {
            return true;
        }
        current = *category.parentId;
    }
    return false;
}

} // namespace models
} // namespace woniunote
