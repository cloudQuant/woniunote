/**
 * @file Article.h
 * @brief Article Model for Drogon ORM
 * 
 * Corresponds to the 'article' table in MySQL.
 */

#ifndef WONIUNOTE_MODELS_ARTICLE_H
#define WONIUNOTE_MODELS_ARTICLE_H

#include <drogon/orm/Mapper.h>
#include <drogon/orm/Field.h>
#include <json/json.h>
#include <string>
#include <chrono>

namespace woniunote {
namespace models {

/**
 * @class Article
 * @brief Article entity class
 */
class Article {
public:
    static constexpr const char* tableName = "article";
    static constexpr const char* primaryKeyName = "articleid";

    Article() = default;
    explicit Article(const drogon::orm::Row& row);

    // Getters
    int64_t getArticleid() const { return articleid_; }
    int64_t getUserid() const { return userid_; }
    int getType() const { return type_; }
    const std::string& getHeadline() const { return headline_; }
    const std::string& getContent() const { return content_; }
    const std::string& getThumbnail() const { return thumbnail_; }
    int getCredit() const { return credit_; }
    int getReadcount() const { return readcount_; }
    int getReplycount() const { return replycount_; }
    int getRecommended() const { return recommended_; }
    int getHidden() const { return hidden_; }
    int getDrafted() const { return drafted_; }
    int getChecked() const { return checked_; }

    // Setters
    void setArticleid(int64_t v) { articleid_ = v; }
    void setUserid(int64_t v) { userid_ = v; }
    void setType(int v) { type_ = v; }
    void setHeadline(const std::string& v) { headline_ = v; }
    void setContent(const std::string& v) { content_ = v; }
    void setThumbnail(const std::string& v) { thumbnail_ = v; }
    void setCredit(int v) { credit_ = v; }
    void setReadcount(int v) { readcount_ = v; }
    void setReplycount(int v) { replycount_ = v; }
    void setRecommended(int v) { recommended_ = v; }
    void setHidden(int v) { hidden_ = v; }
    void setDrafted(int v) { drafted_ = v; }
    void setChecked(int v) { checked_ = v; }

    // JSON
    Json::Value toJson() const;
    Json::Value toJsonBrief() const;  // Without content for lists

private:
    int64_t articleid_ = 0;
    int64_t userid_ = 0;
    int type_ = 0;
    std::string headline_;
    std::string content_;
    std::string thumbnail_;
    int credit_ = 0;
    int readcount_ = 0;
    int replycount_ = 0;
    int recommended_ = 0;
    int hidden_ = 0;
    int drafted_ = 0;
    int checked_ = 1;
    std::string createtime_;
    std::string updatetime_;
    std::string nickname_;  // From JOIN with users table
};

} // namespace models
} // namespace woniunote

#endif // WONIUNOTE_MODELS_ARTICLE_H
