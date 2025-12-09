/**
 * @file Comment.h
 * @brief Comment Model for Drogon ORM
 */

#ifndef WONIUNOTE_MODELS_COMMENT_H
#define WONIUNOTE_MODELS_COMMENT_H

#include <drogon/orm/Mapper.h>
#include <json/json.h>
#include <string>

namespace woniunote {
namespace models {

class Comment {
public:
    static constexpr const char* tableName = "comment";
    static constexpr const char* primaryKeyName = "commentid";

    Comment() = default;
    explicit Comment(const drogon::orm::Row& row);

    int64_t getCommentid() const { return commentid_; }
    int64_t getUserid() const { return userid_; }
    int64_t getArticleid() const { return articleid_; }
    const std::string& getContent() const { return content_; }
    const std::string& getIpaddr() const { return ipaddr_; }
    int64_t getReplyid() const { return replyid_; }
    int getAgreecount() const { return agreecount_; }
    int getOpposecount() const { return opposecount_; }
    int getHidden() const { return hidden_; }

    void setCommentid(int64_t v) { commentid_ = v; }
    void setUserid(int64_t v) { userid_ = v; }
    void setArticleid(int64_t v) { articleid_ = v; }
    void setContent(const std::string& v) { content_ = v; }
    void setIpaddr(const std::string& v) { ipaddr_ = v; }
    void setReplyid(int64_t v) { replyid_ = v; }
    void setAgreecount(int v) { agreecount_ = v; }
    void setOpposecount(int v) { opposecount_ = v; }
    void setHidden(int v) { hidden_ = v; }

    Json::Value toJson() const;

private:
    int64_t commentid_ = 0;
    int64_t userid_ = 0;
    int64_t articleid_ = 0;
    std::string content_;
    std::string ipaddr_;
    int64_t replyid_ = 0;
    int agreecount_ = 0;
    int opposecount_ = 0;
    int hidden_ = 0;
};

} // namespace models
} // namespace woniunote

#endif // WONIUNOTE_MODELS_COMMENT_H
