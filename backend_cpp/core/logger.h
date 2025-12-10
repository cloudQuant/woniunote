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
#include <memory>
#include <spdlog/spdlog.h>

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
    static void init(const std::string& logDir = "logs");

    /**
     * @brief Shutdown logging system
     */
    static void shutdown();

    /**
     * @brief Set global log level
     */
    static void setLevel(spdlog::level::level_enum level);

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
    static void ensureInitialized();
    static std::string formatContext(const std::map<std::string, std::string>& context);
    static std::shared_ptr<spdlog::logger> logger_;
    static inline constexpr std::size_t kRotateSizeBytes = 128 * 1024 * 1024; // 128MB
    static inline constexpr std::size_t kRotateFiles = 30; // Keep 30 days of logs
};

} // namespace woniunote

#endif // WONIUNOTE_CORE_LOGGER_H
