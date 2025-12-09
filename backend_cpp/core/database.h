/**
 * @file database.h
 * @brief Database Utilities
 * 
 * Provides database connection and transaction utilities.
 */

#ifndef WONIUNOTE_CORE_DATABASE_H
#define WONIUNOTE_CORE_DATABASE_H

#include <drogon/drogon.h>
#include <drogon/orm/DbClient.h>
#include <functional>
#include <memory>

namespace woniunote {

using namespace drogon::orm;

/**
 * @class Database
 * @brief Database utility class
 * 
 * Provides convenient access to Drogon's database client.
 */
class Database {
public:
    /**
     * @brief Get the default MySQL database client
     * @return Shared pointer to DbClient
     */
    static DbClientPtr getClient();

    /**
     * @brief Get a database client by name
     * @param name Database connector name from config
     * @return Shared pointer to DbClient
     */
    static DbClientPtr getClient(const std::string& name);

    /**
     * @brief Begin a new transaction
     * @param callback Callback receiving the transaction
     */
    static void beginTransaction(
        std::function<void(const std::shared_ptr<Transaction>&)> callback);

    /**
     * @brief Execute a raw SQL query asynchronously
     * @param sql SQL query string
     * @param callback Success callback
     * @param exceptionCallback Exception callback
     */
    static void execSql(
        const std::string& sql,
        std::function<void(const Result&)> callback,
        std::function<void(const DrogonDbException&)> exceptionCallback);
};

} // namespace woniunote

#endif // WONIUNOTE_CORE_DATABASE_H
