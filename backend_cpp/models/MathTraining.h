/**
 * @file MathTraining.h
 * @brief Math Training Record and Wrong Answer Models
 */

#ifndef WONIUNOTE_MODELS_MATH_TRAINING_H
#define WONIUNOTE_MODELS_MATH_TRAINING_H

#include <string>
#include <vector>
#include <drogon/orm/Mapper.h>
#include <drogon/orm/Field.h>
#include <json/json.h>

namespace woniunote {
namespace models {

class MathTrainingWrongAnswer
{
public:
    MathTrainingWrongAnswer() = default;
    explicit MathTrainingWrongAnswer(const drogon::orm::Row& row);

    Json::Value toJson() const;

    int64_t id_ = 0;
    int64_t record_id_ = 0;
    int64_t user_id_ = 0;
    std::string question_;
    int correct_answer_ = 0;
    int user_answer_ = 0;
    std::string operation_;
    int difficulty_ = 2;
    std::string created_at_;
};

class MathTrainingRecord
{
public:
    MathTrainingRecord() = default;
    explicit MathTrainingRecord(const drogon::orm::Row& row);

    Json::Value toJson() const;
    Json::Value toJsonBrief() const;

    int64_t id_ = 0;
    int64_t user_id_ = 0;
    int difficulty_ = 2;
    int total_questions_ = 20;
    int correct_count_ = 0;
    int wrong_count_ = 0;
    double accuracy_ = 0.0;
    std::string start_time_;
    std::string end_time_;
    int duration_seconds_ = 0;
    std::string created_at_;

    std::vector<MathTrainingWrongAnswer> wrong_answers_;
};

} // namespace models
} // namespace woniunote

#endif // WONIUNOTE_MODELS_MATH_TRAINING_H
