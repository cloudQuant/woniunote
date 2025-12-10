/**
 * @file database.cc
 * @brief Database Utilities Implementation
 */

#include "database.h"
#include "logger.h"

namespace woniunote {

DbClientPtr Database::getClient()
{
    return getClient("mysql");
}

DbClientPtr Database::getClient(const std::string& name)
{
    auto client = drogon::app().getDbClient(name);
    if (!client) {
        Logger::error("[Database] Client not found", {{"name", name}});
        throw std::runtime_error("Database client '" + name + "' not configured");
    }
    Logger::debug("[Database] Client acquired", {{"name", name}});
    return client;
}

void Database::beginTransaction(
    std::function<void(const std::shared_ptr<Transaction>&)> callback)
{
    auto client = getClient();
    client->newTransactionAsync(
        [callback](const std::shared_ptr<Transaction>& trans) {
            if (trans) {
                callback(trans);
            } else {
                Logger::error("Failed to start database transaction");
            }
        }
    );
}

void Database::execSql(
    const std::string& sql,
    std::function<void(const Result&)> callback,
    std::function<void(const DrogonDbException&)> exceptionCallback)
{
    auto client = getClient();
    client->execSqlAsync(
        sql,
        [callback](const Result& result) {
            callback(result);
        },
        [exceptionCallback](const DrogonDbException& e) {
            Logger::error("SQL execution failed: " + std::string(e.base().what()));
            if (exceptionCallback) {
                exceptionCallback(e);
            }
        }
    );
}

} // namespace woniunote
