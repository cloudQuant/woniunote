"""
Math Training Models - 数学训练记录和错题模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class MathTrainingRecord(Base):
    """数学训练记录表"""
    __tablename__ = "math_training_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.userid"), nullable=False, index=True)
    difficulty = Column(Integer, nullable=False, default=2, comment="难度级别: 1=个位数, 2=两位数, 3=三位数")
    total_questions = Column(Integer, nullable=False, default=20, comment="总题数")
    correct_count = Column(Integer, nullable=False, default=0, comment="正确数")
    wrong_count = Column(Integer, nullable=False, default=0, comment="错误数")
    accuracy = Column(Float, nullable=False, default=0.0, comment="正确率")
    start_time = Column(DateTime, nullable=False, comment="训练开始时间")
    end_time = Column(DateTime, nullable=False, comment="训练结束时间")
    duration_seconds = Column(Integer, nullable=False, default=0, comment="训练时长(秒)")
    created_at = Column(DateTime, default=datetime.now, comment="记录创建时间")

    # 关联
    user = relationship("User", backref="math_training_records")
    wrong_answers = relationship("MathTrainingWrongAnswer", back_populates="record", cascade="all, delete-orphan")


class MathTrainingWrongAnswer(Base):
    """数学训练错题表"""
    __tablename__ = "math_training_wrong_answers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_id = Column(Integer, ForeignKey("math_training_records.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.userid"), nullable=False, index=True)
    question = Column(String(100), nullable=False, comment="题目表达式，如 '12 + 34'")
    correct_answer = Column(Integer, nullable=False, comment="正确答案")
    user_answer = Column(Integer, nullable=True, comment="用户答案")
    operation = Column(String(10), nullable=False, comment="运算类型: +, -, *, /")
    difficulty = Column(Integer, nullable=False, comment="难度级别")
    created_at = Column(DateTime, default=datetime.now, comment="记录创建时间")

    # 关联
    record = relationship("MathTrainingRecord", back_populates="wrong_answers")
    user = relationship("User", backref="math_training_wrong_answers")
