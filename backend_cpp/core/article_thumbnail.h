/**
 * @file article_thumbnail.h
 * @brief Validation and normalization for article thumbnail references.
 */

#ifndef WONIUNOTE_CORE_ARTICLE_THUMBNAIL_H
#define WONIUNOTE_CORE_ARTICLE_THUMBNAIL_H

#include <cstddef>
#include <optional>
#include <string>
#include <string_view>

namespace woniunote {
namespace core {
namespace article_thumbnail_detail {

constexpr std::string_view kApiThumbnailPrefix{"/api/thumb/"};
constexpr std::string_view kUploadsPrefix{"/uploads/"};
constexpr std::size_t kMaxThumbnailBytes{512};

inline bool hasOnlySafeAscii(std::string_view value) noexcept
{
    for (const unsigned char character : value)
    {
        const bool isLetter = (character >= 'A' && character <= 'Z') ||
                              (character >= 'a' && character <= 'z');
        const bool isDigit = character >= '0' && character <= '9';
        if (!isLetter && !isDigit && character != '_' && character != '-' &&
            character != '.' && character != '/')
        {
            return false;
        }
    }
    return true;
}

inline bool isSafeBasename(std::string_view filename) noexcept
{
    if (filename.empty() || filename.find('/') != std::string_view::npos ||
        filename.find("..") != std::string_view::npos)
    {
        return false;
    }

    const std::size_t extensionSeparator = filename.rfind('.');
    return extensionSeparator != std::string_view::npos && extensionSeparator > 0 &&
           extensionSeparator + 1 < filename.size();
}

inline bool isSafeUploadsPath(std::string_view path) noexcept
{
    if (path.substr(0, kUploadsPrefix.size()) != kUploadsPrefix)
    {
        return false;
    }

    std::string_view relativePath = path.substr(kUploadsPrefix.size());
    std::string_view finalSegment;
    std::size_t segmentStart = 0;
    while (segmentStart <= relativePath.size())
    {
        const std::size_t separator = relativePath.find('/', segmentStart);
        const std::size_t segmentEnd = separator == std::string_view::npos
                                           ? relativePath.size()
                                           : separator;
        const std::string_view segment = relativePath.substr(
            segmentStart, segmentEnd - segmentStart);
        if (segment.empty() || segment == "." || segment == "..")
        {
            return false;
        }
        finalSegment = segment;
        if (separator == std::string_view::npos)
        {
            break;
        }
        segmentStart = separator + 1;
    }

    return isSafeBasename(finalSegment);
}

}  // namespace article_thumbnail_detail

/**
 * Validate and normalize a thumbnail supplied to an article write.
 * Empty input clears the stored override so the DTO can use the current type's
 * built-in thumbnail. A null optional means the input does not satisfy the
 * storage contract.
 */
inline std::optional<std::string> normalizeArticleThumbnail(std::string_view thumbnail)
{
    using namespace article_thumbnail_detail;

    if (thumbnail.empty())
    {
        return std::string{};
    }
    if (thumbnail.size() > kMaxThumbnailBytes || !hasOnlySafeAscii(thumbnail) ||
        thumbnail.find("..") != std::string_view::npos)
    {
        return std::nullopt;
    }

    if (thumbnail.substr(0, kApiThumbnailPrefix.size()) == kApiThumbnailPrefix)
    {
        const std::string_view filename = thumbnail.substr(kApiThumbnailPrefix.size());
        if (!isSafeBasename(filename))
        {
            return std::nullopt;
        }
        return std::string(filename);
    }

    if (thumbnail.substr(0, kUploadsPrefix.size()) == kUploadsPrefix)
    {
        if (!isSafeUploadsPath(thumbnail))
        {
            return std::nullopt;
        }
        return std::string(thumbnail);
    }

    if (!isSafeBasename(thumbnail))
    {
        return std::nullopt;
    }
    return std::string(thumbnail);
}

/** Return a safe API-facing thumbnail, falling back for invalid old rows. */
inline std::string articleThumbnailForDto(std::string_view thumbnail,
                                          int articleType)
{
    const auto normalized = normalizeArticleThumbnail(thumbnail);
    if (!normalized || normalized->empty())
    {
        return std::to_string(articleType) + ".png";
    }
    return *normalized;
}

}  // namespace core
}  // namespace woniunote

#endif  // WONIUNOTE_CORE_ARTICLE_THUMBNAIL_H
