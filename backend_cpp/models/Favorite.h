/**
 * @file Favorite.h
 * @brief Favorite Model for Drogon ORM
 */

#ifndef WONIUNOTE_MODELS_FAVORITE_H
#define WONIUNOTE_MODELS_FAVORITE_H

#include <drogon/orm/Mapper.h>
#include <json/json.h>

namespace woniunote {
namespace models {

class Favorite {
public:
    static constexpr const char* tableName = "favorite";
    static constexpr const char* primaryKeyName = "favoriteid";

    Favorite() = default;
    explicit Favorite(const drogon::orm::Row& row);

    int64_t getFavoriteid() const { return favoriteid_; }
    int64_t getUserid() const { return userid_; }
    int64_t getArticleid() const { return articleid_; }
    int getCanceled() const { return canceled_; }

    void setFavoriteid(int64_t v) { favoriteid_ = v; }
    void setUserid(int64_t v) { userid_ = v; }
    void setArticleid(int64_t v) { articleid_ = v; }
    void setCanceled(int v) { canceled_ = v; }

    Json::Value toJson() const;

private:
    int64_t favoriteid_ = 0;
    int64_t userid_ = 0;
    int64_t articleid_ = 0;
    int canceled_ = 0;
};

} // namespace models
} // namespace woniunote

#endif // WONIUNOTE_MODELS_FAVORITE_H
