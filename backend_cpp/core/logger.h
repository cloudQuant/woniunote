/**
 * @file logger.h
 * @brief Logging Utilities
 * 
 * Provides structured logging functions for the application.
 */

#ifndef WONIUNOTE_CORE_LOGGER_H
#define WONIUNOTE_CORE_LOGGER_H

#include <string>
#include <map>
#include <drogon/drogon.h>

namespace woniunote {

/**
 * @class Logger
 * @brief Static logging utility class
 * 
 * Provides structured logging with context support.
 */
class Logger {
public:
    /**
     * @brief Initialize logging system
     */
    static void init();

    /**
     * @brief Log info message
     * @param message Log message
     * @param context Optional context map
     */
    static void info(const std::string& message, 
                     const std::map<std::string, std::string>& context = {});

    /**
     * @brief Log warning message
     * @param message Log message
     * @param context Optional context map
     */
    static void warning(const std::string& message,
                        const std::map<std::string, std::string>& context = {});

    /**
     * @brief Log error message
     * @param message Log message
     * @param context Optional context map
     */
    static void error(const std::string& message,
                      const std::map<std::string, std::string>& context = {});

    /**
     * @brief Log debug message
     * @param message Log message
     * @param context Optional context map
     */
    static void debug(const std::string& message,
                      const std::map<std::string, std::string>& context = {});

private:
    static std::string formatContext(const std::map<std::string, std::string>& context);
};

} // namespace woniunote

#endif // WONIUNOTE_CORE_LOGGER_H
