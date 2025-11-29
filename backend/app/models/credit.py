"""
积分模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Credit(Base):
    """积分表"""
    __tablename__ = "credit"
    
    creditid = Column(Integer, primary_key=True, autoincrement=True)
    userid = Column(Integer, ForeignKey("users.userid"), nullable=False, index=True)
    category = Column(String(10))
    target = Column(Integer)
    credit = Column(Integer)
    createtime = Column(DateTime, default=datetime.now)
    updatetime = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    user = relationship("User", back_populates="credits")
    
    def __repr__(self):
        return f"<Credit {self.creditid}: {self.credit}>"
