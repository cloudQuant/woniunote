/**
 * @file upload_safety.h
 * @brief Filename/extension sanitization helpers for file uploads.
 *
 * Header-only and dependency-light so both controllers and the unit tests can
 * share the exact same logic. These functions defend against path traversal
 * and unexpected file types by stripping everything except a safe extension.
 */

#ifndef WONIUNOTE_CORE_UPLOAD_SAFETY_H
#define WONIUNOTE_CORE_UPLOAD_SAFETY_H

#include <algorithm>
#include <cctype>
#include <string>
#include <vector>

namespace woniunote {

/**
 * @brief Extract a sanitized, lowercase extension WITHOUT the leading dot.
 *
 * Only [a-z0-9] are kept, so any embedded path separators, "../" sequences, or
 * NUL bytes in the original name can never reach the filesystem. Returns "" if
 * there is no usable extension. The result is capped at 10 characters.
 */
inline std::string sanitizeExtension(const std::string& originalName)
{
    auto dotPos = originalName.rfind('.');
    if (dotPos == std::string::npos || dotPos + 1 >= originalName.size()) {
        return "";
    }
    std::string ext = originalName.substr(dotPos + 1);
    std::string clean;
    clean.reserve(ext.size());
    for (char c : ext) {
        unsigned char uc = static_cast<unsigned char>(c);
        if (std::isalnum(uc)) {
            clean += static_cast<char>(std::tolower(uc));
        }
    }
    if (clean.size() > 10) {
        clean = clean.substr(0, 10);
    }
    return clean;
}

/** @brief Case-insensitive membership test against an allow-list of extensions. */
inline bool isExtAllowed(const std::string& ext,
                         const std::vector<std::string>& allow)
{
    return std::find(allow.begin(), allow.end(), ext) != allow.end();
}

} // namespace woniunote

#endif // WONIUNOTE_CORE_UPLOAD_SAFETY_H
