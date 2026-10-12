/**
 * @file test_services.cc
 * @brief Unit tests for the DB-free service-layer logic
 *        (services/ArticleServiceLogic.h).
 *
 * The article category/author services are thin wrappers around Drogon DB
 * callbacks; everything that does not need a live DbClient (name validation,
 * parent parsing, pagination arithmetic, SQL assembly and the category JSON
 * payload) was moved verbatim into ArticleServiceLogic.h. These tests pin that
 * behavior — in particular the exact SQL strings, which the DB-backed service
 * paths embed unchanged.
 */

#include "test_framework.h"
#include "services/ArticleServiceLogic.h"

#include <json/json.h>
#include <cstddef>
#include <memory>
#include <optional>
#include <string>
#include <vector>

using namespace woniunote::models;
using namespace woniunote::services::logic;

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

std::size_t countOccurrences(const std::string& haystack, const std::string& needle) {
    if (needle.empty()) return 0;
    std::size_t count = 0;
    for (std::size_t pos = haystack.find(needle); pos != std::string::npos;
         pos = haystack.find(needle, pos + needle.size())) {
        ++count;
    }
    return count;
}

Json::Value jsonFromString(const std::string& raw) {
    Json::Value root;
    Json::CharReaderBuilder builder;
    std::string errs;
    std::unique_ptr<Json::CharReader> reader(builder.newCharReader());
    reader->parse(raw.data(), raw.data() + raw.size(), &root, &errs);
    return root;
}

} // namespace

// ---------------------------------------------------------------------------
// trimCopy — category name normalization
// ---------------------------------------------------------------------------

TEST_CASE(service_trim_copy_normalizes_surrounding_whitespace) {
    CHECK_EQ(trimCopy("  hello  "), std::string("hello"));
    CHECK_EQ(trimCopy("\t\n hello world \r\n"), std::string("hello world"));
    CHECK_EQ(trimCopy("no-trim"), std::string("no-trim"));
    // Inner whitespace is preserved verbatim.
    CHECK_EQ(trimCopy("  a  b  "), std::string("a  b"));
}

TEST_CASE(service_trim_copy_collapses_whitespace_only_input) {
    CHECK_EQ(trimCopy(""), std::string(""));
    CHECK_EQ(trimCopy("   "), std::string(""));
    CHECK_EQ(trimCopy("\t\r\n"), std::string(""));
}

TEST_CASE(service_trim_copy_preserves_multibyte_content) {
    // Byte-wise std::isspace must not touch UTF-8 payload bytes.
    CHECK_EQ(trimCopy("  交易策略  "), std::string("交易策略"));
    CHECK_EQ(trimCopy("CTA策略"), std::string("CTA策略"));
}

// ---------------------------------------------------------------------------
// parseOptionalParent — parent_id parameter validation
// ---------------------------------------------------------------------------

TEST_CASE(service_parse_optional_parent_absent_member_uses_fallback) {
    Json::Value json = jsonFromString("{\"name\":\"A\"}");
    CHECK(!parseOptionalParent(json, std::nullopt).has_value());
    CHECK_EQ(parseOptionalParent(json, std::optional<int>(5)).value_or(-1), 5);
}

TEST_CASE(service_parse_optional_parent_null_and_non_positive_mean_root) {
    CHECK(!parseOptionalParent(jsonFromString("{\"parent_id\":null}"), std::nullopt).has_value());
    CHECK(!parseOptionalParent(jsonFromString("{\"parent_id\":0}"), std::nullopt).has_value());
    CHECK(!parseOptionalParent(jsonFromString("{\"parent_id\":-3}"), std::nullopt).has_value());
    // Json::Value::asInt() truncates fractional values toward zero.
    CHECK(!parseOptionalParent(jsonFromString("{\"parent_id\":0.9}"), std::nullopt).has_value());
    CHECK_EQ(parseOptionalParent(jsonFromString("{\"parent_id\":1.9}"), std::nullopt).value_or(-1), 1);
}

TEST_CASE(service_parse_optional_parent_throws_on_non_numeric_string) {
    // JsonCpp's asInt() raises Json::LogicError for string members instead of
    // coercing; the helper (moved verbatim from the service) propagates that to
    // the caller. Pinned here so a future refactor cannot silently change it.
    bool threw = false;
    try {
        parseOptionalParent(jsonFromString("{\"parent_id\":\"abc\"}"), std::nullopt);
    } catch (const Json::LogicError&) {
        threw = true;
    }
    CHECK(threw);
}

TEST_CASE(service_parse_optional_parent_positive_value_wins_over_fallback) {
    CHECK_EQ(parseOptionalParent(jsonFromString("{\"parent_id\":7}"), std::nullopt).value_or(-1), 7);
    CHECK_EQ(parseOptionalParent(jsonFromString("{\"parent_id\":7}"), std::optional<int>(5)).value_or(-1), 7);
}

// ---------------------------------------------------------------------------
// findCategory / legacyCategoryExists — lookup + fallback validation
// ---------------------------------------------------------------------------

TEST_CASE(service_find_category_returns_match_or_null) {
    auto categories = sampleCategories();
    const auto* found = findCategory(categories, 101);
    CHECK(found != nullptr);
    if (found != nullptr) {
        CHECK_EQ(found->name, std::string("A-1"));
        CHECK_EQ(found->parentId.value_or(-1), 1);
    }
    CHECK(findCategory(categories, 999) == nullptr);
    CHECK(findCategory(categories, 0) == nullptr);
}

TEST_CASE(service_legacy_category_exists_matches_visible_legacy_ids) {
    CHECK(legacyCategoryExists(1));
    CHECK(legacyCategoryExists(101));
    CHECK(legacyCategoryExists(907));
    CHECK(!legacyCategoryExists(0));
    CHECK(!legacyCategoryExists(-1));
    CHECK(!legacyCategoryExists(9999));
}

// ---------------------------------------------------------------------------
// Pagination arithmetic
// ---------------------------------------------------------------------------

TEST_CASE(service_page_offset_is_zero_based) {
    CHECK_EQ(pageOffset(1, 10), 0);
    CHECK_EQ(pageOffset(2, 10), 10);
    CHECK_EQ(pageOffset(3, 20), 40);
    CHECK_EQ(pageOffset(1, 1), 0);
}

TEST_CASE(service_total_pages_rounds_up) {
    CHECK_EQ(totalPages(0, 10), 0);
    CHECK_EQ(totalPages(1, 10), 1);
    CHECK_EQ(totalPages(9, 10), 1);
    CHECK_EQ(totalPages(10, 10), 1);
    CHECK_EQ(totalPages(11, 10), 2);
    CHECK_EQ(totalPages(100, 10), 10);
    CHECK_EQ(totalPages(101, 10), 11);
}

// ---------------------------------------------------------------------------
// SQL assembly
// ---------------------------------------------------------------------------

TEST_CASE(service_sql_string_literal_escapes_quotes_and_backslashes) {
    CHECK_EQ(sqlStringLiteral("abc"), std::string("'abc'"));
    CHECK_EQ(sqlStringLiteral(""), std::string("''"));
    CHECK_EQ(sqlStringLiteral("O'Brien"), std::string("'O''Brien'"));
    CHECK_EQ(sqlStringLiteral("'; DROP TABLE article_category; --"),
             std::string("'''; DROP TABLE article_category; --'"));
    CHECK_EQ(sqlStringLiteral("a\\b"), std::string("'a\\\\b'"));
}

TEST_CASE(service_legacy_insert_sql_splits_roots_and_children) {
    const std::string rootSql = legacyCategoryInsertSql(true);
    const std::string childSql = legacyCategoryInsertSql(false);

    const std::string prefix =
        "INSERT IGNORE INTO article_category (id, parent_id, name, sort_order, visible) VALUES ";

    CHECK(rootSql.rfind(prefix, 0) == 0);
    CHECK(childSql.rfind(prefix, 0) == 0);

    // Roots carry NULL parent_id, children never do.
    CHECK(rootSql.find("(1,NULL,'交易策略',10,1)") != std::string::npos);
    CHECK(rootSql.find("(9,NULL,'教程',90,1)") != std::string::npos);
    CHECK_EQ(countOccurrences(rootSql, "NULL,"), static_cast<std::size_t>(9));
    CHECK_EQ(countOccurrences(childSql, "NULL,"), static_cast<std::size_t>(0));

    // Children carry their parent id.
    CHECK(childSql.find("(101,1,'CTA策略',10,1)") != std::string::npos);
    CHECK(childSql.find("(907,9,'ib_tws_api入门教程',70,1)") != std::string::npos);
    CHECK_EQ(countOccurrences(childSql, "),("), static_cast<std::size_t>(60));

    // No trailing separator after the final tuple.
    CHECK_EQ(rootSql.back(), ')');
    CHECK_EQ(childSql.back(), ')');
}

TEST_CASE(service_my_articles_count_sql_filters_by_positive_type) {
    CHECK_EQ(buildMyArticlesCountSql(0),
             std::string("SELECT COUNT(*) AS total FROM article a WHERE a.userid = ?"));
    CHECK_EQ(buildMyArticlesCountSql(-1),
             std::string("SELECT COUNT(*) AS total FROM article a WHERE a.userid = ?"));
    CHECK_EQ(buildMyArticlesCountSql(5),
             std::string("SELECT COUNT(*) AS total FROM article a WHERE a.userid = ?"
                         " AND a.type = ?"));
}

TEST_CASE(service_my_articles_data_sql_embeds_limit_and_offset) {
    CHECK_EQ(buildMyArticlesDataSql(0, 10, 0),
             std::string("SELECT a.*, u.nickname FROM article a LEFT JOIN users u ON a.userid = u.userid "
                         "WHERE a.userid = ? ORDER BY a.createtime DESC LIMIT 10 OFFSET 0"));
    CHECK_EQ(buildMyArticlesDataSql(3, 20, 40),
             std::string("SELECT a.*, u.nickname FROM article a LEFT JOIN users u ON a.userid = u.userid "
                         "WHERE a.userid = ? AND a.type = ? ORDER BY a.createtime DESC LIMIT 20 OFFSET 40"));
}

// ---------------------------------------------------------------------------
// articleCategoryResponseData — {types, flat, tree} DTO assembly
// ---------------------------------------------------------------------------

TEST_CASE(service_category_response_data_shape) {
    auto data = articleCategoryResponseData(sampleCategories(), true, true);
    CHECK(data.isMember("types"));
    CHECK(data.isMember("flat"));
    CHECK(data.isMember("tree"));
    CHECK_EQ(data["types"]["1"].asString(), std::string("A"));
    CHECK(!data["types"].isMember("102"));
    CHECK_EQ(data["flat"].size(), 5U);
    CHECK_EQ(data["flat"][0]["id"].asInt(), 1);
    CHECK_EQ(data["flat"][0]["article_count"].asInt(), 3);
    CHECK_EQ(data["tree"].size(), 3U);
}

TEST_CASE(service_category_response_data_can_omit_article_counts) {
    auto data = articleCategoryResponseData(sampleCategories(), true, false);
    CHECK_EQ(data["flat"].size(), 5U);
    CHECK(!data["flat"][0].isMember("article_count"));

    // visibleOnly=false keeps hidden categories in the payload.
    auto all = articleCategoryResponseData(sampleCategories(), false, true);
    CHECK_EQ(all["flat"].size(), 6U);
    CHECK(all["types"].isMember("102"));
}
