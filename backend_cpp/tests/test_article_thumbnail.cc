#include "test_framework.h"
#include "core/article_thumbnail.h"

#include <string>
#include <vector>

using woniunote::core::articleThumbnailForDto;
using woniunote::core::normalizeArticleThumbnail;

TEST_CASE(article_thumbnail_accepts_legacy_names_and_normalizes_api_paths) {
    const auto legacy = normalizeArticleThumbnail("cover_1-final.png");
    CHECK(legacy.has_value());
    if (legacy) CHECK_EQ(*legacy, std::string("cover_1-final.png"));

    const auto apiPath = normalizeArticleThumbnail("/api/thumb/cover.png");
    CHECK(apiPath.has_value());
    if (apiPath) CHECK_EQ(*apiPath, std::string("cover.png"));

    const auto uploadsPath = normalizeArticleThumbnail(
        "/uploads/uploads/images/2026/10/123_0001.png");
    CHECK(uploadsPath.has_value());
    if (uploadsPath) {
        CHECK_EQ(*uploadsPath,
                 std::string("/uploads/uploads/images/2026/10/123_0001.png"));
    }
}

TEST_CASE(article_thumbnail_empty_input_clears_stored_override) {
    const auto normalized = normalizeArticleThumbnail("");
    CHECK(normalized.has_value());
    if (normalized) CHECK(normalized->empty());
}

TEST_CASE(article_thumbnail_enforces_512_ascii_byte_limit) {
    const std::string maxName = std::string(508, 'a') + ".png";
    CHECK_EQ(maxName.size(), static_cast<std::size_t>(512));
    const auto maxValue = normalizeArticleThumbnail(maxName);
    CHECK(maxValue.has_value());
    if (maxValue) CHECK_EQ(*maxValue, maxName);

    const std::string tooLong = std::string(509, 'a') + ".png";
    CHECK_EQ(tooLong.size(), static_cast<std::size_t>(513));
    CHECK(!normalizeArticleThumbnail(tooLong).has_value());
}

TEST_CASE(article_thumbnail_rejects_unsafe_paths_and_non_ascii_input) {
    const std::vector<std::string> invalidValues{
        "no-extension",
        ".png",
        "image.",
        "folder/image.png",
        "../image.png",
        "name..png",
        "/api/thumb/",
        "/api/thumb/folder/image.png",
        "/api/thumb//image.png",
        "/uploads/",
        "/uploads//image.png",
        "/uploads/images/./image.png",
        "/uploads/images/../image.png",
        "/uploads/images/name..png",
        "/uploads/images/no-extension",
        "image\\name.png",
        "image%2fname.png",
        "image.png?size=1",
        "image.png#fragment",
        "//cdn.example/image.png",
        "http://cdn.example/image.png",
        "https://cdn.example/image.png",
        "data:image/png;base64,AA",
        std::string("image\n.png"),
        std::string("猫.png")};

    for (const auto& value : invalidValues) {
        CHECK(!normalizeArticleThumbnail(value).has_value());
    }
}

TEST_CASE(article_thumbnail_dtos_preserve_upload_paths_and_fallback_safely) {
    CHECK_EQ(articleThumbnailForDto("cover.png", 3), std::string("cover.png"));
    CHECK_EQ(articleThumbnailForDto("/api/thumb/cover.png", 3), std::string("cover.png"));
    CHECK_EQ(articleThumbnailForDto("/uploads/images/cover.png", 3),
             std::string("/uploads/images/cover.png"));
    CHECK_EQ(articleThumbnailForDto("", 3), std::string("3.png"));
    CHECK_EQ(articleThumbnailForDto("https://cdn.example/cover.png", 3),
             std::string("3.png"));
}
