"""
Math Training Schemas - 数学训练请求/响应模型
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class WrongAnswerCreate(BaseModel):
    """创建错题记录"""
    question: str = Field(..., description="题目表达式")
    correct_answer: int = Field(..., description="正确答案")
    user_answer: Optional[int] = Field(None, description="用户答案")
    operation: str = Field(..., description="运算类型: +, -, *, /")


class MathTrainingRecordCreate(BaseModel):
    """创建训练记录请求"""
    difficulty: int = Field(2, ge=1, le=3, description="难度级别: 1=个位数, 2=两位数, 3=三位数")
    total_questions: int = Field(20, ge=1, description="总题数")
    correct_count: int = Field(0, ge=0, description="正确数")
    wrong_count: int = Field(0, ge=0, description="错误数")
    accuracy: float = Field(0.0, ge=0.0, le=100.0, description="正确率")
    start_time: datetime = Field(..., description="训练开始时间")
    end_time: datetime = Field(..., description="训练结束时间")
    duration_seconds: int = Field(0, ge=0, description="训练时长(秒)")
    wrong_answers: List[WrongAnswerCreate] = Field(default_factory=list, description="错题列表")


class WrongAnswerResponse(BaseModel):
    """错题响应"""
    id: int
    record_id: int
    question: str
    correct_answer: int
    user_answer: Optional[int]
    operation: str
    difficulty: int
    created_at: datetime

    class Config:
        from_attributes = True


class MathTrainingRecordResponse(BaseModel):
    """训练记录响应"""
    id: int
    user_id: int
    difficulty: int
    total_questions: int
    correct_count: int
    wrong_count: int
    accuracy: float
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    created_at: datetime
    wrong_answers: List[WrongAnswerResponse] = []

    class Config:
        from_attributes = True


class MathTrainingRecordListItem(BaseModel):
    """训练记录列表项（不含错题详情）"""
    id: int
    user_id: int
    difficulty: int
    total_questions: int
    correct_count: int
    wrong_count: int
    accuracy: float
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    created_at: datetime

    class Config:
        from_attributes = True


class MathTrainingSummary(BaseModel):
    """训练统计摘要"""
    total_sessions: int = Field(0, description="总训练次数")
    total_questions: int = Field(0, description="总答题数")
    total_correct: int = Field(0, description="总正确数")
    total_wrong: int = Field(0, description="总错误数")
    average_accuracy: float = Field(0.0, description="平均正确率")
    total_duration_seconds: int = Field(0, description="总训练时长(秒)")
