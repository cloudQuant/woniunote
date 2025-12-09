/**
 * @file Card.h
 * @brief Card Models (Category and Card) for Drogon ORM
 */

#ifndef WONIUNOTE_MODELS_CARD_H
#define WONIUNOTE_MODELS_CARD_H

#include <drogon/orm/Mapper.h>
#include <json/json.h>
#include <string>

namespace woniunote {
namespace models {

class CardCategory {
public:
    static constexpr const char* tableName = "card_category";
    static constexpr const char* primaryKeyName = "id";

    CardCategory() = default;
    explicit CardCategory(const drogon::orm::Row& row);

    int64_t getId() const { return id_; }
    int64_t getUserid() const { return userid_; }
    const std::string& getName() const { return name_; }
    int getType() const { return type_; }
    int getSortOrder() const { return sortOrder_; }

    void setId(int64_t v) { id_ = v; }
    void setUserid(int64_t v) { userid_ = v; }
    void setName(const std::string& v) { name_ = v; }
    void setType(int v) { type_ = v; }
    void setSortOrder(int v) { sortOrder_ = v; }

    Json::Value toJson() const;

private:
    int64_t id_ = 0;
    int64_t userid_ = 0;
    std::string name_;
    int type_ = 0;
    int sortOrder_ = 0;
};

class Card {
public:
    static constexpr const char* tableName = "card";
    static constexpr const char* primaryKeyName = "id";

    Card() = default;
    explicit Card(const drogon::orm::Row& row);

    int64_t getId() const { return id_; }
    int64_t getUserid() const { return userid_; }
    int64_t getCategoryId() const { return categoryId_; }
    const std::string& getHeadline() const { return headline_; }
    const std::string& getContent() const { return content_; }
    int getType() const { return type_; }
    int getIsRepeat() const { return isRepeat_; }
    int getUsedtime() const { return usedtime_; }

    void setId(int64_t v) { id_ = v; }
    void setUserid(int64_t v) { userid_ = v; }
    void setCategoryId(int64_t v) { categoryId_ = v; }
    void setHeadline(const std::string& v) { headline_ = v; }
    void setContent(const std::string& v) { content_ = v; }
    void setType(int v) { type_ = v; }
    void setIsRepeat(int v) { isRepeat_ = v; }
    void setUsedtime(int v) { usedtime_ = v; }

    Json::Value toJson() const;

private:
    int64_t id_ = 0;
    int64_t userid_ = 0;
    int64_t categoryId_ = 0;
    std::string headline_;
    std::string content_;
    int type_ = 1;
    int isRepeat_ = 0;
    int usedtime_ = 0;
};

} // namespace models
} // namespace woniunote

#endif // WONIUNOTE_MODELS_CARD_H
