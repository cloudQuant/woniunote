/**
 * @file MathTraining.cc
 * @brief Math Training Record and Wrong Answer Model Implementation
 */

#include "MathTraining.h"

namespace woniunote {
namespace models {

// MathTrainingWrongAnswer implementation
MathTrainingWrongAnswer::MathTrainingWrongAnswer(const drogon::orm::Row& row)
{
    id_ = row["id"].as<int64_t>();
    record_id_ = row["record_id"].as<int64_t>();
    user_id_ = row["user_id"].as<int64_t>();
    question_ = row["question"].as<std::string>();
    correct_answer_ = row["correct_answer"].as<int>();
    if (!row["user_answer"].isNull()) {
        user_answer_ = row["user_answer"].as<int>();
    }
    operation_ = row["operation"].as<std::string>();
    difficulty_ = row["difficulty"].as<int>();
    created_at_ = row["created_at"].as<std::string>();
}

Json::Value MathTrainingWrongAnswer::toJson() const
{
    Json::Value ret;
    ret["id"] = static_cast<Json::Int64>(id_);
    ret["record_id"] = static_cast<Json::Int64>(record_id_);
    ret["user_id"] = static_cast<Json::Int64>(user_id_);
    ret["question"] = question_;
    ret["correct_answer"] = correct_answer_;
    ret["user_answer"] = user_answer_;
    ret["operation"] = operation_;
    ret["difficulty"] = difficulty_;
    ret["created_at"] = created_at_;
    return ret;
}

// MathTrainingRecord implementation
MathTrainingRecord::MathTrainingRecord(const drogon::orm::Row& row)
{
    id_ = row["id"].as<int64_t>();
    user_id_ = row["user_id"].as<int64_t>();
    difficulty_ = row["difficulty"].as<int>();
    total_questions_ = row["total_questions"].as<int>();
    correct_count_ = row["correct_count"].as<int>();
    wrong_count_ = row["wrong_count"].as<int>();
    accuracy_ = row["accuracy"].as<double>();
    start_time_ = row["start_time"].as<std::string>();
    end_time_ = row["end_time"].as<std::string>();
    duration_seconds_ = row["duration_seconds"].as<int>();
    created_at_ = row["created_at"].as<std::string>();
}

Json::Value MathTrainingRecord::toJson() const
{
    Json::Value ret;
    ret["id"] = static_cast<Json::Int64>(id_);
    ret["user_id"] = static_cast<Json::Int64>(user_id_);
    ret["difficulty"] = difficulty_;
    ret["total_questions"] = total_questions_;
    ret["correct_count"] = correct_count_;
    ret["wrong_count"] = wrong_count_;
    ret["accuracy"] = accuracy_;
    ret["start_time"] = start_time_;
    ret["end_time"] = end_time_;
    ret["duration_seconds"] = duration_seconds_;
    ret["created_at"] = created_at_;

    // Include wrong answers if available
    Json::Value wrongAnswers(Json::arrayValue);
    for (const auto& wa : wrong_answers_) {
        wrongAnswers.append(wa.toJson());
    }
    ret["wrong_answers"] = wrongAnswers;

    return ret;
}

Json::Value MathTrainingRecord::toJsonBrief() const
{
    Json::Value ret;
    ret["id"] = static_cast<Json::Int64>(id_);
    ret["user_id"] = static_cast<Json::Int64>(user_id_);
    ret["difficulty"] = difficulty_;
    ret["total_questions"] = total_questions_;
    ret["correct_count"] = correct_count_;
    ret["wrong_count"] = wrong_count_;
    ret["accuracy"] = accuracy_;
    ret["start_time"] = start_time_;
    ret["end_time"] = end_time_;
    ret["duration_seconds"] = duration_seconds_;
    ret["created_at"] = created_at_;
    return ret;
}

} // namespace models
} // namespace woniunote
