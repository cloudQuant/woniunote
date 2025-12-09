/**
 * @file User.h
 * @brief User Model for Drogon ORM
 * 
 * Corresponds to the 'users' table in MySQL.
 */

#ifndef WONIUNOTE_MODELS_USER_H
#define WONIUNOTE_MODELS_USER_H

#include <drogon/orm/Mapper.h>
#include <drogon/orm/Field.h>
#include <json/json.h>
#include <string>
#include <chrono>
#include <optional>

namespace woniunote {
namespace models {

/**
 * @class User
 * @brief User entity class
 * 
 * Represents a row in the 'users' table.
 */
class User {
public:
    // Table name
    static constexpr const char* tableName = "users";
    static constexpr const char* primaryKeyName = "userid";

    // Constructors
    User() = default;
    explicit User(const drogon::orm::Row& row);

    // Getters
    int64_t getUserid() const { return userid_; }
    const std::string& getUsername() const { return username_; }
    const std::string& getPassword() const { return password_; }
    const std::string& getNickname() const { return nickname_; }
    const std::string& getAvatar() const { return avatar_; }
    const std::string& getQq() const { return qq_; }
    const std::string& getRole() const { return role_; }
    int getCredit() const { return credit_; }
    const std::chrono::system_clock::time_point& getCreatetime() const { return createtime_; }
    const std::chrono::system_clock::time_point& getUpdatetime() const { return updatetime_; }

    // Setters
    void setUserid(int64_t value) { userid_ = value; }
    void setUsername(const std::string& value) { username_ = value; }
    void setPassword(const std::string& value) { password_ = value; }
    void setNickname(const std::string& value) { nickname_ = value; }
    void setAvatar(const std::string& value) { avatar_ = value; }
    void setQq(const std::string& value) { qq_ = value; }
    void setRole(const std::string& value) { role_ = value; }
    void setCredit(int value) { credit_ = value; }

    // JSON serialization
    Json::Value toJson() const;
    Json::Value toJsonWithoutPassword() const;

    // Check if user is admin
    bool isAdmin() const { return role_ == "admin"; }

private:
    int64_t userid_ = 0;
    std::string username_;
    std::string password_;
    std::string nickname_;
    std::string avatar_;
    std::string qq_;
    std::string role_ = "user";
    int credit_ = 50;
    std::chrono::system_clock::time_point createtime_;
    std::chrono::system_clock::time_point updatetime_;
};

} // namespace models
} // namespace woniunote

#endif // WONIUNOTE_MODELS_USER_H
