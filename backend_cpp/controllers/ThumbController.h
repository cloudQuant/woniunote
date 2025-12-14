/**
 * @file ThumbController.h
 * @brief Thumbnail resources API Controller
 */

#ifndef WONIUNOTE_CONTROLLERS_THUMB_CONTROLLER_H
#define WONIUNOTE_CONTROLLERS_THUMB_CONTROLLER_H

#include <drogon/HttpController.h>

namespace woniunote {
namespace controllers {

class ThumbController : public drogon::HttpController<ThumbController>
{
public:
    METHOD_LIST_BEGIN
    ADD_METHOD_TO(ThumbController::getThumb,
                  "/api/thumb/{filename}",
                  drogon::Get);
    METHOD_LIST_END

    void getThumb(const drogon::HttpRequestPtr &req,
                  std::function<void(const drogon::HttpResponsePtr &)> &&callback,
                  const std::string &filename);
};

} // namespace controllers
} // namespace woniunote

#endif // WONIUNOTE_CONTROLLERS_THUMB_CONTROLLER_H
