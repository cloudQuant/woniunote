/**
 * @file TodoController.cc
 * @brief Todo API Controller Implementation
 */

#include "TodoController.h"
#include "core/database.h"
#include "core/logger.h"
#include "models/Todo.h"
#include <drogon/HttpResponse.h>

using namespace drogon;

namespace woniunote {
namespace controllers {

void TodoController::listCategories(const HttpRequestPtr& req,
                                    std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "SELECT * FROM todo_category WHERE userid = ? ORDER BY sort_order, id",
        [callback](const orm::Result& result) {
            Json::Value categories(Json::arrayValue);
            for (const auto& row : result) {
                models::TodoCategory cat(row);
                categories.append(cat.toJson());
            }
            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "success";
            ret["data"] = categories;
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("DB error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        std::stoll(userId)
    );
}

void TodoController::createCategory(const HttpRequestPtr& req,
                                    std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto json = req->getJsonObject();
    if (!json || !json->isMember("name")) {
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "分类名称不能为空";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }

    std::string name = (*json)["name"].asString();
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "INSERT INTO todo_category (userid, name, createtime, updatetime) VALUES (?, ?, NOW(), NOW())",
        [callback](const orm::Result& result) {
            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "创建成功";
            ret["data"]["id"] = static_cast<Json::Int64>(result.insertId());
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Insert error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "创建失败";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        std::stoll(userId), name
    );
}

void TodoController::deleteCategory(const HttpRequestPtr& req,
                                    std::function<void(const HttpResponsePtr&)>&& callback,
                                    int64_t id)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "DELETE FROM todo_category WHERE id = ? AND userid = ?",
        [callback](const orm::Result&) {
            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "删除成功";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Delete error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "删除失败";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        id, std::stoll(userId)
    );
}

void TodoController::listItems(const HttpRequestPtr& req,
                               std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    std::string categoryId = req->getParameter("category_id");
    auto dbClient = Database::getClient();

    std::string sql = "SELECT * FROM todo_item WHERE userid = ?";
    if (!categoryId.empty()) {
        sql += " AND category_id = " + categoryId;
    }
    sql += " ORDER BY priority DESC, createtime DESC";

    dbClient->execSqlAsync(
        sql,
        [callback](const orm::Result& result) {
            Json::Value items(Json::arrayValue);
            for (const auto& row : result) {
                models::TodoItem item(row);
                items.append(item.toJson());
            }
            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "success";
            ret["data"] = items;
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("DB error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "数据库错误";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        std::stoll(userId)
    );
}

void TodoController::createItem(const HttpRequestPtr& req,
                                std::function<void(const HttpResponsePtr&)>&& callback)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto json = req->getJsonObject();
    if (!json || !json->isMember("body") || !json->isMember("category_id")) {
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "内容和分类不能为空";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }

    std::string body = (*json)["body"].asString();
    int64_t categoryId = (*json)["category_id"].asInt64();
    int priority = json->get("priority", 0).asInt();
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "INSERT INTO todo_item (userid, category_id, body, priority, createtime, updatetime) "
        "VALUES (?, ?, ?, ?, NOW(), NOW())",
        [callback](const orm::Result& result) {
            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "创建成功";
            ret["data"]["id"] = static_cast<Json::Int64>(result.insertId());
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Insert error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "创建失败";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        std::stoll(userId), categoryId, body, priority
    );
}

void TodoController::updateItem(const HttpRequestPtr& req,
                                std::function<void(const HttpResponsePtr&)>&& callback,
                                int64_t id)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto json = req->getJsonObject();
    if (!json) {
        Json::Value ret;
        ret["code"] = 400;
        ret["message"] = "请求格式错误";
        callback(HttpResponse::newHttpJsonResponse(ret));
        return;
    }

    std::string body = json->get("body", "").asString();
    int priority = json->get("priority", 0).asInt();
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "UPDATE todo_item SET body = ?, priority = ?, updatetime = NOW() WHERE id = ? AND userid = ?",
        [callback](const orm::Result&) {
            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "更新成功";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Update error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "更新失败";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        body, priority, id, std::stoll(userId)
    );
}

void TodoController::deleteItem(const HttpRequestPtr& req,
                                std::function<void(const HttpResponsePtr&)>&& callback,
                                int64_t id)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "DELETE FROM todo_item WHERE id = ? AND userid = ?",
        [callback](const orm::Result&) {
            Json::Value ret;
            ret["code"] = 200;
            ret["message"] = "删除成功";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Delete error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "删除失败";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        id, std::stoll(userId)
    );
}

void TodoController::toggleDone(const HttpRequestPtr& req,
                                std::function<void(const HttpResponsePtr&)>&& callback,
                                int64_t id)
{
    auto userId = req->getAttributes()->get<std::string>("user_id");
    auto dbClient = Database::getClient();

    dbClient->execSqlAsync(
        "UPDATE todo_item SET done = 1 - done, donetime = IF(done = 0, NOW(), NULL), updatetime = NOW() "
        "WHERE id = ? AND userid = ?",
        [callback, id, dbClient](const orm::Result&) {
            dbClient->execSqlAsync(
                "SELECT done FROM todo_item WHERE id = ?",
                [callback](const orm::Result& result) {
                    int done = result[0]["done"].as<int>();
                    Json::Value ret;
                    ret["code"] = 200;
                    ret["message"] = done ? "已完成" : "已取消完成";
                    ret["data"]["done"] = done;
                    callback(HttpResponse::newHttpJsonResponse(ret));
                },
                [callback](const orm::DrogonDbException&) {},
                id
            );
        },
        [callback](const orm::DrogonDbException& e) {
            Logger::error("Update error: " + std::string(e.base().what()));
            Json::Value ret;
            ret["code"] = 500;
            ret["message"] = "操作失败";
            callback(HttpResponse::newHttpJsonResponse(ret));
        },
        id, std::stoll(userId)
    );
}

} // namespace controllers
} // namespace woniunote
