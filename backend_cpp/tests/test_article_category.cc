#include "test_framework.h"
#include "models/ArticleCategory.h"

#include <vector>

using namespace woniunote::models;

namespace {

std::vector<ArticleCategory> sampleCategories() {
    return {
        {2, std::nullopt, "B", 20, true, 5},
        {1, std::nullopt, "A", 10, true, 3},
        {102, 1, "A-2", 20, false, 1},
        {101, 1, "A-1", 10, true, 2},
        {201, 2, "B-1", 10, true, 0},
        {301, 102, "Hidden child promoted", 10, true, 0}
    };
}

} // namespace

TEST_CASE(article_category_type_map_preserves_visible_names) {
    auto types = articleCategoryTypeMap(sampleCategories(), true);
    CHECK_EQ(types["1"].asString(), std::string("A"));
    CHECK_EQ(types["101"].asString(), std::string("A-1"));
    CHECK(!types.isMember("102"));
}

TEST_CASE(article_category_tree_orders_nodes_and_filters_hidden) {
    auto tree = articleCategoryTreeJson(sampleCategories(), true, true);
    CHECK_EQ(tree.size(), 3U);
    CHECK_EQ(tree[0]["id"].asInt(), 1);
    CHECK_EQ(tree[0]["children"][0]["id"].asInt(), 101);
    CHECK_EQ(tree[1]["id"].asInt(), 2);
    CHECK_EQ(tree[1]["children"][0]["id"].asInt(), 201);
}

TEST_CASE(article_category_tree_promotes_children_when_parent_hidden) {
    auto tree = articleCategoryTreeJson(sampleCategories(), true, true);
    bool foundPromoted = false;
    for (const auto& node : tree) {
        if (node["id"].asInt() == 301) {
            foundPromoted = true;
        }
    }
    CHECK(foundPromoted);
}

TEST_CASE(article_category_path_resolves_ancestor_chain) {
    auto path = articleCategoryPath(301, sampleCategories());
    CHECK_EQ(path.size(), 3U);
    CHECK_EQ(path[0], 1);
    CHECK_EQ(path[1], 102);
    CHECK_EQ(path[2], 301);
}

TEST_CASE(article_category_descendant_detects_cycles_and_self) {
    auto categories = sampleCategories();
    CHECK(isArticleCategoryDescendant(301, 1, categories));
    CHECK(isArticleCategoryDescendant(1, 1, categories));
    CHECK(!isArticleCategoryDescendant(201, 1, categories));
}
