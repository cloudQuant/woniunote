/**
 * @file MathTrainingController.h
 * @brief Math Training API Controller
 */

#ifndef WONIUNOTE_CONTROLLERS_MATH_TRAINING_CONTROLLER_H
#define WONIUNOTE_CONTROLLERS_MATH_TRAINING_CONTROLLER_H

#include <drogon/HttpController.h>

namespace woniunote {
namespace controllers {

class MathTrainingController : public drogon::HttpController<MathTrainingController>
{
public:
    METHOD_LIST_BEGIN
    ADD_METHOD_TO(MathTrainingController::createRecord,
                  "/api/math-training/records",
                  drogon::Post,
                  "woniunote::AuthFilter");
    ADD_METHOD_TO(MathTrainingController::getRecords,
                  "/api/math-training/records",
                  drogon::Get,
                  "woniunote::AuthFilter");
    ADD_METHOD_TO(MathTrainingController::getRecordDetail,
                  "/api/math-training/records/{record_id}",
                  drogon::Get,
                  "woniunote::AuthFilter");
    ADD_METHOD_TO(MathTrainingController::getWrongAnswers,
                  "/api/math-training/wrong-answers",
                  drogon::Get,
                  "woniunote::AuthFilter");
    ADD_METHOD_TO(MathTrainingController::getSummary,
                  "/api/math-training/summary",
                  drogon::Get,
                  "woniunote::AuthFilter");
    METHOD_LIST_END

    void createRecord(const drogon::HttpRequestPtr& req,
                      std::function<void(const drogon::HttpResponsePtr&)>&& callback);
    void getRecords(const drogon::HttpRequestPtr& req,
                    std::function<void(const drogon::HttpResponsePtr&)>&& callback);
    void getRecordDetail(const drogon::HttpRequestPtr& req,
                         std::function<void(const drogon::HttpResponsePtr&)>&& callback,
                         int64_t record_id);
    void getWrongAnswers(const drogon::HttpRequestPtr& req,
                         std::function<void(const drogon::HttpResponsePtr&)>&& callback);
    void getSummary(const drogon::HttpRequestPtr& req,
                    std::function<void(const drogon::HttpResponsePtr&)>&& callback);
};

} // namespace controllers
} // namespace woniunote

#endif // WONIUNOTE_CONTROLLERS_MATH_TRAINING_CONTROLLER_H
