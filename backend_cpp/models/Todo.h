/**
 * @file Todo.h
 * @brief Todo Models (Category and Item) for Drogon ORM
 */

#ifndef WONIUNOTE_MODELS_TODO_H
#define WONIUNOTE_MODELS_TODO_H

#include <drogon/orm/Mapper.h>
#include <json/json.h>
#include <string>

namespace woniunote {
namespace models {

class TodoCategory {
public:
    static constexpr const char* tableName = "todo_category";
    static constexpr const char* primaryKeyName = "id";

    TodoCategory() = default;
    explicit TodoCategory(const drogon::orm::Row& row);

    int64_t getId() const { return id_; }
    int64_t getUserid() const { return userid_; }
    const std::string& getName() const { return name_; }
    int getSortOrder() const { return sortOrder_; }

    void setId(int64_t v) { id_ = v; }
    void setUserid(int64_t v) { userid_ = v; }
    void setName(const std::string& v) { name_ = v; }
    void setSortOrder(int v) { sortOrder_ = v; }

    Json::Value toJson() const;

private:
    int64_t id_ = 0;
    int64_t userid_ = 0;
    std::string name_;
    int sortOrder_ = 0;
};

class TodoItem {
public:
    static constexpr const char* tableName = "todo_item";
    static constexpr const char* primaryKeyName = "id";

    TodoItem() = default;
    explicit TodoItem(const drogon::orm::Row& row);

    int64_t getId() const { return id_; }
    int64_t getUserid() const { return userid_; }
    int64_t getCategoryId() const { return categoryId_; }
    const std::string& getBody() const { return body_; }
    int getDone() const { return done_; }
    int getPriority() const { return priority_; }

    void setId(int64_t v) { id_ = v; }
    void setUserid(int64_t v) { userid_ = v; }
    void setCategoryId(int64_t v) { categoryId_ = v; }
    void setBody(const std::string& v) { body_ = v; }
    void setDone(int v) { done_ = v; }
    void setPriority(int v) { priority_ = v; }

    Json::Value toJson() const;

private:
    int64_t id_ = 0;
    int64_t userid_ = 0;
    int64_t categoryId_ = 0;
    std::string body_;
    int done_ = 0;
    int priority_ = 0;
};

} // namespace models
} // namespace woniunote

#endif // WONIUNOTE_MODELS_TODO_H
