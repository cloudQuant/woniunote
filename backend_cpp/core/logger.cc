/**
 * @file logger.cc
 * @brief Logging Utilities Implementation
 */

#include "logger.h"
#include <sstream>
#include <chrono>
#include <iomanip>

namespace woniunote {

void Logger::init()
{
    // Drogon handles log initialization via config.json
    // This is a placeholder for additional initialization if needed
}

std::string Logger::formatContext(const std::map<std::string, std::string>& context)
{
    if (context.empty()) {
        return "";
    }

    std::ostringstream oss;
    oss << " {";
    bool first = true;
    for (const auto& [key, value] : context) {
        if (!first) oss << ", ";
        oss << "\"" << key << "\": \"" << value << "\"";
        first = false;
    }
    oss << "}";
    return oss.str();
}

void Logger::info(const std::string& message, 
                  const std::map<std::string, std::string>& context)
{
    LOG_INFO << message << formatContext(context);
}

void Logger::warning(const std::string& message,
                     const std::map<std::string, std::string>& context)
{
    LOG_WARN << message << formatContext(context);
}

void Logger::error(const std::string& message,
                   const std::map<std::string, std::string>& context)
{
    LOG_ERROR << message << formatContext(context);
}

void Logger::debug(const std::string& message,
                   const std::map<std::string, std::string>& context)
{
    LOG_DEBUG << message << formatContext(context);
}

} // namespace woniunote
