/**
 * @file Credit.h
 * @brief Credit Model for Drogon ORM
 */

#ifndef WONIUNOTE_MODELS_CREDIT_H
#define WONIUNOTE_MODELS_CREDIT_H

#include <drogon/orm/Mapper.h>
#include <json/json.h>
#include <string>

namespace woniunote {
namespace models {

class Credit {
public:
    static constexpr const char* tableName = "credit";
    static constexpr const char* primaryKeyName = "creditid";

    Credit() = default;
    explicit Credit(const drogon::orm::Row& row);

    int64_t getCreditid() const { return creditid_; }
    int64_t getUserid() const { return userid_; }
    const std::string& getCategory() const { return category_; }
    int64_t getTarget() const { return target_; }
    int getCredit() const { return credit_; }

    void setCreditid(int64_t v) { creditid_ = v; }
    void setUserid(int64_t v) { userid_ = v; }
    void setCategory(const std::string& v) { category_ = v; }
    void setTarget(int64_t v) { target_ = v; }
    void setCredit(int v) { credit_ = v; }

    Json::Value toJson() const;

private:
    int64_t creditid_ = 0;
    int64_t userid_ = 0;
    std::string category_;
    int64_t target_ = 0;
    int credit_ = 0;
};

} // namespace models
} // namespace woniunote

#endif // WONIUNOTE_MODELS_CREDIT_H
