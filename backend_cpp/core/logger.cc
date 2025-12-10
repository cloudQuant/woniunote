/**
 * @file logger.cc
 * @brief Logging Utilities Implementation
 */

#include "logger.h"
#include <filesystem>
#include <mutex>
#include <vector>
#include <sstream>
#include <spdlog/async.h>
#include <spdlog/sinks/rotating_file_sink.h>
#include <spdlog/sinks/stdout_color_sinks.h>

namespace woniunote {

namespace {
std::mutex loggerMutex;
}

std::shared_ptr<spdlog::logger> Logger::logger_ = nullptr;

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
    oss << " }";
    return oss.str();
}

void Logger::ensureInitialized()
{
    if (!logger_) {
        init();
    }
}

void Logger::init(const std::string& logDir)
{
    std::lock_guard<std::mutex> lock(loggerMutex);
    if (logger_) {
        return;
    }

    namespace fs = std::filesystem;
    fs::path logPath = fs::path(logDir);
    try {
        if (!fs::exists(logPath)) {
            fs::create_directories(logPath);
        }
    } catch (const std::exception& e) {
        spdlog::error("Failed to create log directory {}: {}", logPath.string(), e.what());
    }

    const auto logFile = (logPath / "backend.log").string();

    try {
        spdlog::init_thread_pool(8192, 1);
    } catch (const spdlog::spdlog_ex&) {
        // Thread pool already initialized elsewhere; ignore.
    }

    auto fileSink = std::make_shared<spdlog::sinks::rotating_file_sink_mt>(
        logFile, kRotateSizeBytes, kRotateFiles, true);
    fileSink->set_level(spdlog::level::debug);
    fileSink->set_pattern("[%Y-%m-%d %H:%M:%S.%e] [%^%l%$] %v");

    auto consoleSink = std::make_shared<spdlog::sinks::stdout_color_sink_mt>();
    consoleSink->set_level(spdlog::level::debug);
    consoleSink->set_pattern("[%Y-%m-%d %H:%M:%S.%e] [%^%l%$] %v");

    std::vector<spdlog::sink_ptr> sinks{consoleSink, fileSink};

    logger_ = std::make_shared<spdlog::logger>("woniunote_logger", sinks.begin(), sinks.end());
    spdlog::register_logger(logger_);
    logger_->set_level(spdlog::level::debug);
    logger_->flush_on(spdlog::level::info);
}

void Logger::shutdown()
{
    std::lock_guard<std::mutex> lock(loggerMutex);
    if (logger_) {
        logger_->flush();
        spdlog::drop(logger_->name());
        logger_.reset();
    }
    spdlog::shutdown();
}

void Logger::setLevel(spdlog::level::level_enum level)
{
    ensureInitialized();
    logger_->set_level(level);
}

void Logger::info(const std::string& message, 
                  const std::map<std::string, std::string>& context)
{
    ensureInitialized();
    logger_->info("{}{}", message, formatContext(context));
}

void Logger::warning(const std::string& message,
                     const std::map<std::string, std::string>& context)
{
    ensureInitialized();
    logger_->warn("{}{}", message, formatContext(context));
}

void Logger::error(const std::string& message,
                   const std::map<std::string, std::string>& context)
{
    ensureInitialized();
    logger_->error("{}{}", message, formatContext(context));
}

void Logger::debug(const std::string& message,
                   const std::map<std::string, std::string>& context)
{
    ensureInitialized();
    logger_->debug("{}{}", message, formatContext(context));
}

} // namespace woniunote
